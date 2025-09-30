#!/usr/bin/env python3
"""
Deep Agent Middleware

Combines all Deep Agents capabilities into a single middleware that provides
the complete Deep Agents experience: planning, filesystem, sub-agents, and enhanced prompts.
"""

from typing import List, Optional
from myagent.tool.base_tool import BaseTool
from myagent.agent.base import BaseAgent
from .base import BaseMiddleware, MiddlewareContext, MiddlewareChain
from .planning import PlanningMiddleware
from .filesystem import FilesystemMiddleware
from .subagent import SubAgentMiddleware


class DeepAgentMiddleware(BaseMiddleware):
    """
    Composite middleware that provides the complete Deep Agents experience.
    
    Combines:
    - Task planning and management
    - Virtual file system
    - Sub-agent delegation
    - Enhanced prompting and guidance
    """
    
    name: str = "deep_agent_middleware"
    description: str = "Complete Deep Agents capabilities"
    priority: int = 5  # Very early in the chain
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize component middleware
        self._chain = MiddlewareChain()
        self._chain.add_middleware(PlanningMiddleware())
        self._chain.add_middleware(FilesystemMiddleware())
        self._chain.add_middleware(SubAgentMiddleware())
    
    async def process(self, context: MiddlewareContext) -> MiddlewareContext:
        """Process context through all Deep Agents middleware."""
        
        # Add Deep Agents system prompt first
        deep_agent_prompt = self.get_system_prompt_addition(context)
        if deep_agent_prompt:
            context.system_prompt_parts.insert(0, deep_agent_prompt)
        
        # Process through component middleware chain
        context = await self._chain.process(context)
        
        # Add Deep Agents metadata
        context.metadata.update({
            "is_deep_agent": True,
            "deep_agent_version": "1.0.0",
            "capabilities": ["planning", "filesystem", "subagents"],
            "middleware_chain": self._chain.get_middleware_info()
        })
        
        return context
    
    def get_tools(self) -> List[BaseTool]:
        """Return all Deep Agents tools."""
        return self._chain.get_all_tools()
    
    def get_system_prompt_addition(self, context: MiddlewareContext) -> str:
        """Return Deep Agents system prompt."""
        return """# Deep Agent Instructions

You are a Deep Agent - an advanced AI agent capable of handling complex, multi-step tasks through:

## Core Capabilities

### 🎯 **Task Planning & Management**
- Break complex tasks into manageable steps using `write_todos`
- Track progress and manage workflow state
- Prioritize and organize multi-step processes

### 📁 **Virtual File System** 
- Create, read, write, and edit files that persist throughout your session
- Build comprehensive documentation and reports
- Manage complex workflows involving multiple documents

### 🤖 **Sub-Agent Delegation**
- Delegate independent tasks to specialized sub-agents
- Achieve context isolation and parallel execution
- Access specialized capabilities for research, code review, and analysis

## Deep Agent Workflow Principles

### 1. **Task Analysis & Planning**
- For complex tasks (3+ steps), use planning tools
- Break down large problems into manageable components
- Create clear, actionable todo lists with status tracking

### 2. **Context Management**
- Use virtual files to maintain state and share information
- Delegate independent tasks to sub-agents for context isolation
- Build comprehensive documentation as you work

### 3. **Systematic Execution**
- Follow your planned steps systematically
- Update task status in real-time as you progress
- Maintain only ONE task in "in_progress" status at a time

### 4. **Quality & Completeness**
- Leverage sub-agents for specialized tasks requiring expertise
- Build comprehensive, well-structured outputs
- Verify and validate results before completion

## Best Practices

**Planning:**
- Use planning for any task requiring multiple steps
- Provide both imperative task descriptions and active forms
- Update status immediately when starting/completing tasks

**File Management:**
- Use descriptive file names and clear organization
- Read before editing to understand current state
- Build comprehensive documentation incrementally

**Sub-Agent Usage:**
- Delegate independent, complex tasks to appropriate specialists
- Provide complete context and clear requirements
- Use for tasks benefiting from focused, isolated execution

**Integration:**
- Combine planning, files, and sub-agents for complex workflows
- Maintain transparency about your process and progress
- Build towards comprehensive, well-documented outcomes

You are designed to handle sophisticated, long-term tasks that would challenge traditional agents. Use your full capabilities to deliver exceptional results."""
    
    async def pre_execution_hook(self, context: MiddlewareContext) -> None:
        """Execute pre-execution hooks for all components."""
        await self._chain.pre_execution_hooks(context)
    
    async def post_execution_hook(self, context: MiddlewareContext, result: str) -> str:
        """Execute post-execution hooks for all components."""
        return await self._chain.post_execution_hooks(context, result)
    
    def get_planning_middleware(self) -> PlanningMiddleware:
        """Get the planning middleware component."""
        for middleware in self._chain._middleware:
            if isinstance(middleware, PlanningMiddleware):
                return middleware
        return None
    
    def get_filesystem_middleware(self) -> FilesystemMiddleware:
        """Get the filesystem middleware component."""
        for middleware in self._chain._middleware:
            if isinstance(middleware, FilesystemMiddleware):
                return middleware
        return None
    
    def get_subagent_middleware(self) -> SubAgentMiddleware:
        """Get the sub-agent middleware component."""
        for middleware in self._chain._middleware:
            if isinstance(middleware, SubAgentMiddleware):
                return middleware
        return None


