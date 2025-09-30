"""
MyAgent - Lightweight toolkit for building tool-aware LLM agents

A comprehensive framework for building LLM agents with:
- ReAct-style reasoning and action patterns
- Comprehensive tracing and debugging capabilities
- WebSocket server support for real-time interactions
- Rich tool ecosystem with built-in safety features
"""

from .agent import BaseAgent
from .agent import ReActAgent
from .agent import ToolCallAgent
from .agent import create_react_agent
from .agent import create_toolcall_agent
from .config import settings
from .llm import LLM
from .logger import logger
from .schema import Message
from .schema import Role
from .schema import ToolCall
from .schema import ToolChoice
from .tool import BaseTool
from .tool import Terminate
from .tool import ToolCollection
from .tool.base_tool import ToolResult
from .trace import TraceManager
from .trace import trace_agent_step
from .trace import trace_run
from .trace import trace_tool_call
from .type import *

# WebSocket Management System
from .manager import AgentManager, ServiceRegistry, ConnectionRouter, HealthMonitor

# Deep Agents Capabilities
from .middleware import DeepAgentMiddleware, PlanningMiddleware, FilesystemMiddleware, SubAgentMiddleware
from .middleware.deep_agent import create_deep_agent

__version__ = "0.1.0"

__all__ = [
    # Core agent functionality
    "BaseAgent",
    "create_react_agent",
    "create_toolcall_agent",
    "ReActAgent",
    "ToolCallAgent",
    # Core components
    "LLM",
    "logger",
    "settings",
    # Schema types
    "Message",
    "Role",
    "ToolCall",
    "ToolChoice",
    "ToolResult",
    # Tool system
    "BaseTool",
    "Terminate",
    "ToolCollection",
    # Tracing system
    "TraceManager",
    "trace_agent_step",
    "trace_run",
    "trace_tool_call",
    # Management system
    "AgentManager",
    "ServiceRegistry",
    "ConnectionRouter", 
    "HealthMonitor",
    # Deep Agents system
    "DeepAgentMiddleware",
    "PlanningMiddleware", 
    "FilesystemMiddleware",
    "SubAgentMiddleware",
    "create_deep_agent",
]
