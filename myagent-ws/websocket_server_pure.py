#!/usr/bin/env python3
"""
Pure WebSocket Message Transport Server

This server provides a pure message transport layer for real-time communication
between agents and frontend clients. It does not contain any business logic
or agent execution code, focusing solely on message routing and broadcasting.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Import WebSocket protocol
from websocket_trace_protocol import (
    TraceEventType, WebSocketMessage,
    create_connection_message
)


class WebSocketConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_metadata[session_id] = {
            "connected_at": asyncio.get_event_loop().time(),
            "message_count": 0
        }
        print(f"✅ WebSocket connection established: {session_id}")
        
        # Send connection established message
        connection_message = create_connection_message(session_id)
        await self.send_message(session_id, connection_message)
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]
        print(f"❌ WebSocket connection closed: {session_id}")
    
    async def send_message(self, session_id: str, message: WebSocketMessage):
        """Send message to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(message.model_dump_json())
                # Update message count
                if session_id in self.session_metadata:
                    self.session_metadata[session_id]["message_count"] += 1
            except Exception as e:
                print(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast_message(self, message: WebSocketMessage):
        """Broadcast message to all connected sessions"""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message.model_dump_json())
                # Update message count
                if session_id in self.session_metadata:
                    self.session_metadata[session_id]["message_count"] += 1
            except Exception as e:
                print(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)
    
    async def send_raw_message(self, session_id: str, message_dict: dict):
        """Send raw message dict to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message_dict))
                # Update message count
                if session_id in self.session_metadata:
                    self.session_metadata[session_id]["message_count"] += 1
            except Exception as e:
                print(f"Error sending raw message to {session_id}: {e}")
                self.disconnect(session_id)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about current connections"""
        return {
            "total_connections": len(self.active_connections),
            "active_sessions": list(self.active_connections.keys()),
            "session_metadata": self.session_metadata
        }


