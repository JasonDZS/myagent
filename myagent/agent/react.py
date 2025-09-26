from abc import ABC, abstractmethod
from typing import Optional

from pydantic import Field

from .base import BaseAgent
from ..llm import LLM
from ..schema import AgentState, Memory


class ReActAgent(BaseAgent, ABC):
    """Abstract base class for agents implementing the ReAct pattern.
    
    The ReAct (Reasoning + Acting) pattern involves:
    1. Think: Process information and decide on actions
    2. Act: Execute actions using available tools
    
    This is an abstract class that defines the interface for ReAct agents.
    Concrete implementations should inherit from this class and implement
    the think() and act() methods.
    
    For a complete implementation, see ToolCallAgent.
    """
    
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act()
