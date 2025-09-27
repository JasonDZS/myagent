#!/usr/bin/env python3
"""
Demo client showing client-side state management for MyAgent WebSocket sessions.

This example demonstrates:
1. Creating a WebSocket session
2. Exporting session state to client
3. Simulating disconnection
4. Reconnecting with saved state
5. Continuing the conversation from where it left off

Usage:
    python examples/client_state_demo.py
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import websockets
from websockets.client import WebSocketClientProtocol

from myagent.logger import logger


class ClientStateManager:
    """Client-side state management for WebSocket sessions."""
    
    def __init__(self):
        self.stored_states: Dict[str, Dict[str, Any]] = {}
    
    def save_state(self, session_id: str, signed_state: Dict[str, Any]) -> None:
        """Save state to local storage (in-memory for demo)."""
        self.stored_states[session_id] = {
            "signed_state": signed_state,
            "saved_at": datetime.now().isoformat(),
        }
        logger.info(f"Saved state for session {session_id}")
    
    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load state from local storage."""
        if session_id in self.stored_states:
            logger.info(f"Loaded state for session {session_id}")
            return self.stored_states[session_id]["signed_state"]
        return None
    
    def list_saved_sessions(self) -> Dict[str, str]:
        """List all saved sessions."""
        return {
            session_id: data["saved_at"] 
            for session_id, data in self.stored_states.items()
        }