# Create FastAPI app
app = FastAPI(title="Pure WebSocket Message Transport Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for the web interface)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass  # Static directory may not exist

# Global connection manager
connection_manager = WebSocketConnectionManager()


@app.get("/")
async def get_index():
    """Serve the main web interface"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MyAgent Real-time Message Transport</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .controls { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .trace-section { background: white; border-radius: 8px; margin-bottom: 20px; }
            .trace-header { 
                background: #f8f9fa; 
                padding: 15px 20px; 
                border-radius: 8px 8px 0 0; 
                cursor: pointer; 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                border-bottom: 1px solid #dee2e6;
            }
            .trace-header:hover { background: #e9ecef; }
            .trace-content { padding: 20px; max-height: 400px; overflow-y: auto; }
            .trace-content.collapsed { display: none; }
            .collapse-icon { transition: transform 0.3s ease; }
            .collapsed .collapse-icon { transform: rotate(-90deg); }
            .trace-event { margin: 10px 0; padding: 10px; border-left: 4px solid #007bff; background: #f8f9fa; border-radius: 4px; }
            .trace-event.error { border-left-color: #dc3545; }
            .trace-event.success { border-left-color: #28a745; }
            .trace-event.warning { border-left-color: #ffc107; }
            .event-time { font-size: 0.8em; color: #666; }
            .event-content { margin-top: 5px; }
            .final-output { background: white; padding: 20px; border-radius: 8px; }
            .final-output h3 { margin-top: 0; color: #28a745; }
            .output-content { 
                background: #f8f9fa; 
                padding: 15px; 
                border-radius: 4px; 
                font-family: monospace; 
                white-space: pre-wrap; 
                border-left: 4px solid #28a745;
                min-height: 50px;
                line-height: 1.5;
            }
            .output-placeholder { color: #6c757d; font-style: italic; }
            .typewriter-cursor { 
                display: inline-block; 
                background-color: #007bff; 
                width: 2px; 
                height: 1.2em; 
                margin-left: 2px;
                animation: blink 1s infinite;
            }
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
            }
            .typewriter-output {
                color: #212529;
            }
            button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            input[type="text"] { padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 300px; }
            .status { margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 4px; }
            .agent-controls { background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #ffc107; }
            .info-box { background: #d1ecf1; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #17a2b8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔌 MyAgent Message Transport Server</h1>
                <p>Pure WebSocket message transport layer for agent communication</p>
            </div>
            
            <div class="info-box">
                <h4>📋 Server Information</h4>
                <p><strong>Purpose:</strong> This server provides pure message transport between agents and frontend clients.</p>
                <p><strong>Agent Runner:</strong> Use <code>agent_runner.py</code> to execute agents independently.</p>
                <p><strong>Session ID:</strong> <span id="sessionIdDisplay"></span></p>
            </div>
            
            <div class="agent-controls">
                <h4>🤖 Agent Control</h4>
                <p><strong>Note:</strong> This server no longer executes agents directly. Use the standalone agent runner:</p>
                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    python agent_runner.py --question "your question here" --session-id <span id="sessionIdForCommand"></span>
                </div>
                <div style="margin-top: 15px;">
                    <input type="text" id="questionInput" placeholder="Enter your question..." value="显示用户表的10条用户数据">
                    <button onclick="showAgentCommand()">📋 Show Command</button>
                    <button onclick="clearTrace()" style="margin-left: 10px; background: #6c757d;">🗑️ Clear</button>
                </div>
                <div id="commandDisplay" style="display: none; margin-top: 15px; background: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace;"></div>
            </div>
            
            <div class="controls">
                <div class="status" id="connectionStatus">
                    Status: <span id="statusText">Connecting...</span>
                </div>
            </div>
            
            <div class="trace-section">
                <div class="trace-header" onclick="toggleTraceSection()">
                    <div>
                        <strong>📋 Message Trace</strong>
                        <span id="traceCount" style="color: #6c757d; margin-left: 10px;">(0 messages)</span>
                    </div>
                    <span class="collapse-icon">▼</span>
                </div>
                <div class="trace-content" id="traceContent">
                    <p style="color: #666; text-align: center;">Connecting to WebSocket server...</p>
                </div>
            </div>
            
            <div class="final-output">
                <h3>🎯 Agent Output</h3>
                <div class="output-content" id="finalOutput">
                    <span class="output-placeholder">Agent responses will appear here when using the standalone runner...</span>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let sessionId = 'session_' + Math.random().toString(36).substring(7);
            let eventCount = 0;
            let fullResponseText = '';
            let isRealTimeStreaming = false;
            let streamingContainer = null;
            let currentStreamId = null;

            // Update session ID displays
            document.getElementById('sessionIdDisplay').textContent = sessionId;
            document.getElementById('sessionIdForCommand').textContent = sessionId;

            function showAgentCommand() {
                const question = document.getElementById('questionInput').value;
                const command = `python agent_runner.py --question "${question}" --session-id ${sessionId}`;
                const displayDiv = document.getElementById('commandDisplay');
                displayDiv.textContent = command;
                displayDiv.style.display = 'block';
                
                // Copy to clipboard
                navigator.clipboard.writeText(command).then(() => {
                    displayDiv.style.background = '#d4edda';
                    displayDiv.innerHTML = command + ' <span style="color: #28a745; font-weight: bold;">(📋 Copied to clipboard!)</span>';
                    setTimeout(() => {
                        displayDiv.style.background = '#f8f9fa';
                        displayDiv.textContent = command;
                    }, 2000);
                }).catch(() => {
                    displayDiv.style.display = 'block';
                });
            }

            function startRealTimeStreaming(data) {
                console.log('Starting real-time streaming:', data);
                isRealTimeStreaming = true;
                currentStreamId = data.stream_id;
                
                const finalOutput = document.getElementById('finalOutput');
                finalOutput.innerHTML = '';
                finalOutput.className = 'output-content';
                
                // Create streaming container
                streamingContainer = document.createElement('div');
                streamingContainer.className = 'typewriter-output';
                finalOutput.appendChild(streamingContainer);
                
                // Add blinking cursor
                const cursor = document.createElement('span');
                cursor.className = 'typewriter-cursor';
                finalOutput.appendChild(cursor);
                
                // Show indicator
                addTraceEvent('info', '⌨️ AI is Streaming...', `Real-time response from ${data.model}`);
            }

            function handleStreamingChunk(data) {
                if (!isRealTimeStreaming || data.stream_id !== currentStreamId || !streamingContainer) {
                    return;
                }
                
                console.log('Received streaming chunk:', data.chunk);
                
                // Handle newlines and create appropriate elements
                const chunk = data.chunk || '';
                const parts = chunk.split('\\n');
                
                for (let i = 0; i < parts.length; i++) {
                    if (i > 0) {
                        // Add line break for newlines
                        streamingContainer.appendChild(document.createElement('br'));
                    }
                    if (parts[i]) {
                        // Add text content
                        const textNode = document.createTextNode(parts[i]);
                        streamingContainer.appendChild(textNode);
                    }
                }
                
                // Auto-scroll to show latest content
                const finalOutput = document.getElementById('finalOutput');
                finalOutput.scrollTop = finalOutput.scrollHeight;
            }

            function finishRealTimeStreaming(data) {
                console.log('Finishing real-time streaming:', data);
                isRealTimeStreaming = false;
                currentStreamId = null;
                
                // Remove cursor after a short delay
                const finalOutput = document.getElementById('finalOutput');
                const cursor = finalOutput.querySelector('.typewriter-cursor');
                if (cursor) {
                    setTimeout(() => {
                        cursor.remove();
                    }, 1000);
                }
                
                // Store final response
                fullResponseText = data.full_response || '';
                
                // Update UI to show completion
                if (data.success) {
                    addTraceEvent('success', '✅ Streaming Complete', 
                        `Final response received (${data.response_length || 0} characters)`);
                } else {
                    addTraceEvent('error', '❌ Streaming Error', 
                        `Error: ${data.error || 'Unknown error'}`);
                }
            }

            function resetStreamingState() {
                console.log('Resetting streaming state');
                isRealTimeStreaming = false;
                streamingContainer = null;
                currentStreamId = null;
                fullResponseText = '';
            }

            function connect() {
                const wsUrl = `ws://localhost:8234/ws/${sessionId}`;
                console.log('Attempting WebSocket connection to:', wsUrl);
                
                // Update status to show connecting
                document.getElementById('statusText').textContent = 'Connecting...';
                document.getElementById('connectionStatus').style.background = '#fff3cd';
                document.getElementById('connectionStatus').style.color = '#856404';
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    console.log('WebSocket connection opened');
                    
                    document.getElementById('statusText').textContent = 'Connected - Ready for Agent Messages';
                    document.getElementById('connectionStatus').style.background = '#d4edda';
                    document.getElementById('connectionStatus').style.color = '#155724';
                    
                    // Clear the "Connecting..." message and show connected status
                    const traceContent = document.getElementById('traceContent');
                    if (traceContent.innerHTML.includes('Connecting to WebSocket server')) {
                        traceContent.innerHTML = '';
                        eventCount = 0;
                        updateEventCount();
                    }
                    
                    addTraceEvent('success', '🔗 WebSocket Connected', 'Connected to message transport server - ready for agent communication');
                };
                
                ws.onmessage = function(event) {
                    try {
                        const message = JSON.parse(event.data);
                        console.log('Received WebSocket message:', message);
                        handleTraceMessage(message);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error, event.data);
                        addTraceEvent('error', '❌ Message Parse Error', 'Failed to parse incoming message');
                    }
                };
                
                ws.onclose = function(event) {
                    console.log('WebSocket connection closed', event);
                    document.getElementById('statusText').textContent = 'Disconnected';
                    document.getElementById('connectionStatus').style.background = '#f8d7da';
                    document.getElementById('connectionStatus').style.color = '#721c24';
                    
                    if (event.wasClean) {
                        addTraceEvent('info', '🔌 WebSocket Disconnected', 'Connection closed cleanly');
                    } else {
                        addTraceEvent('error', '❌ WebSocket Disconnected', 'Connection to server lost - attempting to reconnect...');
                        // Only reconnect if it wasn't a clean disconnect
                        setTimeout(() => {
                            document.getElementById('statusText').textContent = 'Reconnecting...';
                            document.getElementById('connectionStatus').style.background = '#fff3cd';
                            document.getElementById('connectionStatus').style.color = '#856404';
                            connect();
                        }, 3000);
                    }
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    document.getElementById('statusText').textContent = 'Connection Error';
                    document.getElementById('connectionStatus').style.background = '#f8d7da';
                    document.getElementById('connectionStatus').style.color = '#721c24';
                    addTraceEvent('error', '⚠️ WebSocket Error', 'Connection error occurred - check server status');
                };
            }

            function toggleTraceSection() {
                const traceContent = document.getElementById('traceContent');
                const traceHeader = document.querySelector('.trace-header');
                
                if (traceContent.classList.contains('collapsed')) {
                    traceContent.classList.remove('collapsed');
                    traceHeader.classList.remove('collapsed');
                } else {
                    traceContent.classList.add('collapsed');
                    traceHeader.classList.add('collapsed');
                }
            }

            function updateEventCount() {
                document.getElementById('traceCount').textContent = `(${eventCount} messages)`;
            }

            function handleTraceMessage(message) {
                const { event_type, timestamp, data } = message;
                
                switch(event_type) {
                    case 'connection_established':
                        console.log('Received connection_established event');
                        addTraceEvent('success', '🔗 Connection Established', 'WebSocket connection ready for agent communication');
                        break;
                    
                    case 'trace_started':
                        // Clear previous results and reset streaming state
                        clearFinalOutput();
                        resetStreamingState();
                        addTraceEvent('info', '🚀 Agent Started', 
                            `Agent: ${data.agent_name}<br>Request: ${data.request}<br>Max Steps: ${data.max_steps}`);
                        break;
                    
                    case 'trace_completed':
                        addTraceEvent('success', '✅ Agent Completed', 
                            `Status: ${data.status}<br>Response: ${(data.final_response || '').substring(0, 200)}...`);
                        
                        // Only show response if real-time streaming didn't happen
                        if (!isRealTimeStreaming && !streamingContainer) {
                            showFinalOutput(data.final_response || 'Agent completed but no response available');
                        } else {
                            // Store final response
                            fullResponseText = data.final_response || fullResponseText;
                        }
                        break;
                    
                    case 'stream_started':
                        // Clear previous final output and prepare for real-time streaming
                        clearFinalOutput();
                        startRealTimeStreaming(data);
                        addTraceEvent('info', '🚀 Real-time Streaming Started', 
                            `Model: ${data.model}<br>Method: ${data.method}<br>Stream ID: ${data.stream_id}`);
                        break;
                    
                    case 'stream_chunk':
                        // Handle real-time chunk streaming
                        handleStreamingChunk(data);
                        break;
                    
                    case 'stream_completed':
                        // Finalize streaming display
                        finishRealTimeStreaming(data);
                        addTraceEvent('success', '✅ Real-time Streaming Completed', 
                            `Duration: ${data.duration_ms?.toFixed(2)}ms<br>Response length: ${data.response_length} chars<br>Success: ${data.success ? 'Yes' : 'No'}`);
                        break;
                    
                    case 'status_update':
                        addTraceEvent('info', '📊 Status Update', 
                            `Step: ${data.current_step}/${data.max_steps}<br>State: ${data.agent_state}<br>Message: ${data.message?.substring(0, 200)}${data.message?.length > 200 ? '...' : ''}`);
                        break;
                    
                    case 'think_completed':
                        const thinkInputs = data.inputs || {};
                        const thinkOutputs = data.outputs || {};
                        const userMsg = thinkInputs.content || thinkInputs.last_user_message?.content || 'N/A';
                        const assistantMsg = thinkOutputs.content || thinkOutputs.last_assistant_message?.content || 'N/A';
                        addTraceEvent('info', '🤔 Thinking Completed', 
                            `Duration: ${data.duration_ms?.toFixed(2)}ms<br>Input: ${userMsg.substring(0, 100)}...<br>Response: ${assistantMsg.substring(0, 100)}...`);
                        break;
                    
                    case 'tool_completed':
                        const toolInputs = Object.keys(data.inputs || {}).join(', ') || 'None';
                        const toolOutput = data.outputs?.result || data.outputs?.output || 'No output';
                        addTraceEvent('success', `🔧 Tool: ${data.name}`, 
                            `Duration: ${data.duration_ms?.toFixed(2)}ms<br>Inputs: ${toolInputs}<br>Result: ${toolOutput.substring(0, 200)}...`);
                        break;
                    
                    default:
                        console.log('Unhandled message:', event_type, data);
                        addTraceEvent('info', `📨 ${event_type}`, JSON.stringify(data, null, 2).substring(0, 300));
                }
            }

            function addTraceEvent(type, title, content) {
                const traceContent = document.getElementById('traceContent');
                const eventDiv = document.createElement('div');
                eventDiv.className = `trace-event ${type}`;
                
                const timestamp = new Date().toLocaleTimeString();
                eventDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>${title}</strong>
                        <span class="event-time">${timestamp}</span>
                    </div>
                    <div class="event-content">${content}</div>
                `;
                
                traceContent.appendChild(eventDiv);
                traceContent.scrollTop = traceContent.scrollHeight;
                
                // Update event count
                eventCount++;
                updateEventCount();
            }

            function showFinalOutput(response) {
                const finalOutput = document.getElementById('finalOutput');
                finalOutput.innerHTML = response || 'No response received';
                finalOutput.className = 'output-content';
            }

            function clearFinalOutput() {
                resetStreamingState();
                
                const finalOutput = document.getElementById('finalOutput');
                finalOutput.innerHTML = '<span class="output-placeholder">Agent responses will appear here when using the standalone runner...</span>';
                finalOutput.className = 'output-content';
            }

            function clearTrace() {
                const traceContent = document.getElementById('traceContent');
                traceContent.innerHTML = '';
                eventCount = 0;
                updateEventCount();
                clearFinalOutput();
            }

            // Connect when page loads
            connect();
        </script>
    </body>
    </html>
    """)


