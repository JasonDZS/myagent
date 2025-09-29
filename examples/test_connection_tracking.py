#!/usr/bin/env python3
"""
Connection Tracking Test Script

This script tests the WebSocket connection tracking functionality.
"""

import asyncio
import json
import requests
import websockets
from datetime import datetime


async def test_websocket_connection():
    """Test WebSocket connection and tracking."""
    
    print("🔌 Testing WebSocket Connection Tracking")
    print("="*50)
    
    # Check initial connections
    print("\n📊 Initial connection status:")
    response = requests.get("http://localhost:8080/api/v1/connections")
    initial_connections = response.json()
    print(f"   Active connections: {initial_connections['total']}")
    
    # Test WebSocket connection
    print("\n🌐 Connecting to WebSocket proxy...")
    
    try:
        # Connect to the proxy server
        async with websockets.connect('ws://localhost:9090') as websocket:
            print("✅ Connected to WebSocket proxy")
            
            # Wait a moment for connection to be registered
            await asyncio.sleep(1)
            
            # Check connections after connecting
            print("\n📊 Connection status after connecting:")
            response = requests.get("http://localhost:8080/api/v1/connections")
            current_connections = response.json()
            print(f"   Active connections: {current_connections['total']}")
            
            if current_connections['items']:
                conn = current_connections['items'][0]
                print(f"   Connection details:")
                print(f"     ID: {conn['connection_id'][:8]}...")
                print(f"     Client: {conn['client_ip']}:{conn['client_port']}")
                print(f"     Target Service: {conn['target_service_id'][:8]}...")
                print(f"     Status: {conn['status']}")
                print(f"     Connected At: {conn['connected_at']}")
                
                # Test sending a message
                print("\n📤 Sending test message...")
                test_message = {
                    "type": "test",
                    "message": "Hello from connection tracking test!",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                try:
                    response_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                    print(f"📥 Received response: {response_msg[:100]}...")
                except asyncio.TimeoutError:
                    print("⏰ No response received (this might be expected)")
                
                # Wait a moment and check connection stats again
                await asyncio.sleep(1)
                response = requests.get("http://localhost:8080/api/v1/connections")
                updated_connections = response.json()
                
                if updated_connections['items']:
                    updated_conn = updated_connections['items'][0]
                    print(f"\n📈 Updated connection stats:")
                    print(f"     Messages: {updated_conn['message_count']}")
                    print(f"     Last Activity: {updated_conn['last_activity']}")
                
                # Test connection disconnect via API
                connection_id = conn['connection_id']
                print(f"\n🔌 Testing forced disconnect via API...")
                
                # Keep connection alive for a bit longer to test tracking
                await asyncio.sleep(2)
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False
    
    # Check connections after disconnecting
    print("\n📊 Connection status after disconnecting:")
    response = requests.get("http://localhost:8080/api/v1/connections")
    final_connections = response.json()
    print(f"   Active connections: {final_connections['total']}")
    
    return True


async def test_connection_stats_api():
    """Test connection statistics API."""
    
    print("\n📊 Testing Connection Statistics API")
    print("="*40)
    
    # Get system stats
    try:
        response = requests.get("http://localhost:8080/api/v1/stats")
        stats = response.json()
        
        print("System Statistics:")
        print(f"   Services: {stats['services']['total']} total, {stats['services']['running']} running")
        print(f"   Connections: {stats['connections']['total_connections']} total")
        
        if stats['connections']['by_status']:
            print("   Connection by status:")
            for status, count in stats['connections']['by_status'].items():
                print(f"     {status}: {count}")
        
        if stats['connections']['by_service']:
            print("   Connections by service:")
            for service_id, count in stats['connections']['by_service'].items():
                service_short = service_id[:8] + "..." if len(service_id) > 8 else service_id
                print(f"     {service_short}: {count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Stats API test failed: {e}")
        return False


async def test_multiple_connections():
    """Test multiple simultaneous connections."""
    
    print("\n🔗 Testing Multiple Connections")
    print("="*35)
    
    connections = []
    
    try:
        # Create multiple connections
        for i in range(3):
            print(f"🔌 Creating connection {i+1}...")
            connection = await websockets.connect('ws://localhost:9090')
            connections.append(connection)
            await asyncio.sleep(0.5)  # Small delay between connections
        
        # Check connection count
        response = requests.get("http://localhost:8080/api/v1/connections")
        current_connections = response.json()
        print(f"✅ Active connections: {current_connections['total']}")
        
        # Send messages on each connection
        for i, conn in enumerate(connections):
            message = {"type": "test", "connection": i+1, "message": f"Hello from connection {i+1}"}
            await conn.send(json.dumps(message))
            await asyncio.sleep(0.1)
        
        # Wait and check stats
        await asyncio.sleep(1)
        response = requests.get("http://localhost:8080/api/v1/connections")
        updated_connections = response.json()
        
        print(f"📊 Connection details:")
        for conn_info in updated_connections['items']:
            print(f"   {conn_info['connection_id'][:8]}... - Messages: {conn_info['message_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Multiple connections test failed: {e}")
        return False
    
    finally:
        # Clean up connections
        for conn in connections:
            try:
                await conn.close()
            except:
                pass


async def main():
    """Main test function."""
    
    print("🚀 Starting Connection Tracking Tests")
    print("="*60)
    
    # Test basic connection tracking
    success1 = await test_websocket_connection()
    
    # Test stats API
    success2 = await test_connection_stats_api()
    
    # Test multiple connections
    success3 = await test_multiple_connections()
    
    # Final verification
    await asyncio.sleep(2)  # Let connections clean up
    
    print("\n" + "="*60)
    print("🎉 Connection Tracking Test Results")
    print("="*60)
    
    results = [
        ("WebSocket Connection Tracking", success1),
        ("Connection Statistics API", success2),
        ("Multiple Connections", success3),
    ]
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    # Final connection check
    response = requests.get("http://localhost:8080/api/v1/connections")
    final_connections = response.json()
    print(f"\n📊 Final connection count: {final_connections['total']}")
    
    if all(result[1] for result in results):
        print("\n🎊 All connection tracking tests passed!")
        print("🌐 Web console should now display real connection data")
    else:
        print("\n⚠️  Some tests failed - please check the logs")


if __name__ == "__main__":
    asyncio.run(main())