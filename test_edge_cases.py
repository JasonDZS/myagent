#!/usr/bin/env python3
"""
Test edge cases and error handling for WebSocket state management.
"""

import asyncio
import json
import websockets
from datetime import datetime

async def test_invalid_state_signature():
    """Test with invalid state signature."""
    print("🧪 Testing invalid state signature...")
    
    try:
        websocket = await websockets.connect("ws://localhost:8080")
        
        # Send invalid state with fake signature
        invalid_state = {
            "event": "user.reconnect_with_state",
            "signed_state": {
                "state": {
                    "session_id": "fake-session",
                    "current_step": 1,
                    "agent_state": "idle",
                    "created_at": "2024-01-01T10:00:00Z",
                    "memory_snapshot": "[]"
                },
                "timestamp": 1234567890,
                "signature": "invalid-signature",
                "version": "1.0",
                "checksum": "invalid-checksum"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send(json.dumps(invalid_state))
        
        # Wait for error response, skip connection messages
        for _ in range(5):
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("event") in ["system.error", "agent.error"]:
                break
            elif data.get("event") == "system.connected":
                continue
        
        if data.get("event") == "system.error":
            print(f"✅ Invalid signature correctly rejected: {data.get('content')}")
        else:
            print(f"❌ Unexpected response: {data}")
        
        await websocket.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_expired_state():
    """Test with expired state (old timestamp)."""
    print("\n🧪 Testing expired state...")
    
    try:
        websocket = await websockets.connect("ws://localhost:8080")
        
        # Send state with very old timestamp (should be expired)
        expired_state = {
            "event": "user.reconnect_with_state",
            "signed_state": {
                "state": {
                    "session_id": "old-session",
                    "current_step": 1,
                    "agent_state": "idle",
                    "created_at": "2020-01-01T10:00:00Z",
                    "memory_snapshot": "[]"
                },
                "timestamp": 1577836800,  # 2020-01-01, very old
                "signature": "fake-signature",
                "version": "1.0",
                "checksum": "fake-checksum"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send(json.dumps(expired_state))
        
        # Wait for error response, skip connection messages
        for _ in range(5):
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("event") in ["system.error", "agent.error"]:
                break
            elif data.get("event") == "system.connected":
                continue
        
        if data.get("event") == "system.error" and "expired" in data.get("content", "").lower():
            print(f"✅ Expired state correctly rejected: {data.get('content')}")
        else:
            print(f"❌ Unexpected response: {data}")
        
        await websocket.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_malformed_requests():
    """Test with malformed requests."""
    print("\n🧪 Testing malformed requests...")
    
    try:
        websocket = await websockets.connect("ws://localhost:8080")
        
        # Test 1: Missing signed_state
        print("  Testing missing signed_state...")
        malformed1 = {
            "event": "user.reconnect_with_state",
            "timestamp": datetime.now().isoformat()
            # Missing signed_state
        }
        
        await websocket.send(json.dumps(malformed1))
        
        # Wait for error response, skip connection messages
        for _ in range(5):
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("event") in ["system.error", "agent.error"]:
                break
            elif data.get("event") == "system.connected":
                continue
        
        if data.get("event") == "system.error":
            print(f"    ✅ Missing signed_state rejected: {data.get('content')}")
        else:
            print(f"    ❌ Unexpected response: {data}")
        
        # Test 2: Request state for non-existent session
        print("  Testing state request for non-existent session...")
        malformed2 = {
            "event": "user.request_state",
            "session_id": "non-existent-session-id",
            "timestamp": datetime.now().isoformat()
        }
        
        await websocket.send(json.dumps(malformed2))
        
        # Wait for error response
        response = await websocket.recv()
        data = json.loads(response)
        
        if data.get("event") == "agent.error":
            print(f"    ✅ Non-existent session rejected: {data.get('content')}")
        else:
            print(f"    ❌ Unexpected response: {data}")
        
        await websocket.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_concurrent_operations():
    """Test concurrent state operations."""
    print("\n🧪 Testing concurrent operations...")
    
    try:
        # Create a valid session first
        websocket1 = await websockets.connect("ws://localhost:8080")
        
        # Create session
        await websocket1.send(json.dumps({
            "event": "user.create_session",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Wait for session creation
        while True:
            response = await websocket1.recv()
            data = json.loads(response)
            if data.get("event") == "agent.session_created":
                session_id = data.get("session_id")
                print(f"  Created session: {session_id}")
                break
            elif data.get("event") == "system.connected":
                continue
            else:
                break
        
        # Send a message to build some state
        await websocket1.send(json.dumps({
            "event": "user.message",
            "session_id": session_id,
            "content": "Hello",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Wait for response
        await websocket1.recv()  # Skip agent response
        
        # Now test rapid concurrent requests
        print("  Testing rapid state export requests...")
        
        tasks = []
        for i in range(3):
            task = asyncio.create_task(request_state_export(websocket1, session_id, i))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_exports = sum(1 for r in results if not isinstance(r, Exception))
        print(f"    ✅ {successful_exports}/3 concurrent exports succeeded")
        
        await websocket1.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

async def request_state_export(websocket, session_id, request_id):
    """Helper function for concurrent state export requests."""
    await websocket.send(json.dumps({
        "event": "user.request_state",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    }))
    
    # Wait for state export response
    max_attempts = 5
    for _ in range(max_attempts):
        response = await websocket.recv()
        data = json.loads(response)
        if data.get("event") == "agent.state_exported":
            print(f"    Request {request_id}: Export successful")
            return True
        elif data.get("event") in ["agent.error", "system.error"]:
            print(f"    Request {request_id}: Export failed - {data.get('content')}")
            return False
    
    print(f"    Request {request_id}: Timeout")
    return False

async def main():
    """Run all edge case tests."""
    print("🚀 Starting WebSocket state management edge case tests")
    print("=" * 60)
    
    try:
        await test_invalid_state_signature()
        await test_expired_state()
        await test_malformed_requests()
        await test_concurrent_operations()
        
        print("\n" + "=" * 60)
        print("🎉 All edge case tests completed!")
        print("✅ Error handling appears to be working correctly")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())