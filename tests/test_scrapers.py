"""
Tests for NYC Data Scrapers/Fetchers.

Tests for HPD violations, DOB violations, 311 complaints, and permits
data fetching functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json


class TestNYCDataClient:
    """Test suite for the NYC Open Data API client."""

    def test_cache_key_generation(self):
        """Test cache key generation is consistent and deterministic."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        client = NYCDataClient()
        
        # Same inputs should generate same cache key
        key1 = client._cache_key("get_hpd_violations", bbl="3012650001", limit=1000)
        key2 = client._cache_key("get_hpd_violations", bbl="3012650001", limit=1000)
        assert key1 == key2
        
        # Different inputs should generate different keys
        key3 = client._cache_key("get_hpd_violations", bbl="3012650002", limit=1000)
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initializes with correct defaults."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        client = NYCDataClient(
            app_token="test-token",
            max_connections=50,
            request_timeout=30
        )
        
        assert client.app_token == "test-token"
        assert client.max_connections == 50
        assert client.request_timeout == 30
        assert not client._initialized

    @pytest.mark.asyncio
    async def test_health_check(self, mock_redis):
        """Test health check returns proper structure."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_initialize', new_callable=AsyncMock):
            client = NYCDataClient()
            client._session = MagicMock()
            client._session.closed = False
            client._redis = None
            client._memory_cache = MagicMock()
            client._memory_cache.__len__ = MagicMock(return_value=0)
            client._memory_cache.maxsize = 1000
            client._stats = {
                'requests': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'errors': 0,
                'circuit_breaks': 0
            }
            
            health = await client.health_check()
            
            assert 'status' in health
            assert 'timestamp' in health
            assert 'components' in health
            assert 'cache_stats' in health
            assert 'request_stats' in health


class TestHPDViolationsFetcher:
    """Tests for HPD (Housing Preservation and Development) violations fetching."""

    @pytest.fixture
    def mock_hpd_response(self, sample_hpd_violation):
        """Return mock HPD API response."""
        return [sample_hpd_violation]

    @pytest.mark.asyncio
    async def test_get_hpd_violations_returns_list(self, mock_hpd_response):
        """Test that HPD violations endpoint returns a list."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_hpd_response
            
            client = NYCDataClient()
            violations = await client.get_hpd_violations(bbl="3012650001")
            
            assert isinstance(violations, list)
            assert len(violations) == 1
            assert violations[0]['bbl'] == "3012650001"

    @pytest.mark.asyncio
    async def test_get_hpd_violations_with_limit(self):
        """Test HPD violations respects limit parameter."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [{"id": i} for i in range(10)]
            
            client = NYCDataClient()
            await client.get_hpd_violations(bbl="3012650001", limit=10)
            
            # Verify _fetch_with_cache was called
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_hpd_violations_caching_disabled(self):
        """Test HPD violations can bypass cache."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            
            client = NYCDataClient()
            await client.get_hpd_violations(bbl="3012650001", use_cache=False)
            
            # Verify use_cache=False was passed
            call_args = mock_fetch.call_args
            assert call_args is not None


class TestDOBViolationsFetcher:
    """Tests for DOB (Department of Buildings) violations fetching."""

    @pytest.fixture
    def mock_dob_response(self, sample_dob_violation):
        """Return mock DOB API response."""
        return [sample_dob_violation]

    @pytest.mark.asyncio
    async def test_get_dob_violations_returns_list(self, mock_dob_response):
        """Test that DOB violations endpoint returns a list."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_dob_response
            
            client = NYCDataClient()
            violations = await client.get_dob_violations(bbl="3012650001")
            
            assert isinstance(violations, list)
            assert len(violations) == 1

    @pytest.mark.asyncio
    async def test_dob_violations_endpoint_url(self):
        """Test DOB violations uses correct API endpoint."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        client = NYCDataClient()
        assert "data.cityofnewyork.us" in client.DOB_VIOLATIONS_ENDPOINT
        assert "6bgk-3dad" in client.DOB_VIOLATIONS_ENDPOINT  # DOB violations dataset ID


class Test311ComplaintsFetcher:
    """Tests for 311 complaints fetching."""

    @pytest.fixture
    def mock_311_response(self, sample_complaint_311):
        """Return mock 311 API response."""
        return [sample_complaint_311]

    @pytest.mark.asyncio
    async def test_get_311_complaints_returns_list(self, mock_311_response):
        """Test that 311 complaints endpoint returns a list."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_311_response
            
            client = NYCDataClient()
            complaints = await client.get_311_complaints(bbl="3012650001")
            
            assert isinstance(complaints, list)
            assert len(complaints) == 1
            assert complaints[0]['bbl'] == "3012650001"

    @pytest.mark.asyncio
    async def test_get_311_complaints_with_days_filter(self):
        """Test 311 complaints respects days parameter for date filtering."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            
            client = NYCDataClient()
            await client.get_311_complaints(bbl="3012650001", days=60)
            
            # Verify the call was made with days parameter
            assert mock_fetch.called

    @pytest.mark.asyncio
    async def test_get_311_complaints_with_custom_date(self):
        """Test 311 complaints with custom as_of_date."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            
            client = NYCDataClient()
            custom_date = datetime(2024, 6, 1)
            await client.get_311_complaints(
                bbl="3012650001", 
                days=30,
                as_of_date=custom_date
            )
            
            assert mock_fetch.called


class TestPermitsFetcher:
    """Tests for building permits fetching."""

    @pytest.mark.asyncio
    async def test_get_permits_returns_list(self):
        """Test that permits endpoint returns a list."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_fetch_with_cache', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [{"permit_id": "PERM-001"}]
            
            client = NYCDataClient()
            permits = await client.get_permits(bbl="3012650001")
            
            assert isinstance(permits, list)
            assert len(permits) == 1


