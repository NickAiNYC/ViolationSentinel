"""
Circuit Breaker Pattern Implementation for NYC Open Data API Calls.

This module implements a production-grade circuit breaker pattern to handle
transient failures in external API calls (NYC Open Data). The circuit breaker
prevents cascading failures and provides automatic recovery.

The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests fail fast
- HALF_OPEN: Testing if service has recovered

Author: ViolationSentinel Team
Date: 2026-01-15
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """
    Circuit breaker states.
    
    CLOSED: Circuit is closed, requests pass through normally.
    OPEN: Circuit is open, requests fail fast without calling the underlying service.
    HALF_OPEN: Circuit is testing recovery, allows one request through.
    """
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """
    Exception raised when circuit breaker is OPEN.
    
    This exception indicates that the circuit breaker has detected too many
    failures and is preventing requests from reaching the underlying service.
    """
    pass


@dataclass
class CircuitBreakerMetrics:
    """
    Metrics for circuit breaker monitoring.
    
    Attributes:
        total_calls: Total number of calls attempted
        successful_calls: Number of successful calls
        failed_calls: Number of failed calls
        rejected_calls: Number of calls rejected (circuit open)
        state_transitions: Number of state transitions
        time_in_closed: Total time spent in CLOSED state (seconds)
        time_in_open: Total time spent in OPEN state (seconds)
        time_in_half_open: Total time spent in HALF_OPEN state (seconds)
        last_failure_time: Timestamp of last failure
        last_success_time: Timestamp of last success
    """
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_transitions: int = 0
    time_in_closed: float = 0.0
    time_in_open: float = 0.0
    time_in_half_open: float = 0.0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation.
    
    The circuit breaker monitors the success/failure of function calls and
    automatically opens the circuit when a failure threshold is reached.
    After a cooldown period, it enters HALF_OPEN state to test recovery.
    
    Usage:
        ```python
        breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        
        # Wrap a function
        @breaker
        def fetch_violations(bbl):
            response = requests.get(f"https://api.nyc.gov/violations/{bbl}")
            response.raise_for_status()
            return response.json()
        
        # Or use as context manager
        try:
            result = breaker.call(fetch_violations, "1234567890")
        except CircuitBreakerOpenException:
            logger.error("Circuit breaker is open, service unavailable")
            # Handle gracefully, use cached data, etc.
        ```
    
    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit
        timeout: Cooldown period in seconds before attempting recovery
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        name: str = "default"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            timeout: Cooldown period in seconds before testing recovery
            name: Name for this circuit breaker (for logging/monitoring)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        
        # State management
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state_entered_time = time.time()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Metrics
        self._metrics = CircuitBreakerMetrics()
        
        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={timeout}s"
        )
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get detailed state information.
        
        Returns:
            Dictionary containing state, failure count, and timing info
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "timeout": self.timeout,
                "last_failure_time": self._last_failure_time,
                "time_since_state_change": time.time() - self._state_entered_time,
                "metrics": {
                    "total_calls": self._metrics.total_calls,
                    "successful_calls": self._metrics.successful_calls,
                    "failed_calls": self._metrics.failed_calls,
                    "rejected_calls": self._metrics.rejected_calls,
                    "state_transitions": self._metrics.state_transitions,
                    "success_rate": (
                        self._metrics.successful_calls / self._metrics.total_calls
                        if self._metrics.total_calls > 0 else 0.0
                    )
                }
            }
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """
        Get circuit breaker metrics.
        
        Returns:
            CircuitBreakerMetrics object with detailed statistics
        """
        with self._lock:
            # Update time in current state
            time_in_state = time.time() - self._state_entered_time
            if self._state == CircuitState.CLOSED:
                self._metrics.time_in_closed += time_in_state
            elif self._state == CircuitState.OPEN:
                self._metrics.time_in_open += time_in_state
            elif self._state == CircuitState.HALF_OPEN:
                self._metrics.time_in_half_open += time_in_state
            
            self._state_entered_time = time.time()
            
            return self._metrics
    
    def reset(self):
        """
        Manually reset circuit breaker to CLOSED state.
        
        This method should be used carefully, typically only for:
        - Manual intervention after diagnosing and fixing issues
        - Testing purposes
        - Administrative override
        """
        with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._record_state_transition(old_state, CircuitState.CLOSED)
            
            logger.warning(
                f"CircuitBreaker '{self.name}' manually reset from {old_state.value} to CLOSED"
            )
    
    def _record_state_transition(self, from_state: CircuitState, to_state: CircuitState):
        """Record a state transition in metrics."""
        self._metrics.state_transitions += 1
        
        # Update time in previous state
        time_in_state = time.time() - self._state_entered_time
        if from_state == CircuitState.CLOSED:
            self._metrics.time_in_closed += time_in_state
        elif from_state == CircuitState.OPEN:
            self._metrics.time_in_open += time_in_state
        elif from_state == CircuitState.HALF_OPEN:
            self._metrics.time_in_half_open += time_in_state
        
        self._state_entered_time = time.time()
        
        logger.info(
            f"CircuitBreaker '{self.name}' state transition: "
            f"{from_state.value} -> {to_state.value} "
            f"(failures={self._failure_count}/{self.failure_threshold})"
        )
    
    def _check_and_update_state(self):
        """
        Check if circuit should transition to HALF_OPEN after timeout.
        
        This method is called before each request to determine if enough
        time has passed since the circuit opened.
        """
        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None:
                time_since_failure = time.time() - self._last_failure_time
                if time_since_failure >= self.timeout:
                    # Transition to HALF_OPEN for testing
                    old_state = self._state
                    self._state = CircuitState.HALF_OPEN
                    self._record_state_transition(old_state, CircuitState.HALF_OPEN)
                    logger.info(
                        f"CircuitBreaker '{self.name}' entering HALF_OPEN state "
                        f"after {time_since_failure:.1f}s cooldown"
                    )
    
    def _on_success(self):
        """Handle successful call."""
        with self._lock:
            self._metrics.successful_calls += 1
            self._metrics.last_success_time = datetime.now()
            
            if self._state == CircuitState.HALF_OPEN:
                # Success in HALF_OPEN, close circuit
                old_state = self._state
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._record_state_transition(old_state, CircuitState.CLOSED)
                logger.info(
                    f"CircuitBreaker '{self.name}' recovered: HALF_OPEN -> CLOSED"
                )
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                if self._failure_count > 0:
                    logger.debug(
                        f"CircuitBreaker '{self.name}' resetting failure count "
                        f"from {self._failure_count} after success"
                    )
                    self._failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """Handle failed call."""
        with self._lock:
            self._metrics.failed_calls += 1
            self._metrics.last_failure_time = datetime.now()
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                # Failure in HALF_OPEN, reopen circuit
                old_state = self._state
                self._state = CircuitState.OPEN
                self._failure_count = self.failure_threshold  # Max out failures
                self._record_state_transition(old_state, CircuitState.OPEN)
                logger.warning(
                    f"CircuitBreaker '{self.name}' test failed in HALF_OPEN, "
                    f"reopening circuit. Error: {str(exception)}"
                )
            elif self._state == CircuitState.CLOSED:
                # Increment failure count
                self._failure_count += 1
                logger.warning(
                    f"CircuitBreaker '{self.name}' failure {self._failure_count}/"
                    f"{self.failure_threshold}: {str(exception)}"
                )
                
                if self._failure_count >= self.failure_threshold:
                    # Open circuit
                    old_state = self._state
                    self._state = CircuitState.OPEN
                    self._record_state_transition(old_state, CircuitState.OPEN)
                    logger.error(
                        f"CircuitBreaker '{self.name}' OPENED after "
                        f"{self._failure_count} consecutive failures. "
                        f"Cooldown: {self.timeout}s"
                    )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
        
        Returns:
            Result of function call
        
        Raises:
            CircuitBreakerOpenException: If circuit is OPEN
            Exception: Any exception raised by the function
        
        Example:
            ```python
            breaker = CircuitBreaker()
            
            def fetch_data(url):
                response = requests.get(url)
                response.raise_for_status()
                return response.json()
            
            try:
                data = breaker.call(fetch_data, "https://api.example.com/data")
            except CircuitBreakerOpenException:
                # Use cached data or return error
                data = get_cached_data()
            ```
        """
        with self._lock:
            self._metrics.total_calls += 1
            self._check_and_update_state()
            
            if self._state == CircuitState.OPEN:
                # Reject request immediately
                self._metrics.rejected_calls += 1
                time_until_half_open = (
                    self.timeout - (time.time() - self._last_failure_time)
                    if self._last_failure_time else self.timeout
                )
                
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry in {time_until_half_open:.1f}s"
                )
        
        # Execute function outside lock to avoid holding lock during I/O
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise
    
    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to wrap functions with circuit breaker.
        
        Usage:
            ```python
            breaker = CircuitBreaker(failure_threshold=3, timeout=30)
            
            @breaker
            def fetch_violations(bbl):
                response = requests.get(f"https://api.nyc.gov/violations/{bbl}")
                response.raise_for_status()
                return response.json()
            
            # Function is now protected by circuit breaker
            try:
                violations = fetch_violations("1234567890")
            except CircuitBreakerOpenException:
                logger.error("Service unavailable")
            ```
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper


