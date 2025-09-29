#!/usr/bin/env python3
"""
Debug WebSocket Connection Issues

This script helps debug WebSocket connection problems.
"""

import asyncio
import json
import websockets
from datetime import datetime


async def test_direct_service_connection():
    """Test direct connection to the weather service."""
    
    print("🎯 Testing Direct Service Connection")
    print("="*40)
    
    try:
        # Connect directly to the weather service
        async with websockets.connect('ws://localhost:8084') as websocket:
            print("✅ Connected directly to weather service")
            
            # Send a test message
            test_message = {
                "type": "weather", 
                "location": "Beijing",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📤 Sending: {json.dumps(test_message)}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"📥 Received: {response}")
                return True
            except asyncio.TimeoutError:
                print("⏰ No response received within timeout")
                return False
                
    except Exception as e:
        print(f"❌ Direct connection failed: {e}")
        return False


async def test_proxy_connection_with_debug():
    """Test proxy connection with detailed debugging."""
    
    print("\n🔗 Testing Proxy Connection (Debug Mode)")
    print("="*45)
    
    try:
        # Connect to proxy with debug info
        print("🔌 Attempting to connect to proxy...")
        
        async with websockets.connect('ws://localhost:9090') as websocket:
            print("✅ Connected to proxy server")
            
            # Wait for system messages
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"📥 Welcome message: {welcome_msg}")
            except asyncio.TimeoutError:
                print("⏰ No welcome message received")
            
            # Send a test message
            test_message = {
                "type": "weather",
                "location": "Shanghai", 
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📤 Sending via proxy: {json.dumps(test_message)}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                print(f"📥 Received via proxy: {response}")
                return True
            except asyncio.TimeoutError:
                print("⏰ No response received via proxy")
                return False
                
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Proxy connection closed: {e}")
        return False
    except Exception as e:
        print(f"❌ Proxy connection failed: {e}")
        return False


async def test_simple_proxy_connection():
    """Test very simple proxy connection."""
    
    print("\n🔍 Testing Simple Proxy Connection")
    print("="*35)
    
    try:
        print("🔌 Connecting to proxy...")
        
        # Simple connection test
        websocket = await websockets.connect('ws://localhost:9090')
        print("✅ Proxy connection established")
        
        # Keep connection alive briefly
        await asyncio.sleep(2)
        print("⏱️  Connection held for 2 seconds")
        
        await websocket.close()
        print("🔌 Connection closed gracefully")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple proxy test failed: {e}")
        return False


async def main():
    """Main debug function."""
    
    print("🐛 WebSocket Connection Debug Test")
    print("="*50)
    
    # Test 1: Direct service connection
    direct_success = await test_direct_service_connection()
    
    # Test 2: Proxy connection with debug
    proxy_success = await test_proxy_connection_with_debug()
    
    # Test 3: Simple proxy connection
    simple_success = await test_simple_proxy_connection()
    
    # Summary
    print("\n" + "="*50)
    print("🔍 Debug Test Results")
    print("="*50)
    
    results = [
        ("Direct Service Connection", direct_success),
        ("Proxy Connection (Debug)", proxy_success),
        ("Simple Proxy Connection", simple_success),
    ]
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    if direct_success and not proxy_success:
        print("\n💡 Diagnosis: Service works, but proxy has issues")
        print("   - Check proxy server logs")
        print("   - Verify routing configuration")
        print("   - Check service discovery")
    elif not direct_success:
        print("\n💡 Diagnosis: Service itself has issues")
        print("   - Check if weather service is properly running")
        print("   - Verify service configuration")


if __name__ == "__main__":
    asyncio.run(main())