#!/usr/bin/env python3
"""
Deep Agents Sub-Agent System

Implements sub-agent delegation and management similar to DeepAgents' task tool.
Allows main agents to spawn specialized sub-agents for independent task execution.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import asyncio
import uuid

from myagent.agent.base import BaseAgent
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.tool.tool_collection import ToolCollection
from myagent.schema import Memory, Message


class SubAgentConfig(BaseModel):
    """Configuration for a sub-agent."""
    
    name: str = Field(..., description="Sub-agent name")
    description: str = Field(..., description="Sub-agent capabilities description")
    prompt: str = Field(..., description="System prompt for the sub-agent")
    tools: List[BaseTool] = Field(default_factory=list, description="Available tools")
    llm_config: Dict[str, Any] = Field(default_factory=dict, description="LLM configuration")
    max_steps: int = Field(default=5, description="Maximum execution steps")
    
    class Config:
        arbitrary_types_allowed = True


class SubAgentResult(BaseModel):
    """Result from sub-agent execution."""
    
    agent_name: str
    task_description: str
    success: bool
    result: str
    error: Optional[str] = None
    execution_steps: int = 0
    final_memory: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class SubAgentTool(BaseTool):
    """
    Tool for delegating tasks to specialized sub-agents.
    
    Enables context isolation and parallel execution of independent tasks
    through spawned sub-agents with specific capabilities.
    """
    
    name: str = "task"
    description: str = (
        "Launch a specialized sub-agent to handle complex, independent tasks. "
        "Use this when you need to isolate context, run parallel operations, "
        "or delegate to a specialized capability. The sub-agent will work "
        "independently and return complete results."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Detailed task description for the sub-agent to accomplish"
            },
            "subagent_type": {
                "type": "string",
                "description": "Type of sub-agent to use (e.g., 'general-purpose', 'research-agent', 'code-reviewer')"
            },
            "additional_context": {
                "type": "string",
                "description": "Optional additional context or constraints for the task"
            },
            "max_steps": {
                "type": "integer",
                "description": "Maximum execution steps for the sub-agent",
                "default": 5
            }
        },
        "required": ["description", "subagent_type"]
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._registered_subagents: Dict[str, SubAgentConfig] = {}
        self._default_tools: List[BaseTool] = []
        self._setup_default_subagents()

    def register_subagent(self, config: SubAgentConfig) -> None:
        """Register a custom sub-agent configuration."""
        self._registered_subagents[config.name] = config

    def set_default_tools(self, tools: List[BaseTool]) -> None:
        """Set default tools available to all sub-agents."""
        self._default_tools = tools

    async def execute(
        self,
        description: str,
        subagent_type: str,
        additional_context: str = "",
        max_steps: int = 5,
        **kwargs
    ) -> ToolResult:
        """
        Execute a task using a specialized sub-agent.
        
        Args:
            description: Task description for the sub-agent
            subagent_type: Type of sub-agent to use
            additional_context: Additional context or constraints
            max_steps: Maximum execution steps
            
        Returns:
            ToolResult with sub-agent execution results
        """
        try:
            # Get sub-agent configuration
            subagent_config = self._get_subagent_config(subagent_type, max_steps)
            if not subagent_config:
                return ToolResult(
                    error=f"Unknown sub-agent type: {subagent_type}. "
                          f"Available types: {list(self._registered_subagents.keys())}"
                )

            # Create and execute sub-agent
            result = await self._execute_subagent(
                subagent_config, description, additional_context
            )

            # Format result
            output = self._format_subagent_result(result)
            
            return ToolResult(
                output=output,
                system=f"Sub-agent '{result.agent_name}' completed task in {result.execution_steps} steps"
            )

        except Exception as e:
            return ToolResult(error=f"Sub-agent execution failed: {str(e)}")

    def _setup_default_subagents(self) -> None:
        """Setup built-in sub-agent configurations."""
        
        # General purpose sub-agent
        general_config = SubAgentConfig(
            name="general-purpose",
            description="General-purpose agent for complex multi-step tasks",
            prompt=(
                "You are a specialized sub-agent focused on completing a specific task. "
                "Work independently and provide complete, detailed results. "
                "Your response will be the final output, so ensure it fully addresses the request."
            ),
            max_steps=10
        )
        self.register_subagent(general_config)

        # Research specialist
        research_config = SubAgentConfig(
            name="research-agent", 
            description="Specialized agent for research and analysis tasks",
            prompt=(
                "You are a research specialist. Conduct thorough research and analysis. "
                "Provide comprehensive, well-structured findings with sources and evidence. "
                "Focus on accuracy, depth, and actionable insights."
            ),
            max_steps=8
        )
        self.register_subagent(research_config)

        # Code review specialist
        code_config = SubAgentConfig(
            name="code-reviewer",
            description="Specialized agent for code analysis and review",
            prompt=(
                "You are a code review expert. Analyze code for quality, security, "
                "performance, and best practices. Provide specific, actionable feedback "
                "with examples and recommendations for improvement."
            ),
            max_steps=6
        )
        self.register_subagent(code_config)

    def _get_subagent_config(self, subagent_type: str, max_steps: int) -> Optional[SubAgentConfig]:
        """Get configuration for the specified sub-agent type."""
        if subagent_type in self._registered_subagents:
            config = self._registered_subagents[subagent_type].copy()
            config.max_steps = max_steps
            return config
        return None

    async def _execute_subagent(
        self,
        config: SubAgentConfig,
        task_description: str,
        additional_context: str = ""
    ) -> SubAgentResult:
        """Execute a sub-agent with the given configuration and task."""
        
        # Import locally to avoid circular imports
        from myagent.agent.factory import create_toolcall_agent
        from myagent.llm import LLM
        
        # Prepare tools for sub-agent
        subagent_tools = self._default_tools + config.tools
        
        # Create LLM instance (LLM uses config_name, not keyword arguments)
        llm = LLM(config_name=config.name.lower())
        
        # Create sub-agent
        subagent = create_toolcall_agent(
            name=f"{config.name}_{uuid.uuid4().hex[:8]}",
            llm=llm,
            tools=subagent_tools
        )
        
        # Set description
        subagent.description = config.description
        
        # Set prompts
        subagent.system_prompt = config.prompt
        subagent.max_steps = config.max_steps
        
        # Prepare full task context
        full_task = task_description
        if additional_context:
            full_task += f"\n\nAdditional Context: {additional_context}"
        
        try:
            # Execute sub-agent
            result = await subagent.run(full_task)
            
            return SubAgentResult(
                agent_name=config.name,
                task_description=task_description,
                success=True,
                result=result,
                execution_steps=subagent.current_step,
                final_memory=[msg.to_dict() for msg in subagent.memory.messages[-5:]]  # Last 5 messages
            )
            
        except Exception as e:
            return SubAgentResult(
                agent_name=config.name,
                task_description=task_description,
                success=False,
                result="",
                error=str(e),
                execution_steps=subagent.current_step
            )

    def _format_subagent_result(self, result: SubAgentResult) -> str:
        """Format sub-agent execution result for display."""
        output = [
            f"🤖 **Sub-Agent: {result.agent_name}**",
            f"📋 **Task:** {result.task_description}",
            ""
        ]

        if result.success:
            output.extend([
                "✅ **Status:** Completed Successfully",
                f"📊 **Execution Steps:** {result.execution_steps}",
                "",
                "📝 **Result:**",
                result.result
            ])
        else:
            output.extend([
                "❌ **Status:** Failed",
                f"📊 **Execution Steps:** {result.execution_steps}",
                "",
                "🚨 **Error:**",
                result.error or "Unknown error occurred"
            ])

        return "\n".join(output)

    def get_available_subagents(self) -> List[str]:
        """Get list of available sub-agent types."""
        return list(self._registered_subagents.keys())

    def get_subagent_info(self, subagent_type: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific sub-agent type."""
        if subagent_type in self._registered_subagents:
            config = self._registered_subagents[subagent_type]
            return {
                "name": config.name,
                "description": config.description,
                "max_steps": config.max_steps,
                "available_tools": len(config.tools)
            }
        return None


# Convenience function to create a sub-agent tool with default configuration
def create_subagent_tool(default_tools: List[BaseTool] = None) -> SubAgentTool:
    """Create a sub-agent tool with default configuration."""
    tool = SubAgentTool()
    if default_tools:
        tool.set_default_tools(default_tools)
    return tool