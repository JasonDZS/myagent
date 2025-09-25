#!/usr/bin/env python3
"""
Message Bridge for Loose Coupling Communication

This module provides a bridge between agents and the WebSocket server,
enabling loose coupling through async message queues and event-driven communication.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

# Add parent directory to path for myagent imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import websockets
from websocket_trace_protocol import (
    TraceEventType, WebSocketMessage,
    create_connection_message, create_trace_started_message, create_trace_completed_message
)


@dataclass
class MessageEvent:
    """Represents a message event in the system"""
    event_id: str
    event_type: str
    session_id: str
    timestamp: float
    data: Dict[str, Any]
    source: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageEvent':
        return cls(**data)


class MessageQueue:
    """Async message queue for decoupled communication"""
    
    def __init__(self, max_size: int = 1000):
        self.queue = asyncio.Queue(maxsize=max_size)
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_history: List[MessageEvent] = []
        self.max_history = 100
    
    async def publish(self, event: MessageEvent):
        """Publish event to queue and notify subscribers"""
        await self.queue.put(event)
        
        # Store in history
        self.message_history.append(event)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # Notify type-specific subscribers
        event_type = event.event_type
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"❌ Subscriber callback error: {e}")
    
    async def consume(self) -> MessageEvent:
        """Consume next event from queue"""
        return await self.queue.get()
    
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to specific event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        print(f"📡 Subscribed to event type: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from event type"""
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
                print(f"📡 Unsubscribed from event type: {event_type}")
            except ValueError:
                pass
    
    def get_history(self, event_type: Optional[str] = None) -> List[MessageEvent]:
        """Get message history, optionally filtered by event type"""
        if event_type:
            return [e for e in self.message_history if e.event_type == event_type]
        return self.message_history.copy()


