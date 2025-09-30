#!/usr/bin/env python3
"""
Sub-Agent Middleware

Adds sub-agent delegation capabilities to agents.
Provides task delegation tools and sub-agent management.
"""

from typing import List
from myagent.tool.base_tool import BaseTool
from myagent.tool.subagent import SubAgentTool
from .base import BaseMiddleware, MiddlewareContext


class SubAgentMiddleware(BaseMiddleware):
    """
    Middleware that adds sub-agent delegation capabilities to agents.
    
    Provides:
    - task tool for sub-agent delegation
    - Sub-agent management and configuration
    - Context isolation and parallel execution
    """
    
    name: str = "subagent_middleware"
    description: str = "Adds sub-agent delegation capabilities"
    priority: int = 30  # After filesystem, before summary
    
    def __init__(self, default_tools: List[BaseTool] = None, **kwargs):
        super().__init__(**kwargs)
        self._subagent_tool = SubAgentTool()
        
        # Set default tools for sub-agents
        if default_tools:
            self._subagent_tool.set_default_tools(default_tools)
    
    async def process(self, context: MiddlewareContext) -> MiddlewareContext:
        """Add sub-agent tool and prompt to context."""
        
        # Provide current context tools to sub-agents
        self._subagent_tool.set_default_tools(context.tools.copy())
        
        # Add sub-agent tool
        context.tools.append(self._subagent_tool)
        
        # Add sub-agent guidance to system prompt
        subagent_prompt = self.get_system_prompt_addition(context)
        if subagent_prompt:
            context.system_prompt_parts.append(subagent_prompt)
        
        # Add sub-agent metadata
        context.metadata["has_subagents"] = True
        context.metadata["available_subagents"] = self._subagent_tool.get_available_subagents()
        
        return context
    
    def get_tools(self) -> List[BaseTool]:
        """Return the sub-agent tool."""
        return [self._subagent_tool]
    
    def get_system_prompt_addition(self, context: MiddlewareContext) -> str:
        """Return sub-agent-specific system prompt."""
        available_types = self._subagent_tool.get_available_subagents()
        types_list = ", ".join(available_types)
        
        return f"""## Sub-Agent Delegation

You can delegate complex, independent tasks to specialized sub-agents using the `task` tool.

**Available sub-agent types:**
{types_list}

**When to use sub-agents:**
1. **Independent tasks** - When a task can be completed without ongoing interaction
2. **Context isolation** - When you want to avoid cluttering your main context
3. **Specialized work** - When a task requires specific expertise (research, code review, etc.)
4. **Parallel execution** - When multiple tasks can be done simultaneously
5. **Complex multi-step work** - When a task requires its own workflow

**Sub-agent delegation best practices:**
1. Provide clear, complete task descriptions
2. Include all necessary context and constraints  
3. Choose the appropriate sub-agent type for the task
4. Let sub-agents work independently - they have access to the same tools
5. Use for tasks that benefit from focused, isolated execution

**Sub-agent types:**
- `general-purpose`: For complex multi-step tasks requiring planning
- `research-agent`: For research, analysis, and information gathering
- `code-reviewer`: For code analysis, review, and improvement suggestions

**Example usage:**
```
task(
  description="Research the latest developments in quantum computing and create a comprehensive report",
  subagent_type="research-agent"
)
```

Sub-agents will return complete results that you can use in your main workflow."""
    
    def register_subagent(self, config):
        """Register a custom sub-agent configuration."""
        self._subagent_tool.register_subagent(config)
    
    def get_subagent_info(self, subagent_type: str):
        """Get information about a specific sub-agent type."""
        return self._subagent_tool.get_subagent_info(subagent_type)