"""Factory helpers for constructing agents."""

from collections.abc import Sequence
from typing import cast, List

from ..llm import LLM
from ..schema import TOOL_CHOICE_TYPE, ToolChoice
from ..tool import BaseTool, Terminate, ToolCollection
from .toolcall import ToolCallAgent
from .base import BaseAgent


def _ensure_tool_collection(
    tools: Sequence[BaseTool] | ToolCollection | None,
) -> ToolCollection:
    if isinstance(tools, ToolCollection):
        collection = tools
    else:
        collection = ToolCollection(*(tools or ()))
    terminate_tool = Terminate()
    if not collection.get_tool(terminate_tool.name):
        collection.add_tool(terminate_tool)
    return collection


def create_toolcall_agent(
    *,
    name: str = "toolcall-agent",
    llm: LLM | None = None,
    tools: Sequence[BaseTool] | ToolCollection | None = None,
    system_prompt: str | None = None,
    next_step_prompt: str | None = None,
    tool_choice: ToolChoice | TOOL_CHOICE_TYPE | None = ToolChoice.AUTO,
    max_steps: int | None = None,
    max_observe: int | None = None,
    **extra_fields,
) -> ToolCallAgent:
    """Create a tool-aware agent that implements the ReAct pattern.

    This agent uses the ToolCallAgent implementation which combines reasoning (thinking)
    and acting (tool execution) in a single workflow.

    Args:
        name: Agent identifier.
        llm: Concrete ``LLM`` instance to use.
        tools: Sequence of ``BaseTool`` instances or a pre-built ``ToolCollection``.
        system_prompt: Optional system message injected on every turn.
        next_step_prompt: Optional hint appended before each thinking cycle.
        tool_choice: Strategy for tool selection.
        max_steps: Override default step budget.
        max_observe: Optional cap on observation length.
        extra_fields: Any additional ``ToolCallAgent`` fields to set.

    Returns:
        A ToolCallAgent instance that implements the ReAct pattern.

    Notes:
        Always ensures the ``terminate`` tool is available so the agent can finish runs.
    """

    tool_collection = _ensure_tool_collection(tools)

    if tool_choice is None:
        tool_choice_value: TOOL_CHOICE_TYPE = cast(
            "TOOL_CHOICE_TYPE", ToolChoice.AUTO.value
        )
    elif isinstance(tool_choice, ToolChoice):
        tool_choice_value = cast("TOOL_CHOICE_TYPE", tool_choice.value)
    else:
        try:
            tool_choice_value = cast("TOOL_CHOICE_TYPE", ToolChoice(tool_choice).value)
        except ValueError as exc:
            raise ValueError(f"Unsupported tool choice: {tool_choice}") from exc

    agent_kwargs = {
        "name": name,
        "llm": llm if llm is not None else LLM(config_name=name.lower()),
        "available_tools": tool_collection,
        "tool_choices": tool_choice_value,
    }

    if system_prompt is not None:
        agent_kwargs["system_prompt"] = system_prompt
    if next_step_prompt is not None:
        agent_kwargs["next_step_prompt"] = next_step_prompt
    if max_steps is not None:
        agent_kwargs["max_steps"] = max_steps
    if max_observe is not None:
        agent_kwargs["max_observe"] = max_observe

    agent_kwargs.update(extra_fields)

    # If enable_tracing is False, disable tracing for all tools in the collection
    if not agent_kwargs.get("enable_tracing", True):
        for tool_instance in tool_collection.tool_map.values():
            if hasattr(tool_instance, "enable_tracing"):
                tool_instance.enable_tracing = False

    return ToolCallAgent(**agent_kwargs)


def create_react_agent(
    *,
    name: str = "react-agent",
    llm: LLM | None = None,
    tools: Sequence[BaseTool] | ToolCollection | None = None,
    system_prompt: str | None = None,
    next_step_prompt: str | None = None,
    tool_choice: ToolChoice | TOOL_CHOICE_TYPE | None = ToolChoice.AUTO,
    max_steps: int | None = None,
    max_observe: int | None = None,
    **extra_fields,
) -> ToolCallAgent:
    """Create a tool-aware ReAct agent instance.

    This function is an alias for create_toolcall_agent() to maintain backward compatibility.
    The returned agent implements the ReAct (Reason + Act) pattern using tool calls.

    Args:
        name: Agent identifier.
        llm: Concrete ``LLM`` instance to use.
        tools: Sequence of ``BaseTool`` instances or a pre-built ``ToolCollection``.
        system_prompt: Optional system message injected on every turn.
        next_step_prompt: Optional hint appended before each thinking cycle.
        tool_choice: Strategy for tool selection.
        max_steps: Override default step budget.
        max_observe: Optional cap on observation length.
        extra_fields: Any additional ``ToolCallAgent`` fields to set.

    Returns:
        A ToolCallAgent instance that implements the ReAct pattern.

    Notes:
        Always ensures the ``terminate`` tool is available so the agent can finish runs.

    Deprecated:
        Use create_toolcall_agent() instead for better clarity.
    """
    return create_toolcall_agent(
        name=name,
        llm=llm,
        tools=tools,
        system_prompt=system_prompt,
        next_step_prompt=next_step_prompt,
        tool_choice=tool_choice,
        max_steps=max_steps,
        max_observe=max_observe,
        **extra_fields,
    )


def create_deep_agent(
    tools: List[BaseTool] = None,
    llm_config: dict = None,
    name: str = "deep_agent",
    description: str = "A Deep Agent with advanced capabilities"
) -> BaseAgent:
    """
    Create a new Deep Agent with all capabilities enabled.

    This function creates an agent with Deep Agent capabilities including:
    - Task planning and management
    - Virtual file system
    - Sub-agent delegation
    - Enhanced prompting

    Args:
        tools: Additional tools beyond Deep Agent built-ins
        llm_config: LLM configuration (currently unused, uses config_name)
        name: Agent name
        description: Agent description

    Returns:
        Configured Deep Agent with all capabilities
    """
    # Import Deep Agent middleware
    from myagent.middleware.deep_agent import DeepAgentMiddleware
    from myagent.middleware import MiddlewareContext

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