class WebSocketBridge:
    """Bridge between message queue and WebSocket server"""
    
    def __init__(self, websocket_url: str, session_id: str, message_queue: MessageQueue):
        self.websocket_url = websocket_url
        self.session_id = session_id
        self.message_queue = message_queue
        self.websocket = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            self.connected = True
            self.reconnect_attempts = 0
            print(f"🔌 Bridge connected to WebSocket: {self.websocket_url}")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
        except Exception as e:
            print(f"❌ Bridge connection failed: {e}")
            await self._handle_reconnection()
    
    async def _handle_reconnection(self):
        """Handle reconnection logic"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            wait_time = min(2 ** self.reconnect_attempts, 30)  # Exponential backoff, max 30s
            print(f"🔄 Retrying connection in {wait_time}s (attempt {self.reconnect_attempts})")
            await asyncio.sleep(wait_time)
            await self.connect()
        else:
            print(f"❌ Max reconnection attempts reached, giving up")
            self.connected = False
    
    async def _listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Create message event
                    event = MessageEvent(
                        event_id=str(uuid.uuid4()),
                        event_type=data.get("event_type", "websocket_message"),
                        session_id=self.session_id,
                        timestamp=asyncio.get_event_loop().time(),
                        data=data,
                        source="websocket_server"
                    )
                    
                    # Publish to message queue
                    await self.message_queue.publish(event)
                    
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON from WebSocket: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
            self.connected = False
            await self._handle_reconnection()
        except Exception as e:
            print(f"❌ WebSocket listening error: {e}")
            self.connected = False
    
    async def send_message(self, event: MessageEvent):
        """Send message to WebSocket server"""
        if not self.connected or not self.websocket:
            print("❌ Cannot send message: WebSocket not connected")
            return
        
        try:
            message_data = {
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "session_id": event.session_id,
                "data": event.data
            }
            
            await self.websocket.send(json.dumps(message_data))
            print(f"📤 Sent message via WebSocket: {event.event_type}")
            
        except Exception as e:
            print(f"❌ Failed to send WebSocket message: {e}")
            self.connected = False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("🔌 Bridge disconnected from WebSocket")


class MessageBridge:
    """Main message bridge orchestrating communication between components"""
    
    def __init__(self, websocket_url: str = "ws://localhost:8234/ws", session_id: Optional[str] = None):
        self.session_id = session_id or f"bridge_{int(asyncio.get_event_loop().time())}"
        self.message_queue = MessageQueue()
        self.websocket_bridge = WebSocketBridge(
            f"{websocket_url}/{self.session_id}", 
            self.session_id, 
            self.message_queue
        )
        self.running = False
        self.message_handlers: Dict[str, Callable] = {}
    
    async def start(self):
        """Start the message bridge"""
        print(f"🌉 Starting Message Bridge for session: {self.session_id}")
        
        # Connect to WebSocket
        await self.websocket_bridge.connect()
        
        # Start message processing
        self.running = True
        asyncio.create_task(self._process_messages())
        
        print("✅ Message Bridge started successfully")
    
    async def stop(self):
        """Stop the message bridge"""
        print("🛑 Stopping Message Bridge...")
        self.running = False
        await self.websocket_bridge.disconnect()
        print("✅ Message Bridge stopped")
    
    async def _process_messages(self):
        """Process messages from the queue"""
        while self.running:
            try:
                event = await asyncio.wait_for(self.message_queue.consume(), timeout=1.0)
                
                # Handle message based on type
                if event.event_type in self.message_handlers:
                    handler = self.message_handlers[event.event_type]
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            handler(event)
                    except Exception as e:
                        print(f"❌ Message handler error for {event.event_type}: {e}")
                
                # Forward to WebSocket if from agent
                if event.source == "agent" and self.websocket_bridge.connected:
                    await self.websocket_bridge.send_message(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"❌ Message processing error: {e}")
                await asyncio.sleep(1)
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a message handler for specific event type"""
        self.message_handlers[event_type] = handler
        print(f"📋 Registered handler for event type: {event_type}")
    
    async def send_agent_message(self, event_type: str, data: Dict[str, Any]):
        """Send message from agent to the system"""
        event = MessageEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            session_id=self.session_id,
            timestamp=asyncio.get_event_loop().time(),
            data=data,
            source="agent"
        )
        
        await self.message_queue.publish(event)
        print(f"📨 Agent message sent: {event_type}")
    
    def subscribe_to_events(self, event_type: str, callback: Callable):
        """Subscribe to specific event type"""
        self.message_queue.subscribe(event_type, callback)
    
    def get_message_history(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get message history as dictionaries"""
        history = self.message_queue.get_history(event_type)
        return [event.to_dict() for event in history]


# Example usage and testing
async def example_usage():
    """Example of how to use the message bridge"""
    
    # Create message bridge
    bridge = MessageBridge()
    
    # Register some handlers
    def handle_trace_started(event: MessageEvent):
        print(f"🚀 Trace started: {event.data.get('agent_name', 'Unknown')}")
    
    def handle_trace_completed(event: MessageEvent):
        print(f"✅ Trace completed: {event.data.get('status', 'Unknown')}")
    
    bridge.register_handler("trace_started", handle_trace_started)
    bridge.register_handler("trace_completed", handle_trace_completed)
    
    # Start bridge
    await bridge.start()
    
    # Send some test messages
    await bridge.send_agent_message("trace_started", {
        "agent_name": "test-agent",
        "request": "test request",
        "max_steps": 5
    })
    
    await bridge.send_agent_message("trace_completed", {
        "status": "completed",
        "final_response": "Test completed successfully"
    })
    
    # Let it run for a bit
    await asyncio.sleep(5)
    
    # Print message history
    history = bridge.get_message_history()
    print(f"\n📜 Message History ({len(history)} messages):")
    for i, msg in enumerate(history, 1):
        print(f"{i}. {msg['event_type']} at {msg['timestamp']}")
    
    # Stop bridge
    await bridge.stop()


if __name__ == "__main__":
    print("🧪 Testing Message Bridge")
    print("🔌 Make sure WebSocket server is running at localhost:8234")
    print("=" * 50)
    
    # Run example
    asyncio.run(example_usage())