@app.get("/api/connections")
async def get_connections():
    """Get current connection information"""
    return connection_manager.get_connection_info()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for pure message transport"""
    await connection_manager.connect(websocket, session_id)
    
    try:
        while True:
            # Listen for incoming messages and route them appropriately
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                message_type = data.get("type", "unknown")
                
                print(f"📨 Received message from {session_id}: {message_type}")
                
                # Route messages based on type
                if message_type == "agent_command":
                    # This could trigger external agent execution
                    print(f"🤖 Agent command received: {data.get('command', 'unknown')}")
                    
                elif message_type == "broadcast":
                    # Broadcast message to all connections
                    broadcast_data = data.get("data", {})
                    await connection_manager.send_raw_message(session_id, broadcast_data)
                    
                elif message_type == "ping":
                    # Respond to ping
                    await connection_manager.send_raw_message(session_id, {
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    })
                
                else:
                    print(f"📨 Unknown message type: {message_type}")
                    
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON from {session_id}: {message}")
            
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
        print(f"🔌 Client {session_id} disconnected")
    except Exception as e:
        print(f"❌ WebSocket error for {session_id}: {e}")
        connection_manager.disconnect(session_id)


if __name__ == "__main__":
    print("🚀 Starting Pure WebSocket Message Transport Server...")
    print("📍 Server will be available at: http://localhost:8234")
    print("🔌 WebSocket endpoint: ws://localhost:8234/ws/{session_id}")
    print("🤖 Use agent_runner.py to execute agents independently")
    print("📋 API endpoint: http://localhost:8234/api/connections")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8234,
        reload=False,
        access_log=True
    )