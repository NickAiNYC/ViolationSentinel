"""
Demo script to test WebSocket integration with Landlord Dashboard.

This script simulates the WebSocket server sending updates that the
dashboard would receive in real-time.
"""

import asyncio
import json
import time
from monitoring import WebSocketServer
from infrastructure import setup_logging, get_logger

# Setup logging
setup_logging(log_level='INFO', environment='development')
logger = get_logger(__name__)


async def demo_websocket_with_dashboard():
    """
    Demo: Simulate real-time property updates for dashboard.
    
    This demonstrates how the landlord dashboard would receive
    real-time updates via WebSocket when violations change.
    """
    logger.info("=" * 70)
    logger.info("Demo: WebSocket Integration with Landlord Dashboard")
    logger.info("=" * 70)
    
    # Create WebSocket server
    server = WebSocketServer(
        host='0.0.0.0',
        port=8765,
        jwt_secret='demo-secret-key',
        heartbeat_interval=30,
        max_connections=1000,
    )
    
    await server.start()
    logger.info("WebSocket server started on ws://localhost:8765")
    logger.info("Dashboard should connect automatically when opened")
    
    # Wait for connections
    await asyncio.sleep(3)
    
    # Simulate property updates
    properties = ['1012650001', '2012650001', '3012650001']
    
    logger.info("\nSimulating real-time property updates...")
    
    for i in range(10):
        # Pick a random property
        import random
        property_id = random.choice(properties)
        
        # Simulate different types of updates
        update_types = [
            {
                'type': 'VIOLATION_UPDATE',
                'property_id': property_id,
                'violation_type': 'DOB',
                'count': random.randint(5, 15),
                'new_violations': random.randint(0, 3),
                'severity': 'medium' if i % 3 != 0 else 'critical',
                'timestamp': time.time(),
                'message': f"DOB violation count updated: {random.randint(5, 15)} total"
            },
            {
                'type': 'VIOLATION_UPDATE',
                'property_id': property_id,
                'violation_type': 'HPD',
                'count': random.randint(8, 20),
                'new_violations': random.randint(0, 2),
                'severity': 'medium',
                'timestamp': time.time(),
                'message': f"HPD violation count updated: {random.randint(8, 20)} total"
            },
            {
                'type': 'VIOLATION_UPDATE',
                'property_id': property_id,
                'violation_type': '311',
                'count': random.randint(10, 30),
                'new_complaints': random.randint(0, 5),
                'severity': 'low',
                'timestamp': time.time(),
                'message': f"311 complaints updated: {random.randint(10, 30)} in last 30 days"
            }
        ]
        
        update = random.choice(update_types)
        
        # Broadcast to subscribers
        await server.broadcast(property_id, update)
        
        logger.info(f"Update #{i+1}: {update['type']} for {property_id} - {update['message']}")
        
        if update['severity'] == 'critical':
            logger.warning(f"⚠️  CRITICAL violation detected for property {property_id}!")
        
        # Wait before next update
        await asyncio.sleep(3)
    
    logger.info("\nDemo completed. Keeping server running...")
    logger.info("Press Ctrl+C to stop the server")
    
    # Keep server running
    try:
        while True:
            await asyncio.sleep(10)
            
            # Show stats periodically
            stats = server.get_stats()
            logger.info(f"Server stats: {stats['active_connections']} connections, "
                       f"{stats['total_subscriptions']} subscriptions")
    
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    
    finally:
        await server.stop()
        logger.info("Server stopped")


async def test_connection():
    """Simple test to verify WebSocket server is accessible."""
    logger.info("=" * 70)
    logger.info("Test: WebSocket Server Connection")
    logger.info("=" * 70)
    
    server = WebSocketServer(host='0.0.0.0', port=8765, jwt_secret='test')
    
    try:
        await server.start()
        logger.info("✅ Server started successfully on ws://localhost:8765")
        
        # Check stats
        stats = server.get_stats()
        logger.info(f"✅ Server stats: {stats}")
        
        # Keep running briefly
        logger.info("Waiting for connections...")
        await asyncio.sleep(5)
        
        stats = server.get_stats()
        logger.info(f"Final stats: {stats}")
    
    except Exception as e:
        logger.error(f"❌ Server failed: {e}")
    
    finally:
        await server.stop()
        logger.info("Server stopped")


async def main():
    """Run demo."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        await test_connection()
    else:
        await demo_websocket_with_dashboard()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("LANDLORD DASHBOARD - WEBSOCKET INTEGRATION DEMO")
    print("=" * 70)
    print("\nThis demo shows real-time updates for the landlord dashboard.")
    print("\nTo use:")
    print("1. Run this script: python demo_dashboard_websocket.py")
    print("2. Open landlord dashboard: streamlit run landlord_dashboard.py")
    print("3. Add properties with BBLs: 1012650001, 2012650001, 3012650001")
    print("4. Watch real-time updates appear automatically!")
    print("\n" + "=" * 70 + "\n")
    
    asyncio.run(main())
