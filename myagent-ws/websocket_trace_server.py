"""WebSocket Trace Server for Real-time Agent Monitoring"""

import asyncio
import json
import uuid
import sys
import os
from typing import Dict, Set
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Add parent directory to path for myagent imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from myagent import create_react_agent
from myagent.trace import TraceManager, TraceMetadata, get_trace_manager, set_trace_manager, RunType, RunStatus
from myagent.tool.base_tool import BaseTool, ToolResult

from websocket_trace_protocol import (
    TraceEventType, WebSocketMessage, TraceStartedData, TraceCompletedData,
    RunEventData, StatusUpdateData, ProgressUpdateData, SummaryEventData,
    create_connection_message, create_trace_started_message, create_trace_completed_message,
    create_run_event_message, create_status_message, create_progress_message,
    create_summary_started_message, create_summary_completed_message
)

# Import MySQL tools from the original example
import os
from dataclasses import dataclass
from contextlib import closing
from typing import Any, List, Optional, Sequence

import pymysql
from pymysql.cursors import DictCursor


# MySQL configuration (same as original example)
@dataclass
class MySQLConfig:
    host: str
    user: str
    password: str
    database: str
    port: int = 3306
    charset: str = "utf8mb4"


def _load_mysql_config() -> MySQLConfig:
    """Load MySQL configuration from environment variables"""
    required_vars = ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE")
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise RuntimeError(f"Missing MySQL environment variables: {', '.join(missing)}")

    return MySQLConfig(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        charset=os.environ.get("MYSQL_CHARSET", "utf8mb4"),
    )


def _connect(config: MySQLConfig) -> pymysql.connections.Connection:
    """Create MySQL connection"""
    return pymysql.connect(
        host=config.host,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        charset=config.charset,
        autocommit=True,
        cursorclass=DictCursor,
    )


