"""WebSocket event protocol definitions."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class EventProtocol(BaseModel):
    """WebSocket event protocol."""

    session_id: str | None = Field(None, description="Session ID")
    connection_id: str | None = Field(None, description="Connection ID")
    step_id: str | None = Field(None, description="Step ID")
    event: str = Field(..., description="Event type")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    content: str | dict[str, Any] | None = Field(None, description="Event content")
    metadata: dict[str, Any] | None = Field(
        default_factory=dict, description="Metadata"
    )


class UserEvents:
    """User event types"""

    MESSAGE = "user.message"
    RESPONSE = "user.response"
    CANCEL = "user.cancel"
    CREATE_SESSION = "user.create_session"
    RECONNECT = "user.reconnect"
    RECONNECT_WITH_STATE = "user.reconnect_with_state"
    REQUEST_STATE = "user.request_state"


class AgentEvents:
    """Agent event types"""

    THINKING = "agent.thinking"
    TOOL_CALL = "agent.tool_call"
    TOOL_RESULT = "agent.tool_result"
    PARTIAL_ANSWER = "agent.partial_answer"
    FINAL_ANSWER = "agent.final_answer"
    USER_CONFIRM = "agent.user_confirm"
    ERROR = "agent.error"
    TIMEOUT = "agent.timeout"
    INTERRUPTED = "agent.interrupted"
    SESSION_CREATED = "agent.session_created"
    SESSION_END = "agent.session_end"
    LLM_MESSAGE = "agent.llm_message"
    STATE_EXPORTED = "agent.state_exported"
    STATE_RESTORED = "agent.state_restored"


class SystemEvents:
    """System event types"""

    CONNECTED = "system.connected"
    NOTICE = "system.notice"
    HEARTBEAT = "system.heartbeat"
    ERROR = "system.error"


def create_event(
    event_type: str,
    session_id: str | None = None,
    content: str | dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create standard event"""
    event = {"event": event_type, "timestamp": datetime.now().isoformat()}

    if session_id:
        event["session_id"] = session_id
    if content is not None:
        event["content"] = content
    if metadata:
        event["metadata"] = metadata

    event.update(kwargs)
    return event
