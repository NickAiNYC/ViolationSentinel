"""
Production WebSocket server for real-time property monitoring.

This module provides a scalable WebSocket server that supports 10,000+ concurrent
connections for real-time updates on property violations and compliance data.
"""

import asyncio
import json
import time
import jwt
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
from collections import deque
import logging

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WebSocketServerProtocol = object
    WEBSOCKETS_AVAILABLE = False

try:
    from prometheus_client import Counter, Gauge, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Create dummy metrics if prometheus not available
    PROMETHEUS_AVAILABLE = False
    class DummyMetric:
        def labels(self, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def dec(self, *args, **kwargs):
            pass
    Counter = Gauge = Histogram = lambda *args, **kwargs: DummyMetric()

# Configure logging
logger = logging.getLogger(__name__)

# Prometheus Metrics
CONNECTIONS_TOTAL = Counter(
    'websocket_connections_total',
    'Total number of WebSocket connections',
    ['status']
)
ACTIVE_CONNECTIONS = Gauge(
    'websocket_active_connections',
    'Number of active WebSocket connections'
)
MESSAGES_TOTAL = Counter(
    'websocket_messages_total',
    'Total number of WebSocket messages',
    ['type', 'direction']
)
MESSAGE_LATENCY = Histogram(
    'websocket_message_duration_seconds',
    'WebSocket message processing latency',
    ['type']
)
SUBSCRIPTION_COUNT = Gauge(
    'websocket_subscriptions_total',
    'Total number of active subscriptions',
    ['property_id']
)


class WebSocketError(Exception):
    """Base exception for WebSocket errors."""
    pass


class AuthenticationError(WebSocketError):
    """Raised when authentication fails."""
    pass


class RateLimitError(WebSocketError):
    """Raised when rate limit is exceeded."""
    pass


class MessageValidationError(WebSocketError):
    """Raised when message validation fails."""
    pass


class RateLimiter:
    """Per-connection rate limiter."""
    
    def __init__(self, max_messages: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_messages: Maximum messages allowed per window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.messages: deque = deque()
    
    def check_rate_limit(self) -> bool:
        """
        Check if rate limit is exceeded.
        
        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        
        # Remove old messages outside the window
        while self.messages and self.messages[0] < now - self.window_seconds:
            self.messages.popleft()
        
        # Check if limit exceeded
        if len(self.messages) >= self.max_messages:
            return False
        
        # Add new message timestamp
        self.messages.append(now)
        return True


class Connection:
    """Represents a WebSocket connection."""
    
    def __init__(
        self,
        websocket: WebSocketServerProtocol,
        connection_id: str,
        authenticated: bool = False,
        user_id: Optional[str] = None,
    ):
        """
        Initialize connection.
        
        Args:
            websocket: WebSocket protocol instance
            connection_id: Unique connection identifier
            authenticated: Whether connection is authenticated
            user_id: User identifier if authenticated
        """
        self.websocket = websocket
        self.connection_id = connection_id
        self.authenticated = authenticated
        self.user_id = user_id
        self.subscriptions: Set[str] = set()
        self.rate_limiter = RateLimiter()
        self.connected_at = time.time()
        self.last_ping = time.time()
        self.message_queue: deque = deque(maxlen=100)  # Store last 100 messages
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send message to client.
        
        Args:
            message: Message dictionary
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await self.websocket.send(json.dumps(message))
            MESSAGES_TOTAL.labels(type=message.get('type', 'unknown'), direction='outbound').inc()
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {self.connection_id}: {e}")
            return False
    
    def add_to_queue(self, message: Dict[str, Any]):
        """Add message to offline queue."""
        self.message_queue.append({
            'message': message,
            'timestamp': time.time(),
        })


class WebSocketServer:
    """
    Production WebSocket server for real-time property monitoring.
    
    Features:
    - Support for 10,000+ concurrent connections
    - JWT authentication
    - Per-connection rate limiting
    - Automatic reconnection handling
    - Heartbeat/keepalive
    - Graceful connection cleanup
    - Message queue for offline clients
    - Prometheus metrics
    """
    
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 8765,
        jwt_secret: str = 'your-secret-key',
        heartbeat_interval: int = 30,
        max_connections: int = 10000,
        rate_limit_messages: int = 100,
        rate_limit_window: int = 60,
    ):
        """
        Initialize WebSocket server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            jwt_secret: Secret key for JWT validation
            heartbeat_interval: Ping interval in seconds
            max_connections: Maximum concurrent connections
            rate_limit_messages: Max messages per window
            rate_limit_window: Rate limit window in seconds
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets library is required. Install with: pip install websockets")
        
        self.host = host
        self.port = port
        self.jwt_secret = jwt_secret
        self.heartbeat_interval = heartbeat_interval
        self.max_connections = max_connections
        self.rate_limit_messages = rate_limit_messages
        self.rate_limit_window = rate_limit_window
        
        # Connection tracking
        self.connections: Dict[str, Connection] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # property_id -> set of connection_ids
        
        # Server state
        self.server = None
        self.running = False
        self.heartbeat_task = None
        
        logger.info(
            "WebSocketServer initialized",
            extra={
                'host': host,
                'port': port,
                'max_connections': max_connections,
            }
        )
    
    def _validate_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate incoming message.
        
        Args:
            message: Message dictionary
        
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if 'type' not in message:
            return False
        
        # Validate message type
        valid_types = ['SUBSCRIBE', 'UNSUBSCRIBE', 'GET_STATUS', 'PING', 'AUTHENTICATE']
        if message['type'] not in valid_types:
            return False
        
        # Type-specific validation
        if message['type'] in ['SUBSCRIBE', 'UNSUBSCRIBE']:
            if 'property_id' not in message:
                return False
        
        return True
    
    def _sanitize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize message to prevent injection attacks.
        
        Args:
            message: Message dictionary
        
        Returns:
            Sanitized message
        """
        # Create a clean copy with only allowed fields
        sanitized = {
            'type': str(message.get('type', '')),
        }
        
        if 'property_id' in message:
            # Sanitize property_id to alphanumeric only
            property_id = str(message['property_id'])
            sanitized['property_id'] = ''.join(c for c in property_id if c.isalnum())
        
        if 'token' in message:
            sanitized['token'] = str(message['token'])
        
        return sanitized
    
    async def _handle_authenticate(self, conn: Connection, message: Dict[str, Any]):
        """Handle AUTHENTICATE message."""
        token = message.get('token')
        if not token:
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Token required',
            })
            return
        
        payload = self._validate_jwt(token)
        if not payload:
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Invalid or expired token',
            })
            return
        
        # Update connection with authentication info
        conn.authenticated = True
        conn.user_id = payload.get('user_id')
        
        await conn.send_message({
            'type': 'AUTHENTICATED',
            'user_id': conn.user_id,
        })
        
        logger.info(f"Connection {conn.connection_id} authenticated as {conn.user_id}")
    
    async def _handle_subscribe(self, conn: Connection, message: Dict[str, Any]):
        """Handle SUBSCRIBE message."""
        if not conn.authenticated:
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Authentication required',
            })
            return
        
        property_id = message.get('property_id')
        if not property_id:
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Property ID required',
            })
            return
        
        # Add subscription
        conn.subscriptions.add(property_id)
        
        if property_id not in self.subscriptions:
            self.subscriptions[property_id] = set()
        self.subscriptions[property_id].add(conn.connection_id)
        
        SUBSCRIPTION_COUNT.labels(property_id=property_id).inc()
        
        await conn.send_message({
            'type': 'SUBSCRIBED',
            'property_id': property_id,
        })
        
        logger.info(f"Connection {conn.connection_id} subscribed to {property_id}")
    
    async def _handle_unsubscribe(self, conn: Connection, message: Dict[str, Any]):
        """Handle UNSUBSCRIBE message."""
        property_id = message.get('property_id')
        if not property_id:
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Property ID required',
            })
            return
        
        # Remove subscription
        conn.subscriptions.discard(property_id)
        
        if property_id in self.subscriptions:
            self.subscriptions[property_id].discard(conn.connection_id)
            if not self.subscriptions[property_id]:
                del self.subscriptions[property_id]
            SUBSCRIPTION_COUNT.labels(property_id=property_id).dec()
        
        await conn.send_message({
            'type': 'UNSUBSCRIBED',
            'property_id': property_id,
        })
        
        logger.info(f"Connection {conn.connection_id} unsubscribed from {property_id}")
    
    async def _handle_get_status(self, conn: Connection, message: Dict[str, Any]):
        """Handle GET_STATUS message."""
        status = {
            'type': 'STATUS',
            'connection_id': conn.connection_id,
            'authenticated': conn.authenticated,
            'subscriptions': list(conn.subscriptions),
            'connected_at': conn.connected_at,
            'uptime': time.time() - conn.connected_at,
        }
        
        await conn.send_message(status)
    
    async def _handle_ping(self, conn: Connection, message: Dict[str, Any]):
        """Handle PING message."""
        conn.last_ping = time.time()
        await conn.send_message({'type': 'PONG'})
    
    async def _handle_message(self, conn: Connection, raw_message: str):
        """
        Handle incoming message from client.
        
        Args:
            conn: Connection instance
            raw_message: Raw message string
        """
        start_time = time.time()
        
        try:
            # Parse message
            message = json.loads(raw_message)
            MESSAGES_TOTAL.labels(type=message.get('type', 'unknown'), direction='inbound').inc()
            
            # Validate message
            if not self._validate_message(message):
                raise MessageValidationError("Invalid message format")
            
            # Sanitize message
            message = self._sanitize_message(message)
            
            # Check rate limit
            if not conn.rate_limiter.check_rate_limit():
                raise RateLimitError("Rate limit exceeded")
            
            # Route message to handler
            message_type = message['type']
            
            if message_type == 'AUTHENTICATE':
                await self._handle_authenticate(conn, message)
            elif message_type == 'SUBSCRIBE':
                await self._handle_subscribe(conn, message)
            elif message_type == 'UNSUBSCRIBE':
                await self._handle_unsubscribe(conn, message)
            elif message_type == 'GET_STATUS':
                await self._handle_get_status(conn, message)
            elif message_type == 'PING':
                await self._handle_ping(conn, message)
            
            # Record latency
            duration = time.time() - start_time
            MESSAGE_LATENCY.labels(type=message_type).observe(duration)
        
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {conn.connection_id}")
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Invalid JSON',
            })
        
        except MessageValidationError as e:
            logger.warning(f"Message validation failed from {conn.connection_id}: {e}")
            await conn.send_message({
                'type': 'ERROR',
                'message': str(e),
            })
        
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for {conn.connection_id}")
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Rate limit exceeded',
            })
        
        except Exception as e:
            logger.error(f"Error handling message from {conn.connection_id}: {e}", exc_info=True)
            await conn.send_message({
                'type': 'ERROR',
                'message': 'Internal server error',
            })
    
    async def _connection_handler(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle WebSocket connection.
        
        Args:
            websocket: WebSocket protocol instance
            path: Connection path
        """
        # Check connection limit
        if len(self.connections) >= self.max_connections:
            logger.warning(f"Connection limit reached: {len(self.connections)}")
            await websocket.close(1008, "Server at capacity")
            CONNECTIONS_TOTAL.labels(status='rejected').inc()
            return
        
        # Create connection
        connection_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}:{time.time()}"
        conn = Connection(websocket, connection_id)
        self.connections[connection_id] = conn
        
        CONNECTIONS_TOTAL.labels(status='accepted').inc()
        ACTIVE_CONNECTIONS.inc()
        
        logger.info(f"New connection: {connection_id}")
        
        try:
            # Send welcome message
            await conn.send_message({
                'type': 'WELCOME',
                'connection_id': connection_id,
                'server_time': time.time(),
            })
            
            # Handle messages
            async for message in websocket:
                await self._handle_message(conn, message)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {connection_id}")
        
        except Exception as e:
            logger.error(f"Error in connection handler for {connection_id}: {e}", exc_info=True)
        
        finally:
            # Cleanup connection
            await self._cleanup_connection(connection_id)
    
    async def _cleanup_connection(self, connection_id: str):
        """
        Clean up connection resources.
        
        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.connections:
            return
        
        conn = self.connections[connection_id]
        
        # Remove all subscriptions
        for property_id in list(conn.subscriptions):
            if property_id in self.subscriptions:
                self.subscriptions[property_id].discard(connection_id)
                if not self.subscriptions[property_id]:
                    del self.subscriptions[property_id]
                SUBSCRIPTION_COUNT.labels(property_id=property_id).dec()
        
        # Remove connection
        del self.connections[connection_id]
        ACTIVE_CONNECTIONS.dec()
        
        logger.info(f"Connection cleaned up: {connection_id}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat pings to all connections."""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Send ping to all connections
                for conn_id, conn in list(self.connections.items()):
                    try:
                        await conn.send_message({'type': 'PING'})
                    except Exception as e:
                        logger.warning(f"Failed to send heartbeat to {conn_id}: {e}")
                
                logger.debug(f"Heartbeat sent to {len(self.connections)} connections")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
    
    async def broadcast(self, property_id: str, message: Dict[str, Any]):
        """
        Broadcast message to all subscribers of a property.
        
        Args:
            property_id: Property identifier
            message: Message to broadcast
        """
        if property_id not in self.subscriptions:
            return
        
        subscribers = self.subscriptions[property_id].copy()
        
        for conn_id in subscribers:
            if conn_id not in self.connections:
                continue
            
            conn = self.connections[conn_id]
            success = await conn.send_message(message)
            
            # Queue message if send failed
            if not success:
                conn.add_to_queue(message)
        
        logger.debug(f"Broadcast to {len(subscribers)} subscribers of {property_id}")
    
    async def start(self):
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets library is required")
        
        self.running = True
        
        # Start server
        self.server = await websockets.serve(
            self._connection_handler,
            self.host,
            self.port,
            max_size=10 * 1024 * 1024,  # 10MB max message size
            max_queue=1000,
            ping_interval=None,  # We handle pings manually
        )
        
        # Start heartbeat loop
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
    
    async def stop(self):
        """Stop the WebSocket server."""
        logger.info("Stopping WebSocket server...")
        
        self.running = False
        
        # Cancel heartbeat
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for conn_id in list(self.connections.keys()):
            conn = self.connections[conn_id]
            try:
                await conn.websocket.close()
            except Exception:
                pass
            await self._cleanup_connection(conn_id)
        
        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("WebSocket server stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get server statistics.
        
        Returns:
            Dictionary with server statistics
        """
        return {
            'active_connections': len(self.connections),
            'total_subscriptions': sum(len(subs) for subs in self.subscriptions.values()),
            'unique_properties': len(self.subscriptions),
            'authenticated_connections': sum(1 for c in self.connections.values() if c.authenticated),
            'running': self.running,
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


# Admin endpoints helper functions
async def get_connection_info(server: WebSocketServer, connection_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a specific connection."""
    if connection_id not in server.connections:
        return None
    
    conn = server.connections[connection_id]
    return {
        'connection_id': conn.connection_id,
        'authenticated': conn.authenticated,
        'user_id': conn.user_id,
        'subscriptions': list(conn.subscriptions),
        'connected_at': conn.connected_at,
        'uptime': time.time() - conn.connected_at,
        'last_ping': conn.last_ping,
        'message_queue_size': len(conn.message_queue),
    }


async def disconnect_connection(server: WebSocketServer, connection_id: str) -> bool:
    """Forcefully disconnect a connection."""
    if connection_id not in server.connections:
        return False
    
    conn = server.connections[connection_id]
    try:
        await conn.websocket.close(1000, "Disconnected by admin")
        await server._cleanup_connection(connection_id)
        return True
    except Exception as e:
        logger.error(f"Failed to disconnect {connection_id}: {e}")
        return False


# Example usage
if __name__ == "__main__":
    async def main():
        # Create server
        server = WebSocketServer(
            host='0.0.0.0',
            port=8765,
            jwt_secret='your-secret-key-change-this',
            heartbeat_interval=30,
            max_connections=10000,
        )
        
        try:
            # Start server
            await server.start()
            
            logger.info("WebSocket server running. Press Ctrl+C to stop.")
            
            # Keep server running
            while True:
                await asyncio.sleep(10)
                stats = server.get_stats()
                logger.info(f"Server stats: {stats}")
        
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        
        finally:
            await server.stop()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
