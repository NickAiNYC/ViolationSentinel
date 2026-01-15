"""
Tests for Circuit Breaker implementation.

Tests cover all three states (CLOSED, OPEN, HALF_OPEN), state transitions,
thread safety, metrics tracking, and error handling.
"""

import threading
import time
import unittest
from unittest.mock import Mock, patch

from infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
)


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for CircuitBreaker class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=2,  # Short timeout for faster tests
            name="test_breaker"
        )
    
    def test_initialization(self):
        """Test circuit breaker initialization."""
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_threshold, 3)
        self.assertEqual(self.breaker.timeout, 2)
        self.assertEqual(self.breaker.name, "test_breaker")
    
    def test_successful_call(self):
        """Test successful function call through circuit breaker."""
        mock_func = Mock(return_value="success")
        
        result = self.breaker.call(mock_func, "arg1", kwarg1="value1")
        
        self.assertEqual(result, "success")
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        
        # Check metrics
        metrics = self.breaker.get_metrics()
        self.assertEqual(metrics.total_calls, 1)
        self.assertEqual(metrics.successful_calls, 1)
        self.assertEqual(metrics.failed_calls, 0)
    
    def test_failed_call(self):
        """Test failed function call."""
        mock_func = Mock(side_effect=ValueError("test error"))
        
        with self.assertRaises(ValueError):
            self.breaker.call(mock_func)
        
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        
        # Check metrics
        metrics = self.breaker.get_metrics()
        self.assertEqual(metrics.total_calls, 1)
        self.assertEqual(metrics.successful_calls, 0)
        self.assertEqual(metrics.failed_calls, 1)
    
    def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold is reached."""
        mock_func = Mock(side_effect=ValueError("test error"))
        
        # Trigger failures up to threshold
        for i in range(3):
            with self.assertRaises(ValueError):
                self.breaker.call(mock_func)
        
        # Circuit should now be OPEN
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        
        # Next call should raise CircuitBreakerOpenException
        with self.assertRaises(CircuitBreakerOpenException):
            self.breaker.call(mock_func)
        
        # Check metrics
        metrics = self.breaker.get_metrics()
        self.assertEqual(metrics.total_calls, 4)  # 3 failures + 1 rejected
        self.assertEqual(metrics.failed_calls, 3)
        self.assertEqual(metrics.rejected_calls, 1)
    
    def test_circuit_half_open_after_timeout(self):
        """Test circuit enters HALF_OPEN state after timeout."""
        mock_func = Mock(side_effect=ValueError("test error"))
        
        # Open the circuit
        for i in range(3):
            with self.assertRaises(ValueError):
                self.breaker.call(mock_func)
        
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        
        # Wait for timeout
        time.sleep(2.1)
        
        # Circuit should transition to HALF_OPEN on next call attempt
        mock_func.side_effect = None  # Make it succeed
        mock_func.return_value = "success"
        
        result = self.breaker.call(mock_func)
        
        # Should have transitioned to CLOSED after successful test
        self.assertEqual(result, "success")
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
    
    def test_circuit_reopens_on_half_open_failure(self):
        """Test circuit reopens if test in HALF_OPEN fails."""
        mock_func = Mock(side_effect=ValueError("test error"))
        
        # Open the circuit
        for i in range(3):
            with self.assertRaises(ValueError):
                self.breaker.call(mock_func)
        
        # Wait for timeout
        time.sleep(2.1)
        
        # Next call will be in HALF_OPEN, let it fail
        with self.assertRaises(ValueError):
            self.breaker.call(mock_func)
        
        # Circuit should be OPEN again
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
    
    def test_success_resets_failure_count(self):
        """Test successful call resets failure count."""
        mock_func = Mock()
        
        # Cause 2 failures (below threshold)
        mock_func.side_effect = [ValueError(), ValueError(), "success"]
        
        with self.assertRaises(ValueError):
            self.breaker.call(mock_func)
        
        with self.assertRaises(ValueError):
            self.breaker.call(mock_func)
        
        # Successful call should reset failure count
        result = self.breaker.call(mock_func)
        self.assertEqual(result, "success")
        
        # Circuit should still be CLOSED
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        
        # New failures should start from 0
        state = self.breaker.get_state()
        self.assertEqual(state['failure_count'], 0)
    
    def test_manual_reset(self):
        """Test manual reset of circuit breaker."""
        mock_func = Mock(side_effect=ValueError("test error"))
        
        # Open the circuit
        for i in range(3):
            with self.assertRaises(ValueError):
                self.breaker.call(mock_func)
        
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        
        # Manual reset
        self.breaker.reset()
        
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        state = self.breaker.get_state()
        self.assertEqual(state['failure_count'], 0)
    
    def test_decorator_usage(self):
        """Test using circuit breaker as decorator."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1, name="decorator_test")
        
        @breaker
        def test_function(x):
            if x < 0:
                raise ValueError("Negative number")
            return x * 2
        
        # Successful calls
        self.assertEqual(test_function(5), 10)
        self.assertEqual(test_function(3), 6)
        
        # Failed calls
        with self.assertRaises(ValueError):
            test_function(-1)
        
        with self.assertRaises(ValueError):
            test_function(-2)
        
        # Circuit should be OPEN
        with self.assertRaises(CircuitBreakerOpenException):
            test_function(5)
    
    def test_get_state(self):
        """Test get_state method returns complete state info."""
        state = self.breaker.get_state()
        
        self.assertIn('name', state)
        self.assertIn('state', state)
        self.assertIn('failure_count', state)
        self.assertIn('failure_threshold', state)
        self.assertIn('timeout', state)
        self.assertIn('metrics', state)
        
        self.assertEqual(state['name'], 'test_breaker')
        self.assertEqual(state['state'], 'CLOSED')
        self.assertEqual(state['failure_threshold'], 3)
    
    def test_metrics_tracking(self):
        """Test comprehensive metrics tracking."""
        mock_func = Mock()
        mock_func.side_effect = ["success", ValueError(), "success", ValueError(), ValueError()]
        
        # Execute calls
        self.breaker.call(mock_func)  # success
        
        with self.assertRaises(ValueError):
            self.breaker.call(mock_func)  # failure
        
        self.breaker.call(mock_func)  # success
        
        with self.assertRaises(ValueError):
            self.breaker.call(mock_func)  # failure
        
        with self.assertRaises(ValueError):
            self.breaker.call(mock_func)  # failure (opens circuit)
        
        # Check metrics
        metrics = self.breaker.get_metrics()
        self.assertEqual(metrics.total_calls, 5)
        self.assertEqual(metrics.successful_calls, 2)
        self.assertEqual(metrics.failed_calls, 3)
        self.assertIsNotNone(metrics.last_success_time)
        self.assertIsNotNone(metrics.last_failure_time)
    
    def test_thread_safety(self):
        """Test circuit breaker is thread-safe."""
        results = []
        errors = []
        
        def worker():
            try:
                result = self.breaker.call(lambda: time.sleep(0.01) or "success")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All calls should succeed
        self.assertEqual(len(results), 10)
        self.assertEqual(len(errors), 0)
        
        metrics = self.breaker.get_metrics()
        self.assertEqual(metrics.total_calls, 10)
        self.assertEqual(metrics.successful_calls, 10)
    
    def test_state_transitions_logged(self):
        """Test state transitions are properly logged in metrics."""
        mock_func = Mock(side_effect=ValueError("test error"))
        
        initial_transitions = self.breaker.get_metrics().state_transitions
        
        # Open the circuit (CLOSED -> OPEN)
        for i in range(3):
            with self.assertRaises(ValueError):
                self.breaker.call(mock_func)
        
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        
        # Wait for timeout and recover (OPEN -> HALF_OPEN -> CLOSED)
        time.sleep(2.1)
        mock_func.side_effect = None
        mock_func.return_value = "success"
        self.breaker.call(mock_func)
        
        # Should have had 3 transitions: CLOSED->OPEN, OPEN->HALF_OPEN, HALF_OPEN->CLOSED
        final_transitions = self.breaker.get_metrics().state_transitions
        self.assertEqual(final_transitions - initial_transitions, 3)


def run_tests():
    """Run all tests."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCircuitBreaker)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
