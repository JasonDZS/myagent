"""WebSocket event protocol definitions."""

from datetime import datetime
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class EventProtocol(BaseModel):
    """WebSocket event protocol."""
    
    session_id: Optional[str] = Field(None, description="会话ID")
    connection_id: Optional[str] = Field(None, description="连接ID")  
    step_id: Optional[str] = Field(None, description="步骤ID")
    event: str = Field(..., description="事件类型")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    content: Optional[Union[str, Dict[str, Any]]] = Field(None, description="事件内容")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class UserEvents:
    """用户事件类型"""
    MESSAGE = "user.message"
    RESPONSE = "user.response" 
    CANCEL = "user.cancel"
    CREATE_SESSION = "user.create_session"
    RECONNECT = "user.reconnect"


class AgentEvents:
    """Agent 事件类型"""
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


class SystemEvents:
    """系统事件类型"""
    CONNECTED = "system.connected"
    NOTICE = "system.notice"
    HEARTBEAT = "system.heartbeat"
    ERROR = "system.error"


def create_event(event_type: str, session_id: Optional[str] = None, 
                content: Optional[Union[str, Dict[str, Any]]] = None,
                metadata: Optional[Dict[str, Any]] = None,
                **kwargs) -> Dict[str, Any]:
    """创建标准事件"""
    event = {
        "event": event_type,
        "timestamp": datetime.now().isoformat()
    }
    
    if session_id:
        event["session_id"] = session_id
    if content is not None:
        event["content"] = content
    if metadata:
        event["metadata"] = metadata
        
    event.update(kwargs)
    return event