# Example usage and integration
if __name__ == "__main__":
    import requests
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create circuit breaker for NYC Open Data API
    nyc_api_breaker = CircuitBreaker(
        failure_threshold=5,
        timeout=60,
        name="nyc_open_data_api"
    )
    
    @nyc_api_breaker
    def fetch_nyc_violations(bbl: str) -> Dict:
        """Fetch violations from NYC Open Data API."""
        url = f"https://data.cityofnewyork.us/resource/violations.json?bbl={bbl}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    
    # Simulate API calls
    print("Testing circuit breaker with NYC Open Data API...\n")
    
    for i in range(10):
        try:
            print(f"Request {i+1}:")
            # This will fail if API is down, triggering circuit breaker
            data = fetch_nyc_violations("1234567890")
            print(f"  ✓ Success: Retrieved {len(data)} records")
        except CircuitBreakerOpenException as e:
            print(f"  ✗ Circuit OPEN: {e}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        # Show circuit state
        state = nyc_api_breaker.get_state()
        print(f"  State: {state['state']}, Failures: {state['failure_count']}/{state['failure_threshold']}")
        print()
        
        time.sleep(2)
    
    # Show final metrics
    print("\nFinal Metrics:")
    metrics = nyc_api_breaker.get_metrics()
    print(f"  Total calls: {metrics.total_calls}")
    print(f"  Successful: {metrics.successful_calls}")
    print(f"  Failed: {metrics.failed_calls}")
    print(f"  Rejected: {metrics.rejected_calls}")
    print(f"  State transitions: {metrics.state_transitions}")
