# Monitoring Module - Real-Time WebSocket Server

## Overview

Production-grade WebSocket server for real-time property monitoring with support for 10,000+ concurrent connections.

## Features

✅ **High Scalability** - Support for 10,000+ concurrent connections  
✅ **JWT Authentication** - Secure token-based authentication  
✅ **Per-Connection Rate Limiting** - Prevent abuse (100 messages/60s default)  
✅ **Automatic Reconnection** - Client reconnection handling  
✅ **Heartbeat/Keepalive** - Ping every 30 seconds  
✅ **Graceful Cleanup** - Proper connection resource cleanup  
✅ **Message Queue** - Store last 100 messages for offline clients  
✅ **Selective Broadcasting** - Send updates only to subscribed clients  
✅ **Connection Statistics** - Track all connection metrics  
✅ **Structured Logging** - Log all connection events  
✅ **Prometheus Metrics** - Export connection and message metrics  
✅ **Admin Endpoints** - Connection management functions  

## Installation

Install required dependencies:

```bash
pip install websockets>=12.0 PyJWT>=2.8.0
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Quick Start

### Server-Side

```python
import asyncio
from monitoring import WebSocketServer

async def main():
    # Create server
    server = WebSocketServer(
        host='0.0.0.0',
        port=8765,
        jwt_secret='your-secret-key-change-this',
        heartbeat_interval=30,
        max_connections=10000,
    )
    
    # Start server
    await server.start()
    print("WebSocket server running on ws://localhost:8765")
    
    # Broadcast update to property subscribers
    await server.broadcast(
        property_id='1012650001',
        message={
            'type': 'VIOLATION_UPDATE',
            'property_id': '1012650001',
            'new_violations': 5,
            'timestamp': time.time(),
        }
    )
    
    # Keep running
    await asyncio.sleep(3600)
    
    # Stop server
    await server.stop()

asyncio.run(main())
```

### Client-Side

```python
import asyncio
import json
import jwt
from datetime import datetime, timedelta
import websockets

async def main():
    # Generate JWT token
    token = jwt.encode(
        {
            'user_id': 'user123',
            'exp': datetime.utcnow() + timedelta(hours=1),
        },
        'your-secret-key',
        algorithm='HS256'
    )
    
    # Connect to server
    async with websockets.connect('ws://localhost:8765') as websocket:
        # Receive welcome message
        welcome = json.loads(await websocket.recv())
        print(f"Connected: {welcome}")
        
        # Authenticate
        await websocket.send(json.dumps({
            'type': 'AUTHENTICATE',
            'token': token,
        }))
        auth_response = json.loads(await websocket.recv())
        print(f"Authenticated: {auth_response}")
        
        # Subscribe to property
        await websocket.send(json.dumps({
            'type': 'SUBSCRIBE',
            'property_id': '1012650001',
        }))
        sub_response = json.loads(await websocket.recv())
        print(f"Subscribed: {sub_response}")
        
        # Listen for updates
        while True:
            message = json.loads(await websocket.recv())
            print(f"Received: {message}")

asyncio.run(main())
```

## Message Types

### Client → Server

#### AUTHENTICATE
Authenticate the connection with JWT token.

```json
{
  "type": "AUTHENTICATE",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "type": "AUTHENTICATED",
  "user_id": "user123"
}
```

#### SUBSCRIBE
Subscribe to property updates.

```json
{
  "type": "SUBSCRIBE",
  "property_id": "1012650001"
}
```

**Response:**
```json
{
  "type": "SUBSCRIBED",
  "property_id": "1012650001"
}
```

#### UNSUBSCRIBE
Unsubscribe from property updates.

```json
{
  "type": "UNSUBSCRIBE",
  "property_id": "1012650001"
}
```

**Response:**
```json
{
  "type": "UNSUBSCRIBED",
  "property_id": "1012650001"
}
```

#### GET_STATUS
Get connection status.

```json
{
  "type": "GET_STATUS"
}
```

**Response:**
```json
{
  "type": "STATUS",
  "connection_id": "127.0.0.1:12345:1234567890.123",
  "authenticated": true,
  "subscriptions": ["1012650001", "2012650001"],
  "connected_at": 1234567890.123,
  "uptime": 120.5
}
```

#### PING
Send ping to server (server also sends automatic pings).

```json
{
  "type": "PING"
}
```

**Response:**
```json
{
  "type": "PONG"
}
```

### Server → Client

#### WELCOME
Sent upon connection.

```json
{
  "type": "WELCOME",
  "connection_id": "127.0.0.1:12345:1234567890.123",
  "server_time": 1234567890.123
}
```

#### VIOLATION_UPDATE
Property violation update (example).

```json
{
  "type": "VIOLATION_UPDATE",
  "property_id": "1012650001",
  "violation_type": "DOB",
  "count": 5,
  "timestamp": 1234567890.123
}
```

#### ERROR
Error message.

```json
{
  "type": "ERROR",
  "message": "Rate limit exceeded"
}
```

## Configuration

### Constructor Parameters

```python
WebSocketServer(
    host='0.0.0.0',                 # Host to bind to
    port=8765,                       # Port to listen on
    jwt_secret='your-secret-key',    # JWT secret key
    heartbeat_interval=30,           # Ping interval (seconds)
    max_connections=10000,           # Maximum concurrent connections
    rate_limit_messages=100,         # Max messages per window
    rate_limit_window=60,            # Rate limit window (seconds)
)
```

### Environment Variables

Set these in production:

- `JWT_SECRET`: Secret key for JWT validation (required)
- `WEBSOCKET_PORT`: Port to listen on (default: 8765)
- `WEBSOCKET_HOST`: Host to bind to (default: 0.0.0.0)
- `MAX_CONNECTIONS`: Maximum concurrent connections (default: 10000)

## API Reference

### `WebSocketServer`

Main WebSocket server class.

#### Methods

##### `async start()`
Start the WebSocket server.

##### `async stop()`
Stop the server and cleanup all connections.

##### `async broadcast(property_id: str, message: Dict[str, Any])`
Broadcast message to all subscribers of a property.

**Parameters:**
- `property_id`: Property identifier
- `message`: Message dictionary to broadcast

##### `get_stats() -> Dict[str, Any]`
Get server statistics.

**Returns:**
```python
{
    'active_connections': 150,
    'total_subscriptions': 300,
    'unique_properties': 75,
    'authenticated_connections': 145,
    'running': True
}
```

### Admin Functions

#### `async get_connection_info(server: WebSocketServer, connection_id: str)`
Get detailed information about a connection.

#### `async disconnect_connection(server: WebSocketServer, connection_id: str)`
Forcefully disconnect a connection.

## Error Handling

### Custom Exceptions

- `WebSocketError` - Base exception
- `AuthenticationError` - Authentication failure
- `RateLimitError` - Rate limit exceeded
- `MessageValidationError` - Invalid message format

### Error Responses

All errors return:
```json
{
  "type": "ERROR",
  "message": "Error description"
}
```

## Rate Limiting

Each connection is rate-limited to prevent abuse:

- **Default:** 100 messages per 60 seconds
- **Configurable** via constructor parameters
- **Per-connection** tracking
- **Automatic enforcement** with error responses

Example error when limit exceeded:
```json
{
  "type": "ERROR",
  "message": "Rate limit exceeded"
}
```

## Authentication

JWT-based authentication with standard claims:

```python
import jwt
from datetime import datetime, timedelta

