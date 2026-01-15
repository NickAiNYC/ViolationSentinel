"""
Example: Using the production WebSocket server for real-time property monitoring.

This example demonstrates both server-side and client-side usage of the WebSocket
server including authentication, subscriptions, and real-time updates.
"""

import asyncio
import json
import jwt
import time
from datetime import datetime, timedelta

# Server-side example
from monitoring import WebSocketServer
from infrastructure import setup_logging, get_logger

# Setup logging
setup_logging(log_level='INFO', environment='development')
logger = get_logger(__name__)


async def example_server():
    """Example: Running the WebSocket server."""
    logger.info("=" * 70)
    logger.info("Example 1: WebSocket Server")
    logger.info("=" * 70)
    
    # Create and start server
    server = WebSocketServer(
        host='0.0.0.0',
        port=8765,
        jwt_secret='demo-secret-key-change-in-production',
        heartbeat_interval=30,
        max_connections=10000,
        rate_limit_messages=100,
        rate_limit_window=60,
    )
    
    await server.start()
    logger.info(f"WebSocket server running on ws://localhost:8765")
    
    # Simulate broadcasting updates
    async def broadcast_updates():
        """Simulate sending property updates."""
        await asyncio.sleep(5)  # Wait for connections
        
        for i in range(5):
            # Broadcast violation update
            await server.broadcast(
                property_id='1012650001',
                message={
                    'type': 'VIOLATION_UPDATE',
                    'property_id': '1012650001',
                    'violation_type': 'DOB',
                    'count': 5 + i,
                    'timestamp': time.time(),
                }
            )
            logger.info(f"Broadcast update #{i + 1} to subscribers")
            await asyncio.sleep(2)
    
    # Start broadcasting task
    broadcast_task = asyncio.create_task(broadcast_updates())
    
    # Run for 15 seconds
    await asyncio.sleep(15)
    
    # Get statistics
    stats = server.get_stats()
    logger.info(f"Server stats: {stats}")
    
    # Stop server
    await server.stop()
    broadcast_task.cancel()
    
    logger.info("Server stopped")


async def example_client():
    """Example: WebSocket client connecting to server."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: WebSocket Client")
    logger.info("=" * 70)
    
    try:
        import websockets
    except ImportError:
        logger.warning("websockets library not available, skipping client example")
        return
    
    # Generate JWT token
    jwt_secret = 'demo-secret-key-change-in-production'
    token = jwt.encode(
        {
            'user_id': 'demo_user_123',
            'exp': datetime.utcnow() + timedelta(hours=1),
        },
        jwt_secret,
        algorithm='HS256'
    )
    
    try:
        # Connect to server
        async with websockets.connect('ws://localhost:8765') as websocket:
            logger.info("Connected to WebSocket server")
            
            # Receive welcome message
            welcome = json.loads(await websocket.recv())
            logger.info(f"Received: {welcome}")
            
            # Authenticate
            await websocket.send(json.dumps({
                'type': 'AUTHENTICATE',
                'token': token,
            }))
            auth_response = json.loads(await websocket.recv())
            logger.info(f"Authentication: {auth_response}")
            
            # Subscribe to property
            await websocket.send(json.dumps({
                'type': 'SUBSCRIBE',
                'property_id': '1012650001',
            }))
            sub_response = json.loads(await websocket.recv())
            logger.info(f"Subscription: {sub_response}")
            
            # Get status
            await websocket.send(json.dumps({
                'type': 'GET_STATUS',
            }))
            status = json.loads(await websocket.recv())
            logger.info(f"Status: {status}")
            
            # Listen for updates
            logger.info("Listening for updates...")
            try:
                async with asyncio.timeout(10):
                    while True:
                        message = json.loads(await websocket.recv())
                        logger.info(f"Received update: {message}")
            except asyncio.TimeoutError:
                logger.info("Listening timeout")
            
            # Unsubscribe
            await websocket.send(json.dumps({
                'type': 'UNSUBSCRIBE',
                'property_id': '1012650001',
            }))
            unsub_response = json.loads(await websocket.recv())
            logger.info(f"Unsubscribed: {unsub_response}")
    
    except Exception as e:
        logger.error(f"Client error: {e}")


async def example_multiple_clients():
    """Example: Multiple clients with subscriptions."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Multiple Clients")
    logger.info("=" * 70)
    
    try:
        import websockets
    except ImportError:
        logger.warning("websockets library not available, skipping example")
        return
    
    jwt_secret = 'demo-secret-key-change-in-production'
    
    async def client_connection(client_id: str, property_ids: list):
        """Simulate a client connection."""
        token = jwt.encode(
            {
                'user_id': f'user_{client_id}',
                'exp': datetime.utcnow() + timedelta(hours=1),
            },
            jwt_secret,
            algorithm='HS256'
        )
        
        try:
            async with websockets.connect('ws://localhost:8765') as websocket:
                # Receive welcome
                await websocket.recv()
                
                # Authenticate
                await websocket.send(json.dumps({
                    'type': 'AUTHENTICATE',
                    'token': token,
                }))
                await websocket.recv()
                
                # Subscribe to properties
                for prop_id in property_ids:
                    await websocket.send(json.dumps({
                        'type': 'SUBSCRIBE',
                        'property_id': prop_id,
                    }))
                    await websocket.recv()
                
                logger.info(f"Client {client_id} subscribed to {len(property_ids)} properties")
                
                # Listen for updates
                try:
                    async with asyncio.timeout(8):
                        while True:
                            message = json.loads(await websocket.recv())
                            if message['type'] not in ['PING', 'PONG']:
                                logger.info(f"Client {client_id} received: {message['type']}")
                except asyncio.TimeoutError:
                    pass
        
        except Exception as e:
            logger.error(f"Client {client_id} error: {e}")
    
    # Create multiple clients
    clients = [
        client_connection('1', ['1012650001', '2012650001']),
        client_connection('2', ['1012650001']),
        client_connection('3', ['3012650001']),
    ]
    
    await asyncio.gather(*clients)
    logger.info("All clients completed")