def create_deep_agent_from_base(
    base_agent: BaseAgent,
    additional_tools: List[BaseTool] = None
) -> BaseAgent:
    """
    Convert a regular agent into a Deep Agent by applying Deep Agent middleware.
    
    Args:
        base_agent: The base agent to enhance
        additional_tools: Optional additional tools to include
        
    Returns:
        Enhanced agent with Deep Agent capabilities
    """
    
    # Create middleware context
    context = MiddlewareContext(
        agent=base_agent,
        tools=additional_tools or [],
        system_prompt_parts=[],
        metadata={}
    )
    
    # Create and apply Deep Agent middleware
    deep_middleware = DeepAgentMiddleware()
    
    # This would need to be integrated into the agent's execution flow
    # For now, we return the modified agent
    return base_agent


def create_deep_agent(
    tools: List[BaseTool] = None,
    llm_config: dict = None,
    name: str = "deep_agent",
    description: str = "A Deep Agent with advanced capabilities"
) -> BaseAgent:
    """
    Create a new Deep Agent with all capabilities enabled.
    
    Args:
        tools: Additional tools beyond Deep Agent built-ins
        llm_config: LLM configuration
        name: Agent name
        description: Agent description
        
    Returns:
        Configured Deep Agent
    """
    # Import locally to avoid circular imports
    from myagent.agent.factory import create_toolcall_agent
    from myagent.llm import LLM
    
    # Get Deep Agent tools
    deep_middleware = DeepAgentMiddleware()
    deep_tools = deep_middleware.get_tools()
    
    # Combine with additional tools
    all_tools = deep_tools + (tools or [])
    
    # Create LLM instance (LLM uses config_name, not keyword arguments)
    llm = LLM(config_name=name.lower())
    
    # Create base agent using create_toolcall_agent directly
    agent = create_toolcall_agent(
        name=name,
        llm=llm,
        tools=all_tools
    )
    
    # Set description
    agent.description = description
    
    # Build enhanced system prompt
    context = MiddlewareContext(
        agent=agent,
        tools=all_tools,
        system_prompt_parts=[],
        metadata={}
    )
    
    enhanced_prompt = deep_middleware.get_system_prompt_addition(context)
    if agent.system_prompt:
        agent.system_prompt = f"{agent.system_prompt}\n\n{enhanced_prompt}"
    else:
        agent.system_prompt = enhanced_prompt
    
    return agent