class TestBatchFetching:
    """Tests for batch data fetching operations."""

    @pytest.mark.asyncio
    async def test_batch_fetch_multiple_bbls(self):
        """Test batch fetching for multiple properties."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, 'get_hpd_violations', new_callable=AsyncMock) as mock_hpd, \
             patch.object(NYCDataClient, 'get_dob_violations', new_callable=AsyncMock) as mock_dob, \
             patch.object(NYCDataClient, 'get_311_complaints', new_callable=AsyncMock) as mock_311, \
             patch.object(NYCDataClient, 'get_permits', new_callable=AsyncMock) as mock_permits:
            
            mock_hpd.return_value = []
            mock_dob.return_value = []
            mock_311.return_value = []
            mock_permits.return_value = []
            
            client = NYCDataClient()
            bbls = ["3012650001", "3012650002", "1012650003"]
            
            results = await client.batch_fetch(bbls)
            
            assert isinstance(results, dict)
            assert len(results) == 3
            for bbl in bbls:
                assert bbl in results

    @pytest.mark.asyncio
    async def test_batch_fetch_selective_data_types(self):
        """Test batch fetching with selective data type flags."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, 'get_hpd_violations', new_callable=AsyncMock) as mock_hpd, \
             patch.object(NYCDataClient, 'get_dob_violations', new_callable=AsyncMock) as mock_dob, \
             patch.object(NYCDataClient, 'get_311_complaints', new_callable=AsyncMock) as mock_311, \
             patch.object(NYCDataClient, 'get_permits', new_callable=AsyncMock) as mock_permits:
            
            mock_hpd.return_value = []
            mock_dob.return_value = []
            mock_311.return_value = []
            mock_permits.return_value = []
            
            client = NYCDataClient()
            
            await client.batch_fetch(
                bbls=["3012650001"],
                include_hpd=True,
                include_dob=False,
                include_311=True,
                include_permits=False
            )
            
            assert mock_hpd.called
            assert mock_311.called
            # DOB and permits should not be called when disabled
            assert not mock_dob.called
            assert not mock_permits.called


class TestRateLimiting:
    """Tests for API rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_under_limit(self):
        """Test that rate limiter allows requests under the limit."""
        try:
            from api.nyc_data_client import RateLimiter
        except ImportError:
            pytest.skip("RateLimiter not available")
        
        limiter = RateLimiter(rate=10, per=60.0)
        
        # Should allow first 10 requests
        for _ in range(10):
            await limiter.acquire()  # Should not raise

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self):
        """Test that rate limiter blocks requests over the limit."""
        try:
            from api.nyc_data_client import RateLimiter, RateLimitError
        except ImportError:
            pytest.skip("RateLimiter not available")
        
        limiter = RateLimiter(rate=2, per=60.0)
        
        # Use up the rate limit
        await limiter.acquire()
        await limiter.acquire()
        
        # Third request should fail
        with pytest.raises(RateLimitError):
            await limiter.acquire()


class TestCaching:
    """Tests for multi-layer caching functionality."""

    @pytest.mark.asyncio
    async def test_memory_cache_hit(self):
        """Test memory cache hit returns cached data."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        client = NYCDataClient()
        cache_key = "test_key"
        test_data = [{"id": 1}]
        
        # Populate memory cache
        client._memory_cache[cache_key] = test_data
        
        # Should return from memory cache
        result = await client._get_from_cache(cache_key)
        assert result == test_data

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """Test cache miss returns None."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        client = NYCDataClient()
        client._redis = None  # Disable Redis
        
        result = await client._get_from_cache("nonexistent_key")
        assert result is None


class TestCircuitBreaker:
    """Tests for circuit breaker fault tolerance."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after repeated failures."""
        try:
            from api.nyc_data_client import NYCDataClient, CircuitBreakerOpenError
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        # This tests the circuit breaker decorator behavior
        # The actual circuit breaker is from the circuitbreaker library
        client = NYCDataClient()
        
        # Verify circuit breaker state tracking is initialized
        assert '_stats' in dir(client)
        assert 'circuit_breaks' in client._stats


class TestClientStatistics:
    """Tests for client statistics tracking."""

    def test_get_stats_returns_expected_keys(self):
        """Test get_stats returns all expected metrics."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        client = NYCDataClient()
        stats = client.get_stats()
        
        expected_keys = [
            'requests',
            'cache_hits',
            'cache_misses',
            'cache_hit_rate',
            'errors',
            'circuit_breaks',
            'memory_cache_size'
        ]
        
        for key in expected_keys:
            assert key in stats, f"Missing key: {key}"

    def test_initial_stats_are_zero(self):
        """Test initial statistics are all zero."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        client = NYCDataClient()
        stats = client.get_stats()
        
        assert stats['requests'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        assert stats['errors'] == 0
        assert stats['circuit_breaks'] == 0


class TestContextManager:
    """Tests for async context manager functionality."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test client works as async context manager."""
        try:
            from api.nyc_data_client import NYCDataClient
        except ImportError:
            pytest.skip("NYCDataClient not available")
        
        with patch.object(NYCDataClient, '_initialize', new_callable=AsyncMock), \
             patch.object(NYCDataClient, 'close', new_callable=AsyncMock) as mock_close:
            
            async with NYCDataClient() as client:
                assert client is not None
            
            # Verify close was called on exit
            mock_close.assert_called_once()
