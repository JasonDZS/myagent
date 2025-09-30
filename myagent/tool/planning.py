#!/usr/bin/env python3
"""
Deep Agents Planning Tool

Implements task management and planning capabilities similar to DeepAgents' write_todos tool.
Provides structured task breakdown and progress tracking.
"""

from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field

from .base_tool import BaseTool, ToolResult


class TodoItem(BaseModel):
    """Represents a single todo item."""
    
    content: str = Field(..., description="Task description")
    status: Literal["pending", "in_progress", "completed"] = Field(
        default="pending", description="Current task status"
    )
    activeForm: str = Field(..., description="Present continuous form for active display")
    priority: Literal["high", "medium", "low"] = Field(
        default="medium", description="Task priority level"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="List of dependencies"
    )


class PlanningTool(BaseTool):
    """
    Task planning and management tool for complex multi-step operations.
    
    Enables agents to create, update, and track structured task lists for 
    complex goals that require planning and step-by-step execution.
    """
    
    name: str = "write_todos"
    description: str = (
        "Create and manage structured task lists for complex goals. "
        "Use this tool when you need to break down complex tasks into manageable steps, "
        "track progress, or organize multi-step workflows. Only use for tasks with 3+ steps."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "List of todo items with status tracking",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Imperative form describing what needs to be done"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "Current status of the task"
                        },
                        "activeForm": {
                            "type": "string", 
                            "description": "Present continuous form shown during execution"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Task priority level"
                        },
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of task dependencies"
                        }
                    },
                    "required": ["content", "status", "activeForm"]
                }
            }
        },
        "required": ["todos"]
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._todo_state: List[TodoItem] = []

    async def execute(self, todos: List[Dict[str, Any]]) -> ToolResult:
        """
        Execute the planning tool to create/update todo list.
        
        Args:
            todos: List of todo items with status and metadata
            
        Returns:
            ToolResult with formatted todo list and status summary
        """
        try:
            # Validate and convert todos to TodoItem objects
            todo_items = []
            for todo_data in todos:
                try:
                    todo_item = TodoItem(**todo_data)
                    todo_items.append(todo_item)
                except Exception as e:
                    return ToolResult(
                        error=f"Invalid todo item format: {todo_data}. Error: {str(e)}"
                    )
            
            # Update internal state
            self._todo_state = todo_items
            
            # Generate formatted output
            output = self._format_todo_list(todo_items)
            
            # Add status summary
            status_summary = self._generate_status_summary(todo_items)
            
            return ToolResult(
                output=f"{output}\n\n{status_summary}",
                system=f"Todo list updated with {len(todo_items)} items"
            )
            
        except Exception as e:
            return ToolResult(error=f"Planning tool execution failed: {str(e)}")

    def _format_todo_list(self, todos: List[TodoItem]) -> str:
        """Format todo list for display."""
        if not todos:
            return "📋 No tasks planned yet."
        
        formatted = ["📋 **Task Planning Overview**\n"]
        
        # Group by status for better organization
        status_groups = {
            "in_progress": [],
            "pending": [],
            "completed": []
        }
        
        for todo in todos:
            status_groups[todo.status].append(todo)
        
        # Display in_progress tasks first
        if status_groups["in_progress"]:
            formatted.append("🔄 **Currently Working On:**")
            for todo in status_groups["in_progress"]:
                priority_emoji = self._get_priority_emoji(todo.priority)
                formatted.append(f"  {priority_emoji} {todo.activeForm}")
            formatted.append("")
        
        # Then pending tasks
        if status_groups["pending"]:
            formatted.append("⏳ **Pending Tasks:**")
            for i, todo in enumerate(status_groups["pending"], 1):
                priority_emoji = self._get_priority_emoji(todo.priority)
                formatted.append(f"  {i}. {priority_emoji} {todo.content}")
                if todo.dependencies:
                    formatted.append(f"     📎 Dependencies: {', '.join(todo.dependencies)}")
            formatted.append("")
        
        # Finally completed tasks
        if status_groups["completed"]:
            formatted.append("✅ **Completed:**")
            for todo in status_groups["completed"]:
                formatted.append(f"  ✓ {todo.content}")
        
        return "\n".join(formatted)

    def _generate_status_summary(self, todos: List[TodoItem]) -> str:
        """Generate a summary of task status."""
        if not todos:
            return ""
        
        total = len(todos)
        completed = len([t for t in todos if t.status == "completed"])
        in_progress = len([t for t in todos if t.status == "in_progress"])
        pending = len([t for t in todos if t.status == "pending"])
        
        progress_percentage = int((completed / total) * 100) if total > 0 else 0
        
        summary = [
            f"📊 **Progress Summary:**",
            f"  • Total Tasks: {total}",
            f"  • Completed: {completed} ({progress_percentage}%)",
            f"  • In Progress: {in_progress}",
            f"  • Pending: {pending}",
        ]
        
        # Add progress bar
        progress_bar = self._create_progress_bar(progress_percentage)
        summary.append(f"  • Progress: {progress_bar}")
        
        return "\n".join(summary)

    def _get_priority_emoji(self, priority: str) -> str:
        """Get emoji for priority level."""
        return {
            "high": "🔴",
            "medium": "🟡", 
            "low": "🟢"
        }.get(priority, "🟡")

    def _create_progress_bar(self, percentage: int, width: int = 20) -> str:
        """Create a visual progress bar."""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"{bar} {percentage}%"

    def get_current_todos(self) -> List[TodoItem]:
        """Get current todo state."""
        return self._todo_state

    def get_active_task(self) -> TodoItem | None:
        """Get the currently active (in_progress) task."""
        for todo in self._todo_state:
            if todo.status == "in_progress":
                return todo
        return None

    def complete_task(self, task_content: str) -> bool:
        """Mark a task as completed by content."""
        for todo in self._todo_state:
            if todo.content == task_content and todo.status == "in_progress":
                todo.status = "completed"
                return True
        return False

    def start_task(self, task_content: str) -> bool:
        """Mark a task as in_progress by content."""
        for todo in self._todo_state:
            if todo.content == task_content and todo.status == "pending":
                todo.status = "in_progress"
                return True
        return False