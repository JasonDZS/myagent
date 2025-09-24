"""WebSocket Trace Protocol Definitions"""

from typing import Any, Dict, Optional, Union
from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class TraceEventType(str, Enum):
    """WebSocket trace event types"""
    # Connection events
    CONNECTION_ESTABLISHED = "connection_established"
    CONNECTION_CLOSED = "connection_closed"
    
    # Agent execution events  
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    
    # Trace events
    TRACE_STARTED = "trace_started"
    TRACE_COMPLETED = "trace_completed"
    
    # Run events
    RUN_STARTED = "run_started"
    RUN_UPDATED = "run_updated"
    RUN_COMPLETED = "run_completed"
    RUN_ERROR = "run_error"
    
    # Step events
    STEP_STARTED = "step_started"
    THINK_STARTED = "think_started" 
    THINK_COMPLETED = "think_completed"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    
    # Status events
    STATUS_UPDATE = "status_update"
    PROGRESS_UPDATE = "progress_update"


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure"""
    event_type: TraceEventType
    timestamp: datetime
    message_id: str
    data: Dict[str, Any]
    session_id: Optional[str] = None


class TraceStartedData(BaseModel):
    """Trace started event data"""
    trace_id: str
    trace_name: str
    request: str
    agent_name: str
    max_steps: int
    metadata: Optional[Dict[str, Any]] = None


class TraceCompletedData(BaseModel):
    """Trace completed event data"""
    trace_id: str
    duration_ms: Optional[float]
    total_runs: int
    status: str
    total_cost: Optional[float] = None
    total_tokens: Optional[int] = None
    final_response: Optional[str] = None


class RunEventData(BaseModel):
    """Run event data"""
    run_id: str
    trace_id: str
    parent_run_id: Optional[str]
    name: str
    run_type: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StatusUpdateData(BaseModel):
    """Status update data"""
    current_step: int
    max_steps: int
    agent_state: str
    message: str
    progress_percentage: Optional[float] = None


class ProgressUpdateData(BaseModel):
    """Progress update data"""
    current_step: int
    total_steps: int
    step_name: str
    step_description: str
    percentage: float
    estimated_time_remaining: Optional[float] = None


# Message factory functions
def create_connection_message(session_id: str) -> WebSocketMessage:
    """Create connection established message"""
    return WebSocketMessage(
        event_type=TraceEventType.CONNECTION_ESTABLISHED,
        timestamp=datetime.now(),
        message_id=f"conn_{datetime.now().timestamp()}",
        session_id=session_id,
        data={"status": "connected", "session_id": session_id}
    )


def create_trace_started_message(trace_data: TraceStartedData, session_id: str) -> WebSocketMessage:
    """Create trace started message"""
    return WebSocketMessage(
        event_type=TraceEventType.TRACE_STARTED,
        timestamp=datetime.now(),
        message_id=f"trace_start_{trace_data.trace_id[:8]}",
        session_id=session_id,
        data=trace_data.model_dump()
    )


def create_trace_completed_message(trace_data: TraceCompletedData, session_id: str) -> WebSocketMessage:
    """Create trace completed message"""
    return WebSocketMessage(
        event_type=TraceEventType.TRACE_COMPLETED,
        timestamp=datetime.now(),
        message_id=f"trace_end_{trace_data.trace_id[:8]}",
        session_id=session_id,
        data=trace_data.model_dump()
    )


def create_run_event_message(event_type: TraceEventType, run_data: RunEventData, session_id: str) -> WebSocketMessage:
    """Create run event message"""
    return WebSocketMessage(
        event_type=event_type,
        timestamp=datetime.now(),
        message_id=f"run_{event_type.value}_{run_data.run_id[:8]}",
        session_id=session_id,
        data=run_data.model_dump()
    )


def create_status_message(status_data: StatusUpdateData, session_id: str) -> WebSocketMessage:
    """Create status update message"""
    return WebSocketMessage(
        event_type=TraceEventType.STATUS_UPDATE,
        timestamp=datetime.now(),
        message_id=f"status_{datetime.now().timestamp()}",
        session_id=session_id,
        data=status_data.model_dump()
    )


def create_progress_message(progress_data: ProgressUpdateData, session_id: str) -> WebSocketMessage:
    """Create progress update message"""
    return WebSocketMessage(
        event_type=TraceEventType.PROGRESS_UPDATE,
        timestamp=datetime.now(),
        message_id=f"progress_{datetime.now().timestamp()}",
        session_id=session_id,
        data=progress_data.model_dump()
    )