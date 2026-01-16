"""
Monitoring module for ViolationSentinel.

Provides real-time monitoring and WebSocket communication capabilities.
"""

from .websocket_server import (
    WebSocketServer,
    WebSocketError,
    AuthenticationError,
    RateLimitError,
    MessageValidationError,
    get_connection_info,
    disconnect_connection,
)

__all__ = [
    'WebSocketServer',
    'WebSocketError',
    'AuthenticationError',
    'RateLimitError',
    'MessageValidationError',
    'get_connection_info',
    'disconnect_connection',
]