class MyAgentClient:
    """WebSocket client for MyAgent with state management."""
    
    def __init__(self, server_url: str = "ws://localhost:8080"):
        self.server_url = server_url
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.state_manager = ClientStateManager()
        self.running = False
        # Event handling
        self.pending_operations = {}  # Store futures for pending operations
    
    async def connect(self) -> bool:
        """Connect to WebSocket server."""
        try:
            self.websocket = await websockets.connect(self.server_url)
            logger.info(f"Connected to {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from server")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send message to server."""
        if not self.websocket:
            raise RuntimeError("Not connected to server")
        
        message_json = json.dumps(message)
        await self.websocket.send(message_json)
        logger.debug(f"Sent: {message}")
    
    async def receive_message(self) -> Dict[str, Any]:
        """Receive message from server."""
        if not self.websocket:
            raise RuntimeError("Not connected to server")
        
        message_json = await self.websocket.recv()
        message = json.loads(message_json)
        logger.debug(f"Received: {message}")
        return message
    
    async def create_session(self) -> bool:
        """Create a new session."""
        try:
            # Create a future for this operation
            operation_id = "create_session"
            future = asyncio.Future()
            self.pending_operations[operation_id] = future
            
            await self.send_message({
                "event": "user.create_session",
                "timestamp": datetime.now().isoformat(),
            })
            
            # Wait for the operation to complete
            result = await asyncio.wait_for(future, timeout=10.0)
            return result
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for session creation")
            return False
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
        finally:
            self.pending_operations.pop(operation_id, None)
    
    async def reconnect_with_state(self, signed_state: Dict[str, Any]) -> bool:
        """Reconnect using saved state."""
        try:
            # Create a future for this operation
            operation_id = "reconnect_with_state"
            future = asyncio.Future()
            self.pending_operations[operation_id] = future
            
            await self.send_message({
                "event": "user.reconnect_with_state",
                "signed_state": signed_state,
                "timestamp": datetime.now().isoformat(),
            })
            
            # Wait for the operation to complete
            result = await asyncio.wait_for(future, timeout=10.0)
            return result
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for state restoration")
            return False
        except Exception as e:
            logger.error(f"Error reconnecting with state: {e}")
            return False
        finally:
            self.pending_operations.pop(operation_id, None)
    
    async def request_state_export(self) -> Optional[Dict[str, Any]]:
        """Request current session state export."""
        if not self.session_id:
            logger.error("No active session")
            return None
        
        try:
            # Create a future for this operation
            operation_id = "request_state_export"
            future = asyncio.Future()
            self.pending_operations[operation_id] = future
            
            await self.send_message({
                "event": "user.request_state",
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
            })
            
            # Wait for the operation to complete
            result = await asyncio.wait_for(future, timeout=10.0)
            return result
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for state export")
            return None
        except Exception as e:
            logger.error(f"Error requesting state export: {e}")
            return None
        finally:
            self.pending_operations.pop(operation_id, None)
    
    async def send_user_message(self, content: str):
        """Send user message to agent."""
        if not self.session_id:
            logger.error("No active session")
            return
        
        await self.send_message({
            "event": "user.message",
            "session_id": self.session_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
    
    async def listen_for_events(self):
        """Listen for events from server."""
        self.running = True
        try:
            while self.running and self.websocket:
                try:
                    # Directly receive from websocket to avoid conflicts
                    message_json = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    message = json.loads(message_json)
                    logger.debug(f"Received: {message}")
                    await self.handle_event(message)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.info("Connection closed by server")
                    break
        except Exception as e:
            logger.error(f"Error in event listener: {e}")
        finally:
            self.running = False
    
    async def handle_event(self, event: Dict[str, Any]):
        """Handle incoming events."""
        event_type = event.get("event")
        content = event.get("content", "")
        
        # Handle pending operations first
        if event_type == "agent.session_created":
            self.session_id = event.get("session_id")
            logger.info(f"Created session: {self.session_id}")
            print(f"🚀 会话创建成功: {self.session_id}")
            
            # Complete the create_session operation
            future = self.pending_operations.get("create_session")
            if future and not future.done():
                future.set_result(True)
        
        elif event_type == "agent.state_exported":
            metadata = event.get("metadata", {})
            signed_state = metadata.get("signed_state")
            if signed_state:
                print(f"💾 状态导出成功 (大小: {metadata.get('state_size', 'unknown')} 字节)")
                
                # Complete the request_state_export operation
                future = self.pending_operations.get("request_state_export")
                if future and not future.done():
                    future.set_result(signed_state)
        
        elif event_type == "agent.state_restored":
            self.session_id = event.get("session_id")
            metadata = event.get("metadata", {})
            logger.info(f"Restored session: {self.session_id}")
            print(f"🔄 会话恢复成功: {self.session_id}")
            print(f"   恢复步骤: {metadata.get('restored_step', 'unknown')}")
            print(f"   消息数量: {metadata.get('message_count', 'unknown')}")
            
            # Complete the reconnect_with_state operation
            future = self.pending_operations.get("reconnect_with_state")
            if future and not future.done():
                future.set_result(True)
        
        # Handle regular events
        elif event_type == "agent.thinking":
            print(f"🤔 Agent thinking: {content}")
        elif event_type == "agent.tool_call":
            metadata = event.get("metadata", {})
            tool_name = metadata.get("tool", "unknown")
            print(f"🔧 Tool call: {tool_name}")
        elif event_type == "agent.tool_result":
            print(f"✅ Tool result: {content}")
        elif event_type == "agent.final_answer":
            print(f"💡 Final answer: {content}")
        elif event_type == "agent.error" or event_type == "system.error":
            print(f"❌ Error: {content}")
            
            # Complete any pending operations with error
            for operation_id, future in list(self.pending_operations.items()):
                if not future.done():
                    future.set_result(False)
                    
        elif event_type == "system.connected":
            print(f"🔗 Connected: {content}")
        else:
            logger.debug(f"Unhandled event: {event_type}")
    
    def stop_listening(self):
        """Stop listening for events."""
        self.running = False


async def demo_state_management():
    """Demonstrate client-side state management."""
    client = MyAgentClient()
    
    print("🚀 Starting client-side state management demo")
    print("=" * 50)
    
    # Step 1: Connect and create session
    print("\n📡 Step 1: Connecting to server...")
    if not await client.connect():
        print("❌ Failed to connect to server")
        return
    
    # Start event listener
    listen_task = asyncio.create_task(client.listen_for_events())
    
    print("\n🆕 Step 2: Creating new session...")
    if not await client.create_session():
        print("❌ Failed to create session")
        return
    
    await asyncio.sleep(1)  # Wait for session creation
    
    # Step 2: Send some messages
    print("\n💬 Step 3: Sending messages to build conversation history...")
    await client.send_user_message("Hello, what's the weather like?")
    await asyncio.sleep(2)  # Wait for agent response
    
    await client.send_user_message("Can you tell me a joke?")
    await asyncio.sleep(2)  # Wait for agent response
    
    # Step 3: Export state
    print("\n💾 Step 4: Exporting session state...")
    signed_state = await client.request_state_export()
    if signed_state:
        original_session_id = client.session_id
        client.state_manager.save_state(original_session_id, signed_state)
        print(f"✅ State saved for session {original_session_id}")
    else:
        print("❌ Failed to export state")
        return
    
    # Step 4: Simulate disconnection
    print("\n🔌 Step 5: Simulating disconnection...")
    client.stop_listening()
    await client.disconnect()
    await asyncio.sleep(1)
    
    # Step 5: Reconnect with state
    print("\n🔄 Step 6: Reconnecting with saved state...")
    if not await client.connect():
        print("❌ Failed to reconnect")
        return
    
    # Restart event listener
    listen_task = asyncio.create_task(client.listen_for_events())
    
    # Load and restore state
    saved_state = client.state_manager.load_state(original_session_id)
    if saved_state and await client.reconnect_with_state(saved_state):
        print(f"✅ Successfully restored session from state")
    else:
        print("❌ Failed to restore state")
        return
    
    await asyncio.sleep(1)  # Wait for restoration
    
    # Step 6: Continue conversation
    print("\n💬 Step 7: Continuing conversation from restored state...")
    await client.send_user_message("Do you remember our previous conversation?")
    await asyncio.sleep(3)  # Wait for agent response
    
    # Step 7: Show saved sessions
    print("\n📋 Step 8: Listing saved sessions...")
    saved_sessions = client.state_manager.list_saved_sessions()
    for session_id, saved_at in saved_sessions.items():
        print(f"  Session {session_id}: saved at {saved_at}")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    client.stop_listening()
    await client.disconnect()
    
    print("\n✅ Demo completed successfully!")
    print("🎯 Key features demonstrated:")
    print("  - Session state export")
    print("  - Client-side state storage")
    print("  - State-based reconnection")
    print("  - Conversation continuity")


async def main():
    """Main function."""
    try:
        await demo_state_management()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.exception("Demo error")


if __name__ == "__main__":
    asyncio.run(main())