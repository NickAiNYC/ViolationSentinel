"""
NYC Open Data API Client with Production-Grade Resilience.

This module provides a robust client for interacting with NYC Open Data APIs,
featuring circuit breakers, rate limiting, multi-layer caching, exponential backoff,
and comprehensive monitoring.
"""

import asyncio
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from circuitbreaker import circuit, CircuitBreakerError
from cachetools import TTLCache
from prometheus_client import Counter, Histogram, Gauge
import redis.asyncio as redis

# Configure logging
logger = logging.getLogger(__name__)


# Custom Exceptions
class NYCDataError(Exception):
    """Base exception for NYC Data API errors."""
    pass


class RateLimitError(NYCDataError):
    """Raised when API rate limit is exceeded."""
    pass


class CircuitBreakerOpenError(NYCDataError):
    """Raised when circuit breaker is open."""
    pass


class CacheError(NYCDataError):
    """Raised when cache operation fails."""
    pass


# Prometheus Metrics
REQUEST_COUNT = Counter(
    'nyc_data_requests_total',
    'Total number of NYC Data API requests',
    ['method', 'status']
)
REQUEST_LATENCY = Histogram(
    'nyc_data_request_duration_seconds',
    'NYC Data API request latency',
    ['method']
)
CACHE_HITS = Counter(
    'nyc_data_cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)
CACHE_MISSES = Counter(
    'nyc_data_cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)
ERROR_COUNT = Counter(
    'nyc_data_errors_total',
    'Total number of errors',
    ['error_type']
)
CIRCUIT_BREAKER_STATE = Gauge(
    'nyc_data_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open)',
    ['endpoint']
)


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: int = 1000, per: float = 60.0):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self._lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current
            self.allowance += time_passed * (self.rate / self.per)
            
            if self.allowance > self.rate:
                self.allowance = self.rate
            
            if self.allowance < 1.0:
                raise RateLimitError("Rate limit exceeded")
            
            self.allowance -= 1.0


class NYCDataClient:
    """
    Production-grade NYC Open Data API client with comprehensive resilience features.
    
    Features:
    - Async HTTP requests with connection pooling
    - Circuit breaker for fault tolerance
    - Rate limiting to respect API limits
    - Multi-layer caching (in-memory LRU + Redis)
    - Exponential backoff retry with jitter
    - Request timeout handling
    - Automatic failover to cached data
    - Structured logging
    - Prometheus metrics
    """
    
    # NYC Open Data API endpoints
    DOB_VIOLATIONS_ENDPOINT = "https://data.cityofnewyork.us/resource/6bgk-3dad.json"
    HPD_VIOLATIONS_ENDPOINT = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
    COMPLAINTS_311_ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    PERMITS_ENDPOINT = "https://data.cityofnewyork.us/resource/ipu4-2q9a.json"
    
    def __init__(
        self,
        app_token: Optional[str] = None,
        redis_url: Optional[str] = None,
        max_connections: int = 50,
        request_timeout: int = 30,
        memory_cache_size: int = 1000,
        memory_cache_ttl: int = 300,
        redis_cache_ttl: int = 3600,
        rate_limit: int = 1000,
        rate_limit_period: float = 60.0,
    ):
        """
        Initialize NYC Data Client.
        
        Args:
            app_token: NYC Open Data API token
            redis_url: Redis connection URL (optional)
            max_connections: Maximum concurrent connections
            request_timeout: Request timeout in seconds
            memory_cache_size: In-memory cache size
            memory_cache_ttl: In-memory cache TTL in seconds
            redis_cache_ttl: Redis cache TTL in seconds
            rate_limit: Number of requests allowed
            rate_limit_period: Rate limit period in seconds
        """
        self.app_token = app_token
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.request_timeout = request_timeout
        self.memory_cache_ttl = memory_cache_ttl
        self.redis_cache_ttl = redis_cache_ttl
        
        # Initialize components
        self._session: Optional[aiohttp.ClientSession] = None
        self._redis: Optional[redis.Redis] = None
        self._memory_cache = TTLCache(maxsize=memory_cache_size, ttl=memory_cache_ttl)
        self._rate_limiter = RateLimiter(rate=rate_limit, per=rate_limit_period)
        self._initialized = False
        
        # Cache statistics
        self._stats = {
            'requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'circuit_breaks': 0,
        }
        
        logger.info(
            "NYCDataClient initialized",
            extra={
                'max_connections': max_connections,
                'request_timeout': request_timeout,
                'rate_limit': rate_limit,
            }
        )
    
    async def _initialize(self):
        """Initialize async components."""
        if self._initialized:
            return
        
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.max_connections,
            ttl_dns_cache=300,
        )
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
        )
        
        # Initialize Redis if URL provided
        if self.redis_url:
            try:
                self._redis = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Continuing without Redis cache.")
                self._redis = None
        
        self._initialized = True
        logger.info("NYCDataClient fully initialized")
    
    async def close(self):
        """Close connections and cleanup resources."""
        if self._session:
            await self._session.close()
        
        if self._redis:
            await self._redis.close()
        
        self._initialized = False
        logger.info("NYCDataClient closed")
    
    def _cache_key(self, method: str, **params) -> str:
        """Generate cache key from method and parameters."""
        key_data = f"{method}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve data from multi-layer cache."""
        # Try memory cache first
        if cache_key in self._memory_cache:
            CACHE_HITS.labels(cache_type='memory').inc()
            self._stats['cache_hits'] += 1
            logger.debug(f"Memory cache hit: {cache_key}")
            return self._memory_cache[cache_key]
        
        # Try Redis cache
        if self._redis:
            try:
                data = await self._redis.get(cache_key)
                if data:
                    CACHE_HITS.labels(cache_type='redis').inc()
                    self._stats['cache_hits'] += 1
                    logger.debug(f"Redis cache hit: {cache_key}")
                    result = json.loads(data)
                    # Populate memory cache
                    self._memory_cache[cache_key] = result
                    return result
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        CACHE_MISSES.labels(cache_type='all').inc()
        self._stats['cache_misses'] += 1
        return None
    
    async def _set_to_cache(self, cache_key: str, data: Any):
        """Store data in multi-layer cache."""
        # Store in memory cache
        self._memory_cache[cache_key] = data
        
        # Store in Redis cache
        if self._redis:
            try:
                await self._redis.setex(
                    cache_key,
                    self.redis_cache_ttl,
                    json.dumps(data)
                )
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
    
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=NYCDataError)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _make_request(
        self,
        url: str,
        params: Dict[str, Any],
        method_name: str,
    ) -> List[Dict]:
        """
        Make HTTP request with circuit breaker and retry logic.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            method_name: Name of the calling method (for metrics)
        
        Returns:
            List of data records
        """
        await self._initialize()
        
        # Check rate limit
        try:
            await self._rate_limiter.acquire()
        except RateLimitError as e:
            ERROR_COUNT.labels(error_type='rate_limit').inc()
            self._stats['errors'] += 1
            logger.warning(f"Rate limit exceeded for {method_name}")
            raise
        
        # Add app token to headers if available
        headers = {}
        if self.app_token:
            headers['X-App-Token'] = self.app_token
        
        # Make request
        start_time = time.time()
        try:
            async with self._session.get(url, params=params, headers=headers) as response:
                duration = time.time() - start_time
                REQUEST_LATENCY.labels(method=method_name).observe(duration)
                
                if response.status == 200:
                    data = await response.json()
                    REQUEST_COUNT.labels(method=method_name, status='success').inc()
                    self._stats['requests'] += 1
                    
                    logger.info(
                        f"API request successful: {method_name}",
                        extra={
                            'duration': duration,
                            'records': len(data),
                            'url': url,
                        }
                    )
                    return data
                else:
                    REQUEST_COUNT.labels(method=method_name, status='error').inc()
                    ERROR_COUNT.labels(error_type='http_error').inc()
                    self._stats['errors'] += 1
                    
                    error_text = await response.text()
                    logger.error(
                        f"API request failed: {method_name}",
                        extra={
                            'status': response.status,
                            'error': error_text[:200],
                        }
                    )
                    raise NYCDataError(f"HTTP {response.status}: {error_text[:200]}")
        
        except CircuitBreakerError:
            CIRCUIT_BREAKER_STATE.labels(endpoint=url).set(1)
            self._stats['circuit_breaks'] += 1
            ERROR_COUNT.labels(error_type='circuit_breaker').inc()
            logger.error(f"Circuit breaker open for {method_name}")
            raise CircuitBreakerOpenError(f"Circuit breaker open for {method_name}")
        
        except Exception as e:
            ERROR_COUNT.labels(error_type='request_error').inc()
            self._stats['errors'] += 1
            logger.error(f"Request error in {method_name}: {str(e)}")
            raise
    
    async def _fetch_with_cache(
        self,
        method_name: str,
        url: str,
        params: Dict[str, Any],
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Fetch data with caching and automatic failover.
        
        Args:
            method_name: Name of the calling method
            url: API endpoint URL
            params: Query parameters
            use_cache: Whether to use cache
        
        Returns:
            List of data records
        """
        cache_key = self._cache_key(method_name, **params)
        
        # Try cache first if enabled
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data is not None:
                logger.debug(f"Returning cached data for {method_name}")
                return cached_data
        
        # Try API request
        try:
            data = await self._make_request(url, params, method_name)
            
            # Cache successful response
            if use_cache:
                await self._set_to_cache(cache_key, data)
            
            return data
        
        except (CircuitBreakerOpenError, RateLimitError, NYCDataError) as e:
            # Try to return stale cached data as failover
            if use_cache:
                logger.warning(f"API error, attempting failover to cache: {e}")
                cached_data = await self._get_from_cache(cache_key)
                if cached_data is not None:
                    logger.info(f"Failover successful for {method_name}")
                    return cached_data
            
            # No cached data available
            logger.error(f"No cached data available for failover in {method_name}")
            raise
    
    async def get_dob_violations(
        self,
        bbl: str,
        limit: int = 1000,
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Fetch Department of Buildings violations for a property.
        
        Args:
            bbl: Borough-Block-Lot identifier (10 digits)
            limit: Maximum number of records to return
            use_cache: Whether to use caching
        
        Returns:
            List of DOB violation records
        
        Raises:
            NYCDataError: On API errors
            RateLimitError: When rate limit is exceeded
            CircuitBreakerOpenError: When circuit breaker is open
        """
        params = {
            'bbl': str(bbl),
            '$limit': limit,
            '$order': 'issue_date DESC',
        }
        
        return await self._fetch_with_cache(
            'get_dob_violations',
            self.DOB_VIOLATIONS_ENDPOINT,
            params,
            use_cache,
        )
    
    async def get_hpd_violations(
        self,
        bbl: str,
        limit: int = 1000,
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Fetch Housing Preservation and Development violations for a property.
        
        Args:
            bbl: Borough-Block-Lot identifier (10 digits)
            limit: Maximum number of records to return
            use_cache: Whether to use caching
        
        Returns:
            List of HPD violation records
        
        Raises:
            NYCDataError: On API errors
            RateLimitError: When rate limit is exceeded
            CircuitBreakerOpenError: When circuit breaker is open
        """
        params = {
            'bbl': str(bbl),
            '$limit': limit,
            '$order': 'inspectiondate DESC',
        }
        
        return await self._fetch_with_cache(
            'get_hpd_violations',
            self.HPD_VIOLATIONS_ENDPOINT,
            params,
            use_cache,
        )
    
    async def get_311_complaints(
        self,
        bbl: str,
        days: int = 30,
        limit: int = 1000,
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Fetch 311 complaints for a property within a time window.
        
        Args:
            bbl: Borough-Block-Lot identifier (10 digits)
            days: Number of days to look back
            limit: Maximum number of records to return
            use_cache: Whether to use caching
        
        Returns:
            List of 311 complaint records
        
        Raises:
            NYCDataError: On API errors
            RateLimitError: When rate limit is exceeded
            CircuitBreakerOpenError: When circuit breaker is open
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        params = {
            'bbl': str(bbl),
            '$where': f"created_date >= '{cutoff_date}'",
            '$limit': limit,
            '$order': 'created_date DESC',
        }
        
        return await self._fetch_with_cache(
            'get_311_complaints',
            self.COMPLAINTS_311_ENDPOINT,
            params,
            use_cache,
        )
    
    async def get_permits(
        self,
        bbl: str,
        limit: int = 1000,
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Fetch building permits for a property.
        
        Args:
            bbl: Borough-Block-Lot identifier (10 digits)
            limit: Maximum number of records to return
            use_cache: Whether to use caching
        
        Returns:
            List of permit records
        
        Raises:
            NYCDataError: On API errors
            RateLimitError: When rate limit is exceeded
            CircuitBreakerOpenError: When circuit breaker is open
        """
        params = {
            'bin': str(bbl),  # Permits use BIN (Building Identification Number)
            '$limit': limit,
            '$order': 'filing_date DESC',
        }
        
        return await self._fetch_with_cache(
            'get_permits',
            self.PERMITS_ENDPOINT,
            params,
            use_cache,
        )
    
    async def batch_fetch(
        self,
        bbls: List[str],
        include_dob: bool = True,
        include_hpd: bool = True,
        include_311: bool = True,
        include_permits: bool = True,
        days_311: int = 30,
        use_cache: bool = True,
    ) -> Dict[str, Dict[str, List[Dict]]]:
        """
        Batch fetch data for multiple properties concurrently.
        
        Args:
            bbls: List of Borough-Block-Lot identifiers
            include_dob: Whether to fetch DOB violations
            include_hpd: Whether to fetch HPD violations
            include_311: Whether to fetch 311 complaints
            include_permits: Whether to fetch permits
            days_311: Number of days to look back for 311 complaints
            use_cache: Whether to use caching
        
        Returns:
            Dictionary mapping BBL to data types to records
            
        Example:
            {
                "1012650001": {
                    "dob_violations": [...],
                    "hpd_violations": [...],
                    "311_complaints": [...],
                    "permits": [...]
                }
            }
        
        Raises:
            NYCDataError: On critical errors
        """
        results = {}
        tasks = []
        
        for bbl in bbls:
            bbl_tasks = []
            
            if include_dob:
                bbl_tasks.append(('dob_violations', self.get_dob_violations(bbl, use_cache=use_cache)))
            
            if include_hpd:
                bbl_tasks.append(('hpd_violations', self.get_hpd_violations(bbl, use_cache=use_cache)))
            
            if include_311:
                bbl_tasks.append(('311_complaints', self.get_311_complaints(bbl, days=days_311, use_cache=use_cache)))
            
            if include_permits:
                bbl_tasks.append(('permits', self.get_permits(bbl, use_cache=use_cache)))
            
            tasks.append((bbl, bbl_tasks))
        
        # Execute all tasks concurrently
        for bbl, bbl_tasks in tasks:
            results[bbl] = {}
            
            # Gather all tasks for this BBL
            task_coros = [task for _, task in bbl_tasks]
            task_names = [name for name, _ in bbl_tasks]
            
            try:
                task_results = await asyncio.gather(*task_coros, return_exceptions=True)
                
                for name, result in zip(task_names, task_results):
                    if isinstance(result, Exception):
                        logger.error(f"Error fetching {name} for BBL {bbl}: {result}")
                        results[bbl][name] = []
                    else:
                        results[bbl][name] = result
            
            except Exception as e:
                logger.error(f"Batch fetch error for BBL {bbl}: {e}")
                # Initialize with empty lists
                for name in task_names:
                    results[bbl][name] = []
        
        logger.info(
            f"Batch fetch completed for {len(bbls)} properties",
            extra={'bbls_count': len(bbls)}
        )
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all components.
        
        Returns:
            Dictionary with health status of each component
        """
        await self._initialize()
        
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {},
        }
        
        # Check aiohttp session
        health['components']['http_session'] = {
            'status': 'healthy' if self._session and not self._session.closed else 'unhealthy',
        }
        
        # Check Redis
        if self._redis:
            try:
                await self._redis.ping()
                health['components']['redis'] = {'status': 'healthy'}
            except Exception as e:
                health['components']['redis'] = {
                    'status': 'unhealthy',
                    'error': str(e),
                }
                health['status'] = 'degraded'
        else:
            health['components']['redis'] = {'status': 'disabled'}
        
        # Add cache statistics
        health['cache_stats'] = {
            'memory_cache_size': len(self._memory_cache),
            'memory_cache_maxsize': self._memory_cache.maxsize,
        }
        
        # Add request statistics
        health['request_stats'] = self._stats.copy()
        
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Dictionary with various statistics
        """
        return {
            'requests': self._stats['requests'],
            'cache_hits': self._stats['cache_hits'],
            'cache_misses': self._stats['cache_misses'],
            'cache_hit_rate': (
                self._stats['cache_hits'] / (self._stats['cache_hits'] + self._stats['cache_misses'])
                if (self._stats['cache_hits'] + self._stats['cache_misses']) > 0
                else 0.0
            ),
            'errors': self._stats['errors'],
            'circuit_breaks': self._stats['circuit_breaks'],
            'memory_cache_size': len(self._memory_cache),
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
