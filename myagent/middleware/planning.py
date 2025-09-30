#!/usr/bin/env python3
"""
Planning Middleware

Adds task planning and management capabilities to agents.
Provides the write_todos tool and planning-specific prompts.
"""

from typing import List
from myagent.tool.base_tool import BaseTool
from myagent.tool.planning import PlanningTool
from .base import BaseMiddleware, MiddlewareContext


class PlanningMiddleware(BaseMiddleware):
    """
    Middleware that adds task planning capabilities to agents.
    
    Provides:
    - write_todos tool for task management
    - Planning-specific system prompts
    - Task breakdown guidance
    """
    
    name: str = "planning_middleware"
    description: str = "Adds task planning and management capabilities"
    priority: int = 10  # Early in the chain
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._planning_tool = PlanningTool()
    
    async def process(self, context: MiddlewareContext) -> MiddlewareContext:
        """Add planning tool and prompt to context."""
        
        # Add planning tool
        context.tools.append(self._planning_tool)
        
        # Add planning guidance to system prompt
        planning_prompt = self.get_system_prompt_addition(context)
        if planning_prompt:
            context.system_prompt_parts.append(planning_prompt)
        
        # Add planning metadata
        context.metadata["has_planning"] = True
        context.metadata["planning_tool"] = self._planning_tool.name
        
        return context
    
    def get_tools(self) -> List[BaseTool]:
        """Return the planning tool."""
        return [self._planning_tool]
    
    def get_system_prompt_addition(self, context: MiddlewareContext) -> str:
        """Return planning-specific system prompt."""
        return """## Task Planning & Management

You have access to the `write_todos` tool for managing complex, multi-step tasks.

**When to use planning:**
- Tasks requiring 3 or more distinct steps
- Complex workflows with multiple components
- When the user explicitly requests a plan
- Tasks that could benefit from parallel execution

**Planning best practices:**
1. Break complex tasks into specific, actionable items
2. Use clear, imperative task descriptions
3. Provide both "content" (what to do) and "activeForm" (present continuous for progress)
4. Set appropriate priorities and dependencies
5. Mark tasks as in_progress BEFORE starting work
6. Mark tasks as completed IMMEDIATELY after finishing
7. Only have ONE task in_progress at a time

**Task status workflow:**
- `pending` → `in_progress` → `completed`
- Always update status in real-time as you work
- Complete current tasks before starting new ones

**Example todo structure:**
```json
{
  "content": "Research market trends",
  "status": "pending", 
  "activeForm": "Researching market trends",
  "priority": "high"
}
```

Use planning to organize your work and provide transparency to the user about your progress."""
    
    def get_current_todos(self):
        """Get current todo state from the planning tool."""
        return self._planning_tool.get_current_todos()
    
    def get_active_task(self):
        """Get the currently active task."""
        return self._planning_tool.get_active_task()