# Simple MySQL tools for demo
class MySQLSchemaTool(BaseTool):
    name: str = "mysql_schema"
    description: str = "Inspect MySQL table structure"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Optional table name. When omitted, returns list of tables.",
            }
        },
    }

    async def execute(self, table: Optional[str] = None) -> ToolResult:
        try:
            config = _load_mysql_config()
            
            def _inspect_schema() -> str:
                with closing(_connect(config)) as conn, closing(conn.cursor()) as cursor:
                    if not table:
                        cursor.execute("SHOW TABLES")
                        tables = [next(iter(row.values())) for row in cursor.fetchall()]
                        return "Available tables:\\n" + "\\n".join(f"- {name}" for name in tables)
                    
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable, column_key, column_type
                        FROM information_schema.columns
                        WHERE table_schema = %s AND table_name = %s
                        ORDER BY ordinal_position
                    """, (config.database, table))
                    
                    columns = cursor.fetchall()
                    if not columns:
                        return f"Table '{table}' not found"
                    
                    result = [f"Columns for {table}:"]
                    for col in columns:
                        nullable = "NULLABLE" if col["is_nullable"] == "YES" else "NOT NULL"
                        key = f" {col['column_key']}" if col["column_key"] else ""
                        result.append(f"- {col['column_name']} ({col['column_type']} {nullable}{key})")
                    
                    return "\\n".join(result)
            
            result = await asyncio.to_thread(_inspect_schema)
            return ToolResult(output=result, system="Schema inspection completed")
            
        except Exception as e:
            return ToolResult(error=f"Schema inspection failed: {e}")


class MySQLQueryTool(BaseTool):
    name: str = "mysql_query"
    description: str = "Execute read-only SQL queries"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "SQL query to execute"},
            "max_rows": {"type": "integer", "default": 20, "description": "Maximum rows to return"}
        },
        "required": ["sql"]
    }

    async def execute(self, sql: str, max_rows: int = 20) -> ToolResult:
        try:
            # Basic read-only validation
            sql_lower = sql.strip().lower()
            if not any(sql_lower.startswith(prefix) for prefix in ('select', 'show', 'describe', 'explain')):
                return ToolResult(error="Only read-only queries allowed")
            
            config = _load_mysql_config()
            
            def _run_query() -> str:
                with closing(_connect(config)) as conn, closing(conn.cursor()) as cursor:
                    cursor.execute(sql.strip().rstrip(';'))
                    rows = cursor.fetchmany(size=max_rows)
                    
                    if not rows:
                        return "No rows returned"
                    
                    # Simple table formatting
                    headers = list(rows[0].keys()) if rows else []
                    result = [" | ".join(headers)]
                    result.append("-" * len(result[0]))
                    
                    for row in rows:
                        result.append(" | ".join(str(v) if v is not None else "NULL" for v in row.values()))
                    
                    return "\\n".join(result) + f"\\n({len(rows)} rows)"
            
            result = await asyncio.to_thread(_run_query)
            return ToolResult(output=result, system=f"Query executed: {sql[:50]}...")
            
        except Exception as e:
            return ToolResult(error=f"Query failed: {e}")


class WebSocketConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_agents: Dict[str, Any] = {}  # session_id -> agent instance
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
        # Send connection established message
        message = create_connection_message(session_id)
        await self.send_message(session_id, message)
        print(f"✅ WebSocket connection established: {session_id}")
    
    def disconnect(self, session_id: str):
        """Remove connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_agents:
            del self.session_agents[session_id]
        print(f"❌ WebSocket connection closed: {session_id}")
    
    async def send_message(self, session_id: str, message: WebSocketMessage):
        """Send message to specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(message.model_dump_json())
            except Exception as e:
                print(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast_message(self, message: WebSocketMessage):
        """Broadcast message to all connected sessions"""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message.model_dump_json())
            except Exception as e:
                print(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)


class WebSocketTraceManager(TraceManager):
    """Enhanced TraceManager that sends events via WebSocket"""
    
    def __init__(self, connection_manager: WebSocketConnectionManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection_manager = connection_manager
        self.current_session_id = None
        
        # Override storage methods to add WebSocket notifications
        original_save_run = self.storage.save_run
        
        async def websocket_save_run(run):
            result = await original_save_run(run)
            await self._notify_run_update(run)
            return result
        
        self.storage.save_run = websocket_save_run
    
    def set_current_session(self, session_id: str):
        """Set current session for WebSocket notifications"""
        self.current_session_id = session_id
    
    @asynccontextmanager
    async def trace(self, *args, **kwargs):
        """Override trace method to add WebSocket notifications"""
        async with super().trace(*args, **kwargs) as trace_ctx:
            await self._notify_trace_started(trace_ctx)
            yield trace_ctx
            await self._notify_trace_completed(trace_ctx)
    
    async def _notify_trace_started(self, trace_ctx):
        """Notify trace started via WebSocket"""
        if not self.current_session_id:
            return
        
        trace_data = TraceStartedData(
            trace_id=trace_ctx.id,
            trace_name=trace_ctx.name,
            request=trace_ctx.request or "",
            agent_name=getattr(trace_ctx.metadata, "custom_fields", {}).get("agent_name", "unknown") if trace_ctx.metadata else "unknown",
            max_steps=getattr(trace_ctx.metadata, "custom_fields", {}).get("max_steps", 10) if trace_ctx.metadata else 10,
            metadata=trace_ctx.metadata.model_dump() if trace_ctx.metadata else None
        )
        
        message = create_trace_started_message(trace_data, self.current_session_id)
        await self.connection_manager.send_message(self.current_session_id, message)
    
    async def _notify_trace_completed(self, trace_ctx):
        """Notify trace completed via WebSocket"""
        if not self.current_session_id:
            return
        
        trace_data = TraceCompletedData(
            trace_id=trace_ctx.id,
            duration_ms=trace_ctx.duration_ms,
            total_runs=len(trace_ctx.runs),
            status=trace_ctx.status.value if hasattr(trace_ctx.status, 'value') else str(trace_ctx.status),
            total_cost=trace_ctx.total_cost,
            total_tokens=trace_ctx.total_tokens,
            final_response=trace_ctx.response
        )
        
        message = create_trace_completed_message(trace_data, self.current_session_id)
        await self.connection_manager.send_message(self.current_session_id, message)
    
    async def _notify_run_update(self, run):
        """Notify run update via WebSocket"""
        if not self.current_session_id:
            return
        
        # Determine event type based on run status and type
        if run.status == RunStatus.ERROR:
            event_type = TraceEventType.RUN_ERROR
        elif run.status == RunStatus.SUCCESS:
            if run.run_type == RunType.THINK:
                event_type = TraceEventType.THINK_COMPLETED
            elif run.run_type == RunType.TOOL:
                event_type = TraceEventType.TOOL_COMPLETED
            elif run.run_type == RunType.SUMMARY:
                event_type = TraceEventType.SUMMARY_COMPLETED
            else:
                event_type = TraceEventType.RUN_COMPLETED
        elif run.status == RunStatus.RUNNING:
            if run.run_type == RunType.THINK:
                event_type = TraceEventType.THINK_STARTED
            elif run.run_type == RunType.TOOL:
                event_type = TraceEventType.TOOL_STARTED
            elif run.run_type == RunType.SUMMARY:
                event_type = TraceEventType.SUMMARY_STARTED
            else:
                event_type = TraceEventType.RUN_STARTED
        else:
            event_type = TraceEventType.RUN_UPDATED
        
        run_data = RunEventData(
            run_id=run.id,
            trace_id=run.trace_id,
            parent_run_id=run.parent_run_id,
            name=run.name,
            run_type=run.run_type.value if hasattr(run.run_type, 'value') else str(run.run_type),
            status=run.status.value if hasattr(run.status, 'value') else str(run.status),
            start_time=run.start_time,
            end_time=run.end_time,
            duration_ms=run.duration_ms,
            inputs=run.inputs,
            outputs=run.outputs,
            error=run.error,
            error_type=run.error_type,
            metadata=run.metadata
        )
        
        message = create_run_event_message(event_type, run_data, self.current_session_id)
        await self.connection_manager.send_message(self.current_session_id, message)


# Global connection manager
connection_manager = WebSocketConnectionManager()

# Create FastAPI app
app = FastAPI(title="MyAgent WebSocket Trace Server", version="1.0.0")

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


@app.get("/")
async def get_index():
    """Serve the main web interface"""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MyAgent Real-time Trace Monitor</title>
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 MyAgent Real-time Trace Monitor</h1>
                <p>Real-time monitoring of AI agent execution traces</p>
            </div>
            
            <div class="controls">
                <div style="margin-bottom: 15px;">
                    <input type="text" id="questionInput" placeholder="Enter your question..." value="显示用户表的10条用户数据">
                    <button id="startButton" onclick="startAgent()">🚀 Start Agent</button>
                    <button id="clearButton" onclick="clearTrace()" style="margin-left: 10px; background: #6c757d;">🗑️ Clear</button>
                </div>
                <div class="status" id="connectionStatus">
                    Status: <span id="statusText">Connecting...</span>
                </div>
            </div>
            
            <div class="trace-section">
                <div class="trace-header" onclick="toggleTraceSection()">
                    <div>
                        <strong>📋 Execution Trace</strong>
                        <span id="traceCount" style="color: #6c757d; margin-left: 10px;">(0 events)</span>
                    </div>
                    <span class="collapse-icon">▼</span>
                </div>
                <div class="trace-content" id="traceContent">
                    <p style="color: #666; text-align: center;">Connecting to WebSocket server...</p>
                </div>
            </div>
            
            <div class="final-output">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3>🎯 Final Output</h3>
                    <button id="skipTypingButton" style="display: none; background: #6c757d; padding: 5px 10px; font-size: 0.8em;" onclick="skipTypewriting()">⏩ Skip Typing</button>
                </div>
                <div class="output-content" id="finalOutput">
                    <span class="output-placeholder">The final agent response will appear here...</span>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let sessionId = 'session_' + Math.random().toString(36).substring(7);
            let eventCount = 0;
            let finalResponse = '';
            let isTyping = false;
            let typewriterTimeout = null;
            let fullResponseText = '';
            let isRealTimeStreaming = false;
            let streamingContainer = null;
            let currentStreamId = null;

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
                
                // Re-enable start button
                document.getElementById('startButton').disabled = false;
                document.getElementById('startButton').textContent = '🚀 Start Agent';
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
                    
                    // Clear connection timeout
                    if (connectionTimeout) {
                        clearTimeout(connectionTimeout);
                        connectionTimeout = null;
                    }
                    
                    document.getElementById('statusText').textContent = 'Connected';
                    document.getElementById('connectionStatus').style.background = '#d4edda';
                    document.getElementById('connectionStatus').style.color = '#155724';
                    
                    // Clear the "Connecting..." message and show connected status
                    const traceContent = document.getElementById('traceContent');
                    if (traceContent.innerHTML.includes('Connecting to WebSocket server')) {
                        traceContent.innerHTML = '';
                        eventCount = 0;
                        updateEventCount();
                    }
                    
                    addTraceEvent('success', '🔗 WebSocket Connected', 'Connected to trace server - ready to monitor agent execution');
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
                            setConnectionTimeout();
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
                document.getElementById('traceCount').textContent = `(${eventCount} events)`;
            }

            function handleTraceMessage(message) {
                const { event_type, timestamp, data } = message;
                
                // Clear connection timeout when we receive any message
                if (connectionTimeout) {
                    clearTimeout(connectionTimeout);
                    connectionTimeout = null;
                }
                
                switch(event_type) {
                    case 'connection_established':
                        console.log('Received connection_established event');
                        addTraceEvent('success', '🔗 Connection Established', 'WebSocket connection ready for agent execution');
                        break;
                    
                    case 'trace_started':
                        // Clear previous results and reset streaming state
                        clearFinalOutput();
                        resetStreamingState();
                        addTraceEvent('info', '🚀 Trace Started', 
                            `Agent: ${data.agent_name}<br>Request: ${data.request}<br>Max Steps: ${data.max_steps}`);
                        break;
                    
                    case 'trace_completed':
                        addTraceEvent('success', '✅ Trace Completed', 
                            `Duration: ${data.duration_ms?.toFixed(2)}ms<br>Total Runs: ${data.total_runs}<br>Status: ${data.status}`);
                        
                        // Only show typewriter effect if real-time streaming didn't happen
                        if (!isRealTimeStreaming && !streamingContainer) {
                            // Show final response with typewriter effect (fallback for non-streaming)
                            if (data.final_response) {
                                showFinalOutputWithTypewriter(data.final_response);
                            } else {
                                showFinalOutputWithTypewriter('Trace completed but no final response available');
                            }
                        } else {
                            // If streaming already happened, just store the final response
                            fullResponseText = data.final_response || fullResponseText;
                            
                            // Show completion message if final output is empty
                            const finalOutput = document.getElementById('finalOutput');
                            if (!finalOutput.textContent.trim() || finalOutput.innerHTML.includes('output-placeholder')) {
                                showFinalOutput(data.final_response || 'Trace completed but no final response available');
                            }
                        }
                        
                        document.getElementById('startButton').disabled = false;
                        document.getElementById('startButton').textContent = '🚀 Start Agent';
                        break;
                    
                    case 'status_update':
                        // Don't try to extract final output from status messages
                        // Only use the official final_response from trace_completed event
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
                    
                    case 'summary_started':
                        addTraceEvent('info', '📝 Summary Generation Started', 
                            `Triggered by: ${data.special_tool_name || 'Unknown'}<br>Message cleaning: ${data.original_message_count} → ${data.cleaned_message_count} messages`);
                        break;
                    
                    case 'summary_completed':
                        const summaryLength = data.summary_length || (data.summary_content?.length || 0);
                        addTraceEvent('success', '✨ Summary Generation Completed', 
                            `Duration: ${data.duration_ms?.toFixed(2)}ms<br>Summary length: ${summaryLength} characters<br>Success: ${data.success ? 'Yes' : 'No'}`);
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
                    
                    case 'run_error':
                        addTraceEvent('error', `❌ Error in ${data.name}`, 
                            `Error: ${data.error}<br>Type: ${data.error_type || 'Unknown'}`);
                        break;
                    
                    default:
                        console.log('Unhandled event:', event_type, data);
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

            function showFinalOutputWithTypewriter(response) {
                const finalOutput = document.getElementById('finalOutput');
                const skipButton = document.getElementById('skipTypingButton');
                const text = response || 'No response received';
                
                // Store full response for skip functionality
                fullResponseText = text;
                isTyping = true;
                
                // Show skip button
                skipButton.style.display = 'inline-block';
                
                // Clear current content and show cursor
                finalOutput.innerHTML = '<span class="typewriter-cursor"></span>';
                finalOutput.className = 'output-content';
                
                // Create container for typed text
                const textContainer = document.createElement('div');
                textContainer.className = 'typewriter-output';
                finalOutput.insertBefore(textContainer, finalOutput.firstChild);
                
                let currentIndex = 0;
                const typeSpeed = 25; // milliseconds per character
                const pauseAfterPunctuation = 150; // extra pause after . ! ?
                const pauseAfterNewline = 300; // extra pause after newlines
                
                function typeNextCharacter() {
                    // Check if typing was cancelled
                    if (!isTyping) {
                        return;
                    }
                    
                    if (currentIndex < text.length) {
                        const char = text[currentIndex];
                        
                        // Handle newlines by creating line breaks
                        if (char === '\\n') {
                            textContainer.appendChild(document.createElement('br'));
                        } else {
                            // Create a text node and add it
                            const textNode = document.createTextNode(char);
                            textContainer.appendChild(textNode);
                        }
                        
                        currentIndex++;
                        
                        // Variable typing speed based on character
                        let delay = typeSpeed;
                        if (char === '.' || char === '!' || char === '?') {
                            delay += pauseAfterPunctuation;
                        } else if (char === '\\n') {
                            delay += pauseAfterNewline;
                        }
                        
                        // Scroll to show the latest text
                        finalOutput.scrollTop = finalOutput.scrollHeight;
                        
                        typewriterTimeout = setTimeout(typeNextCharacter, delay);
                    } else {
                        // Typing completed
                        isTyping = false;
                        skipButton.style.display = 'none';
                        
                        // Remove cursor when typing is complete
                        const cursor = finalOutput.querySelector('.typewriter-cursor');
                        if (cursor) {
                            setTimeout(() => cursor.remove(), 1000); // Keep cursor for 1 second after completion
                        }
                    }
                }
                
                // Start typing with a small delay and show "typing..." indicator
                addTraceEvent('info', '⌨️ Generating Response', 'AI is typing the final response...');
                typewriterTimeout = setTimeout(typeNextCharacter, 500);
            }

            function skipTypewriting() {
                if (isTyping) {
                    // Cancel current typing
                    isTyping = false;
                    if (typewriterTimeout) {
                        clearTimeout(typewriterTimeout);
                    }
                    
                    // Show full response immediately
                    const finalOutput = document.getElementById('finalOutput');
                    finalOutput.innerHTML = fullResponseText || 'No response received';
                    finalOutput.className = 'output-content';
                    
                    // Hide skip button
                    document.getElementById('skipTypingButton').style.display = 'none';
                }
            }

            function clearFinalOutput() {
                // Reset typing state
                isTyping = false;
                if (typewriterTimeout) {
                    clearTimeout(typewriterTimeout);
                }
                document.getElementById('skipTypingButton').style.display = 'none';
                
                // Reset streaming state
                resetStreamingState();
                
                const finalOutput = document.getElementById('finalOutput');
                finalOutput.innerHTML = '<span class="output-placeholder">The final agent response will appear here...</span>';
                finalOutput.className = 'output-content';
            }

            function startAgent() {
                const question = document.getElementById('questionInput').value;
                if (!question.trim()) {
                    alert('Please enter a question');
                    return;
                }
                
                // Reset counters
                eventCount = 0;
                updateEventCount();
                
                document.getElementById('startButton').disabled = true;
                document.getElementById('startButton').textContent = '⏳ Running...';
                
                // Send start request
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        action: 'start_agent',
                        question: question
                    }));
                } else {
                    alert('WebSocket not connected');
                    document.getElementById('startButton').disabled = false;
                    document.getElementById('startButton').textContent = '🚀 Start Agent';
                }
            }

            function clearTrace() {
                document.getElementById('traceContent').innerHTML = '';
                eventCount = 0;
                updateEventCount();
                clearFinalOutput();
            }

            // Connection timeout handling
            let connectionTimeout = null;
            
            function setConnectionTimeout() {
                if (connectionTimeout) {
                    clearTimeout(connectionTimeout);
                }
                connectionTimeout = setTimeout(() => {
                    if (!ws || ws.readyState !== WebSocket.OPEN) {
                        document.getElementById('statusText').textContent = 'Connection Timeout';
                        document.getElementById('connectionStatus').style.background = '#f8d7da';
                        document.getElementById('connectionStatus').style.color = '#721c24';
                        addTraceEvent('error', '⏰ Connection Timeout', 'Failed to connect to WebSocket server within 10 seconds. Please check if the server is running.');
                    }
                }, 10000); // 10 second timeout
            }
            
            // Connect on page load
            connect();
            setConnectionTimeout();
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time trace communication"""
    await connection_manager.connect(websocket, session_id)
    
    # Setup enhanced trace manager for this session
    websocket_trace_manager = WebSocketTraceManager(connection_manager)
    websocket_trace_manager.set_current_session(session_id)
    set_trace_manager(websocket_trace_manager)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "start_agent":
                # Start agent execution in background task
                question = message.get("question", "显示用户表的10条用户数据")
                asyncio.create_task(run_agent_for_session(session_id, question))
            
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error for session {session_id}: {e}")
        connection_manager.disconnect(session_id)