async def example_admin_functions():
    """Example: Admin functions for connection management."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Admin Functions")
    logger.info("=" * 70)
    
    from monitoring import get_connection_info, disconnect_connection
    
    server = WebSocketServer(
        host='0.0.0.0',
        port=8765,
        jwt_secret='demo-secret-key',
    )
    
    await server.start()
    logger.info("Server started")
    
    # Wait for connections (would normally have real connections)
    await asyncio.sleep(2)
    
    # Get server statistics
    stats = server.get_stats()
    logger.info(f"Server statistics: {stats}")
    
    # List all connections
    logger.info(f"Active connections: {len(server.connections)}")
    for conn_id in server.connections:
        info = await get_connection_info(server, conn_id)
        logger.info(f"  {conn_id}: {info}")
    
    # Simulate disconnecting a connection
    if server.connections:
        conn_id = list(server.connections.keys())[0]
        success = await disconnect_connection(server, conn_id)
        logger.info(f"Disconnected {conn_id}: {success}")
    
    await server.stop()


async def example_rate_limiting():
    """Example: Rate limiting demonstration."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 5: Rate Limiting")
    logger.info("=" * 70)
    
    try:
        import websockets
    except ImportError:
        logger.warning("websockets library not available, skipping example")
        return
    
    jwt_secret = 'demo-secret-key-change-in-production'
    token = jwt.encode(
        {
            'user_id': 'rate_limit_test',
            'exp': datetime.utcnow() + timedelta(hours=1),
        },
        jwt_secret,
        algorithm='HS256'
    )
    
    try:
        async with websockets.connect('ws://localhost:8765') as websocket:
            # Receive welcome
            await websocket.recv()
            
            # Authenticate
            await websocket.send(json.dumps({
                'type': 'AUTHENTICATE',
                'token': token,
            }))
            await websocket.recv()
            
            # Send many messages to trigger rate limit
            logger.info("Sending rapid messages to test rate limiting...")
            for i in range(150):  # Exceeds default 100/60s limit
                await websocket.send(json.dumps({
                    'type': 'GET_STATUS',
                }))
                
                try:
                    response = json.loads(await websocket.recv())
                    if response.get('type') == 'ERROR' and 'rate limit' in response.get('message', '').lower():
                        logger.info(f"Rate limit triggered after {i + 1} messages")
                        break
                except Exception:
                    pass
    
    except Exception as e:
        logger.error(f"Rate limit test error: {e}")


async def example_broadcast_to_subscribers():
    """Example: Broadcasting updates to specific property subscribers."""
    logger.info("\n" + "=" * 70)
    logger.info("Example 6: Broadcasting to Subscribers")
    logger.info("=" * 70)
    
    server = WebSocketServer(host='0.0.0.0', port=8765, jwt_secret='demo-secret')
    await server.start()
    
    # Simulate property update events
    properties_to_update = ['1012650001', '2012650001', '3012650001']
    
    for prop_id in properties_to_update:
        update_message = {
            'type': 'VIOLATION_UPDATE',
            'property_id': prop_id,
            'new_violations': 3,
            'total_violations': 15,
            'severity': 'medium',
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        await server.broadcast(prop_id, update_message)
        logger.info(f"Broadcast update for property {prop_id}")
    
    await asyncio.sleep(1)
    await server.stop()


async def main():
    """Run all examples."""
    logger.info("\n" + "=" * 70)
    logger.info("WEBSOCKET SERVER EXAMPLES")
    logger.info("=" * 70)
    logger.info("\nThese examples demonstrate the production WebSocket server")
    logger.info("for real-time property monitoring and updates.")
    
    # Note: These examples need to be run separately or with proper
    # coordination since they all try to use the same port
    
    logger.info("\nRun individual examples by uncommenting below:")
    
    # Example 1: Basic server
    # await example_server()
    
    # Example 2: Client connection (requires server running)
    # await example_client()
    
    # Example 3: Multiple clients (requires server running)
    # await example_multiple_clients()
    
    # Example 4: Admin functions
    await example_admin_functions()
    
    # Example 5: Rate limiting (requires server running)
    # await example_rate_limiting()
    
    # Example 6: Broadcasting
    await example_broadcast_to_subscribers()
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ Examples completed!")
    logger.info("=" * 70)
    logger.info("\nTo use in production:")
    logger.info("1. Set strong JWT_SECRET environment variable")
    logger.info("2. Configure appropriate rate limits")
    logger.info("3. Use SSL/TLS (wss://) in production")
    logger.info("4. Monitor connection metrics with Prometheus")
    logger.info("5. Set up proper authentication backend")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
