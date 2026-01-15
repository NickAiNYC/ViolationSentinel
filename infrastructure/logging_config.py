"""
Production-grade structured logging configuration for ViolationSentinel.

This module provides comprehensive logging setup with JSON formatting, log rotation,
contextual logging, and request tracing capabilities.
"""

import logging
import logging.config
import logging.handlers
import os
import sys
import time
import functools
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from contextvars import ContextVar
import json

try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None


# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class ContextualFilter(logging.Filter):
    """Add contextual information to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to the log record."""
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter if jsonlogger else logging.Formatter):
    """
    Custom JSON formatter with enhanced metadata.
    Falls back to standard formatter if python-json-logger is not installed.
    """
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to JSON log record."""
        if jsonlogger:
            super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger_name'] = record.name
        log_record['function_name'] = record.funcName
        log_record['line_number'] = record.lineno
        log_record['module'] = record.module
        
        # Add contextual fields if available
        if hasattr(record, 'request_id') and record.request_id:
            log_record['request_id'] = record.request_id
        if hasattr(record, 'user_id') and record.user_id:
            log_record['user_id'] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON or plain text."""
        if not jsonlogger:
            # Fallback to standard formatting if python-json-logger not available
            return super().format(record)
        
        return super().format(record)


class PrettyConsoleFormatter(logging.Formatter):
    """Pretty-printed formatter for console output in development."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Format level with color
        level = f"{color}{record.levelname:8s}{reset}"
        
        # Format logger name
        logger_name = f"{record.name:20s}"
        
        # Format location
        location = f"{record.filename}:{record.lineno}"
        
        # Add request_id if available
        request_id = getattr(record, 'request_id', None)
        request_str = f" [{request_id}]" if request_id else ""
        
        # Format message
        message = record.getMessage()
        
        # Combine all parts
        formatted = f"{timestamp} | {level} | {logger_name} | {location:30s}{request_str} | {message}"
        
        # Add exception if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted


def setup_logging(
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    environment: Optional[str] = None,
) -> None:
    """
    Set up production-grade logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   Defaults to LOG_LEVEL env var or INFO.
        log_dir: Directory for log files. Defaults to LOG_DIR env var or './logs'.
        environment: Environment name (development, production).
                     Defaults to ENVIRONMENT env var or 'development'.
    
    Example:
        >>> setup_logging(log_level='INFO', environment='production')
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    # Get configuration from environment or defaults
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO').upper()
    log_dir = log_dir or os.getenv('LOG_DIR', './logs')
    environment = environment or os.getenv('ENVIRONMENT', 'development').lower()
    
    # Create log directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Determine if we should use JSON formatting (production) or pretty (development)
    use_json = environment == 'production'
    
    # Base configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'filters': {
            'contextual': {
                '()': ContextualFilter,
            },
        },
        'formatters': {
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(timestamp)s %(level)s %(logger_name)s %(message)s',
            } if jsonlogger else {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
            'pretty': {
                '()': PrettyConsoleFormatter,
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'pretty' if not use_json else 'json',
                'stream': 'ext://sys.stdout',
                'filters': ['contextual'],
            },
            'app_file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': log_level,
                'formatter': 'json' if use_json else 'simple',
                'filename': str(log_path / 'app.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8',
                'filters': ['contextual'],
            },
            'error_file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'json' if use_json else 'simple',
                'filename': str(log_path / 'error.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8',
                'filters': ['contextual'],
            },
            'api_file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': log_level,
                'formatter': 'json' if use_json else 'simple',
                'filename': str(log_path / 'api.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8',
                'filters': ['contextual'],
            },
            'model_file': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': log_level,
                'formatter': 'json' if use_json else 'simple',
                'filename': str(log_path / 'model.log'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8',
                'filters': ['contextual'],
            },
        },
        'loggers': {
            # Root logger
            '': {
                'level': log_level,
                'handlers': ['console', 'app_file', 'error_file'],
            },
            # API logger
            'api': {
                'level': log_level,
                'handlers': ['console', 'api_file', 'error_file'],
                'propagate': False,
            },
            # Model logger
            'model': {
                'level': log_level,
                'handlers': ['console', 'model_file', 'error_file'],
                'propagate': False,
            },
            # NYC Data Client logger
            'api.nyc_data_client': {
                'level': log_level,
                'handlers': ['console', 'api_file', 'error_file'],
                'propagate': False,
            },
            # Third-party loggers (less verbose)
            'aiohttp': {
                'level': 'WARNING',
            },
            'urllib3': {
                'level': 'WARNING',
            },
            'asyncio': {
                'level': 'WARNING',
            },
        },
    }
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Log configuration info
    root_logger = logging.getLogger()
    root_logger.info(
        "Logging configured",
        extra={
            'log_level': log_level,
            'log_dir': str(log_path),
            'environment': environment,
            'json_logging': use_json,
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name, typically __name__ from the calling module.
    
    Returns:
        Configured logger instance.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request")
    """
    return logging.getLogger(name)


def set_request_context(request_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
    """
    Set contextual information for request tracing.
    
    Args:
        request_id: Unique request identifier (correlation ID).
        user_id: User identifier for the current request.
    
    Example:
        >>> import uuid
        >>> set_request_context(request_id=str(uuid.uuid4()), user_id="user123")
        >>> logger = get_logger(__name__)
        >>> logger.info("User action")  # Will include request_id and user_id
    """
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """
    Clear contextual information for request tracing.
    
    Example:
        >>> clear_request_context()
    """
    request_id_var.set(None)
    user_id_var.set(None)


def log_execution_time(func: Optional[Callable] = None, *, logger: Optional[logging.Logger] = None) -> Callable:
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to decorate (used when decorator is called without arguments).
        logger: Logger instance to use (defaults to function's module logger).
    
    Example:
        >>> @log_execution_time
        >>> def process_data():
        >>>     # ... processing ...
        >>>     pass
        
        >>> @log_execution_time(logger=get_logger(__name__))
        >>> async def fetch_data():
        >>>     # ... fetching ...
        >>>     pass
    """
    def decorator(f: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(f.__module__)
        
        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"Function {f.__name__} completed",
                    extra={
                        'function': f.__name__,
                        'duration_seconds': round(duration, 3),
                        'success': True,
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Function {f.__name__} failed",
                    extra={
                        'function': f.__name__,
                        'duration_seconds': round(duration, 3),
                        'success': False,
                        'error': str(e),
                    },
                    exc_info=True
                )
                raise
        
        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await f(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(
                    f"Function {f.__name__} completed",
                    extra={
                        'function': f.__name__,
                        'duration_seconds': round(duration, 3),
                        'success': True,
                    }
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Function {f.__name__} failed",
                    extra={
                        'function': f.__name__,
                        'duration_seconds': round(duration, 3),
                        'success': False,
                        'error': str(e),
                    },
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(f):
            return async_wrapper
        else:
            return sync_wrapper
    
    # Handle both @log_execution_time and @log_execution_time()
    if func is None:
        return decorator
    else:
        return decorator(func)


def log_exceptions(func: Optional[Callable] = None, *, logger: Optional[logging.Logger] = None, reraise: bool = True) -> Callable:
    """
    Decorator to automatically log exceptions.
    
    Args:
        func: Function to decorate (used when decorator is called without arguments).
        logger: Logger instance to use (defaults to function's module logger).
        reraise: Whether to reraise the exception after logging (default: True).
    
    Example:
        >>> @log_exceptions
        >>> def risky_operation():
        >>>     # ... may raise exception ...
        >>>     pass
        
        >>> @log_exceptions(logger=get_logger(__name__), reraise=False)
        >>> def safe_operation():
        >>>     # ... exception will be logged but not reraised ...
        >>>     pass
    """
    def decorator(f: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(f.__module__)
        
        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {f.__name__}: {str(e)}",
                    extra={
                        'function': f.__name__,
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                    },
                    exc_info=True
                )
                if reraise:
                    raise
        
        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            try:
                return await f(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {f.__name__}: {str(e)}",
                    extra={
                        'function': f.__name__,
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                    },
                    exc_info=True
                )
                if reraise:
                    raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(f):
            return async_wrapper
        else:
            return sync_wrapper
    
    # Handle both @log_exceptions and @log_exceptions()
    if func is None:
        return decorator
    else:
        return decorator(func)


# Example usage for documentation
if __name__ == "__main__":
    # Setup logging
    setup_logging(log_level='DEBUG', environment='development')
    
    # Get logger
    logger = get_logger(__name__)
    
    # Basic logging
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Contextual logging
    import uuid
    set_request_context(request_id=str(uuid.uuid4()), user_id="user123")
    logger.info("Processing user request")
    clear_request_context()
    
    # Using decorators
    @log_execution_time
    def example_function():
        """Example function with execution time logging."""
        time.sleep(0.1)
        return "success"
    
    @log_exceptions
    def risky_function():
        """Example function with exception logging."""
        raise ValueError("Something went wrong")
    
    # Test decorators
    result = example_function()
    logger.info(f"Function returned: {result}")
    
    try:
        risky_function()
    except ValueError:
        pass
    
    logger.info("Logging examples completed")