async def run_agent_for_session(session_id: str, question: str):
    """Run agent for specific session"""
    try:
        # Create MySQL tools
        schema_tool = MySQLSchemaTool()
        query_tool = MySQLQueryTool()
        
        # Create trace metadata
        metadata = TraceMetadata(
            user_id=f"websocket_user_{session_id}",
            session_id=session_id,
            tags=["websocket", "mysql", "realtime"],
            environment="websocket_demo",
            custom_fields={
                "question": question,
                "interface": "websocket",
                "agent_name": "websocket-mysql-agent",
                "max_steps": 10
            }
        )
        
        # Create agent
        agent = create_react_agent(
            name="websocket-mysql-agent",
            tools=[schema_tool, query_tool],
            system_prompt=(
                "You are a MySQL expert that translates natural language to SQL. "
                "Always inspect schema first if needed, then write and execute queries. "
                "Keep responses concise and focused."
            ),
            next_step_prompt="Use mysql_schema to check structure, mysql_query to get data.",
            max_steps=10,
            enable_tracing=True,
            trace_metadata=metadata
        )
        
        # Store agent in session
        connection_manager.session_agents[session_id] = agent
        
        # Run agent
        result = await agent.run(question)
        
        # Send completion status
        status_data = StatusUpdateData(
            current_step=agent.current_step,
            max_steps=agent.max_steps,
            agent_state=str(agent.state),
            message=f"Agent completed successfully: {result[:100]}...",
            progress_percentage=100.0
        )
        
        completion_message = create_status_message(status_data, session_id)
        await connection_manager.send_message(session_id, completion_message)
        
    except Exception as e:
        print(f"Error running agent for session {session_id}: {e}")
        
        # Send error status
        error_status = StatusUpdateData(
            current_step=0,
            max_steps=10,
            agent_state="ERROR",
            message=f"Agent execution failed: {str(e)}",
            progress_percentage=0.0
        )
        
        error_message = create_status_message(error_status, session_id)
        await connection_manager.send_message(session_id, error_message)


if __name__ == "__main__":
    print("🚀 Starting MyAgent WebSocket Trace Server...")
    print("📍 Server will be available at: http://localhost:8234")
    print("🔌 WebSocket endpoint: ws://localhost:8234/ws/{session_id}")
    print()
    print("Make sure to set MySQL environment variables:")
    print("  - MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8234,
        log_level="info"
    )