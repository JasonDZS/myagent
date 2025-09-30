#!/usr/bin/env python3
"""
Base Middleware System

Provides the foundation for middleware components that can modify agent behavior,
add tools, and customize prompts throughout the agent execution lifecycle.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from myagent.agent.base import BaseAgent
from myagent.tool.base_tool import BaseTool
from myagent.schema import Message


class MiddlewareContext(BaseModel):
    """Context passed through middleware chain."""
    
    agent: BaseAgent = Field(..., description="The agent being processed")
    tools: List[BaseTool] = Field(default_factory=list, description="Available tools")
    system_prompt_parts: List[str] = Field(default_factory=list, description="System prompt components")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        arbitrary_types_allowed = True


class BaseMiddleware(ABC):
    """
    Abstract base class for agent middleware.
    
    Middleware can modify agent behavior by:
    - Adding tools
    - Modifying system prompts
    - Preprocessing requests
    - Postprocessing responses
    """
    
    name: str = "base_middleware"
    description: str = "Base middleware class"
    priority: int = 50  # Lower numbers run first
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @abstractmethod
    async def process(self, context: MiddlewareContext) -> MiddlewareContext:
        """
        Process the context and return modified context.
        
        Args:
            context: The middleware context to process
            
        Returns:
            Modified context
        """
        pass
    
    def get_tools(self) -> List[BaseTool]:
        """Return tools provided by this middleware."""
        return []
    
    def get_system_prompt_addition(self, context: MiddlewareContext) -> str:
        """Return system prompt additions for this middleware."""
        return ""
    
    async def pre_execution_hook(self, context: MiddlewareContext) -> None:
        """Hook called before agent execution."""
        pass
    
    async def post_execution_hook(self, context: MiddlewareContext, result: str) -> str:
        """Hook called after agent execution."""
        return result


class MiddlewareChain:
    """
    Manages and executes a chain of middleware components.
    
    Middleware are executed in priority order (lower numbers first).
    """
    
    def __init__(self):
        self._middleware: List[BaseMiddleware] = []
    
    def add_middleware(self, middleware: BaseMiddleware) -> None:
        """Add middleware to the chain."""
        self._middleware.append(middleware)
        # Sort by priority (lower numbers first)
        self._middleware.sort(key=lambda m: m.priority)
    
    def remove_middleware(self, middleware_name: str) -> bool:
        """Remove middleware by name."""
        for i, middleware in enumerate(self._middleware):
            if middleware.name == middleware_name:
                del self._middleware[i]
                return True
        return False
    
    async def process(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process context through the middleware chain."""
        for middleware in self._middleware:
            context = await middleware.process(context)
        return context
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all tools from all middleware."""
        tools = []
        for middleware in self._middleware:
            tools.extend(middleware.get_tools())
        return tools
    
    def build_system_prompt(self, base_prompt: str, context: MiddlewareContext) -> str:
        """Build system prompt with middleware additions."""
        prompt_parts = [base_prompt] if base_prompt else []
        
        # Add parts from context
        prompt_parts.extend(context.system_prompt_parts)
        
        # Add parts from middleware
        for middleware in self._middleware:
            addition = middleware.get_system_prompt_addition(context)
            if addition:
                prompt_parts.append(addition)
        
        return "\n\n".join(prompt_parts)
    
    async def pre_execution_hooks(self, context: MiddlewareContext) -> None:
        """Execute all pre-execution hooks."""
        for middleware in self._middleware:
            await middleware.pre_execution_hook(context)
    
    async def post_execution_hooks(self, context: MiddlewareContext, result: str) -> str:
        """Execute all post-execution hooks."""
        for middleware in self._middleware:
            result = await middleware.post_execution_hook(context, result)
        return result
    
    def get_middleware_info(self) -> List[Dict[str, Any]]:
        """Get information about all middleware in the chain."""
        return [
            {
                "name": m.name,
                "description": m.description,
                "priority": m.priority,
                "tool_count": len(m.get_tools())
            }
            for m in self._middleware
        ]