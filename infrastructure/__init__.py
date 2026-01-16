"""
Infrastructure module for ViolationSentinel.

Provides core infrastructure utilities including logging configuration and caching.
"""

from .logging_config import (
    setup_logging,
    get_logger,
    set_request_context,
    clear_request_context,
    log_execution_time,
    log_exceptions,
)
from .cache import (
    CacheManager,
    cached,
    CacheError,
    CacheConnectionError,
    CacheSerializationError,
)

__all__ = [
    # Logging
    'setup_logging',
    'get_logger',
    'set_request_context',
    'clear_request_context',
    'log_execution_time',
    'log_exceptions',
    # Caching
    'CacheManager',
    'cached',
    'CacheError',
    'CacheConnectionError',
    'CacheSerializationError',
]