token = jwt.encode(
    {
        'user_id': 'user123',
        'exp': datetime.utcnow() + timedelta(hours=1),
    },
    'your-secret-key',
    algorithm='HS256'
)
```

## Monitoring

### Prometheus Metrics

The server exports metrics for monitoring:

- `websocket_connections_total{status}` - Total connections (accepted/rejected)
- `websocket_active_connections` - Current active connections
- `websocket_messages_total{type, direction}` - Total messages (inbound/outbound)
- `websocket_message_duration_seconds{type}` - Message processing latency
- `websocket_subscriptions_total{property_id}` - Active subscriptions per property

### Example Prometheus Queries

```promql
# Active connections
websocket_active_connections

# Message rate
rate(websocket_messages_total[5m])

# Average message latency
rate(websocket_message_duration_seconds_sum[5m]) / rate(websocket_message_duration_seconds_count[5m])

# Subscription count
sum(websocket_subscriptions_total) by (property_id)
```

## Best Practices

### Production Deployment

1. **Use SSL/TLS**: Always use `wss://` in production
2. **Strong JWT Secret**: Use environment variable, min 32 characters
3. **Rate Limiting**: Adjust based on your use case
4. **Connection Limits**: Monitor and adjust max_connections
5. **Heartbeat Interval**: Balance between responsiveness and overhead
6. **Message Queue Size**: Adjust based on offline client needs
7. **Load Balancing**: Use sticky sessions for WebSocket connections
8. **Monitoring**: Set up alerts on connection/error metrics

### Security

1. **JWT Expiration**: Set reasonable expiration times
2. **Input Validation**: All messages are validated and sanitized
3. **Rate Limiting**: Prevent DoS attacks
4. **Connection Limits**: Prevent resource exhaustion
5. **Authentication**: Require authentication before subscriptions
6. **Message Size**: Limited to 10MB by default

### Performance

1. **Async Operations**: All I/O is non-blocking
2. **Connection Pooling**: Efficient resource usage
3. **Selective Broadcasting**: Only send to subscribed clients
4. **Message Queuing**: Store messages for offline clients
5. **Graceful Shutdown**: Clean connection cleanup

## Examples

See `example_websocket_usage.py` for comprehensive examples including:

- Basic server setup
- Client connection with authentication
- Property subscriptions
- Real-time updates
- Multiple concurrent clients
- Admin functions
- Rate limiting demonstration
- Broadcasting to subscribers

## Integration with NYC Data Client

```python
from api.nyc_data_client import NYCDataClient
from monitoring import WebSocketServer

async def monitor_property(server: WebSocketServer):
    """Monitor property and broadcast updates."""
    async with NYCDataClient() as client:
        while True:
            # Fetch latest violations
            violations = await client.get_dob_violations('1012650001')
            
            # Broadcast to subscribers
            await server.broadcast(
                property_id='1012650001',
                message={
                    'type': 'VIOLATION_UPDATE',
                    'property_id': '1012650001',
                    'count': len(violations),
                    'timestamp': time.time(),
                }
            )
            
            await asyncio.sleep(300)  # Check every 5 minutes
```

## Troubleshooting

### Connection Issues

- **Cannot connect**: Check firewall and port availability
- **Connection drops**: Verify heartbeat_interval is appropriate
- **Authentication fails**: Verify JWT secret matches

### Performance Issues

- **High latency**: Check network, reduce message size
- **Memory usage**: Reduce max_connections or message_queue size
- **CPU usage**: Reduce heartbeat frequency

### Rate Limiting

- **Unexpected rate limits**: Check rate_limit_messages setting
- **Legitimate traffic blocked**: Increase rate limits

## License

MIT License - See LICENSE file for details.
