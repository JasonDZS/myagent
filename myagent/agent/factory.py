"""Factory helpers for constructing agents."""
from typing import Optional, Sequence, Union, cast

from .toolcall import ToolCallAgent
from ..llm import LLM
from ..schema import TOOL_CHOICE_TYPE, ToolChoice
from ..tool import BaseTool, Terminate, ToolCollection


def _ensure_tool_collection(
    tools: Optional[Union[Sequence[BaseTool], ToolCollection]]
) -> ToolCollection:
    if isinstance(tools, ToolCollection):
        collection = tools
    else:
        collection = ToolCollection(*(tools or ()))
    terminate_tool = Terminate()
    if not collection.get_tool(terminate_tool.name):
        collection.add_tool(terminate_tool)
    return collection


def create_react_agent(
    *,
    name: str = "react-agent",
    llm: Optional[LLM] = None,
    tools: Optional[Union[Sequence[BaseTool], ToolCollection]] = None,
    system_prompt: Optional[str] = None,
    next_step_prompt: Optional[str] = None,
    tool_choice: Optional[Union[ToolChoice, TOOL_CHOICE_TYPE]] = ToolChoice.AUTO,
    max_steps: Optional[int] = None,
    max_observe: Optional[int] = None,
    **extra_fields,
) -> ToolCallAgent:
    """Create a tool-aware ReAct agent instance.

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

    Notes:
        Always ensures the ``terminate`` tool is available so the agent can finish runs.
    """

    tool_collection = _ensure_tool_collection(tools)

    if tool_choice is None:
        tool_choice_value: TOOL_CHOICE_TYPE = cast(
            TOOL_CHOICE_TYPE, ToolChoice.AUTO.value
        )
    elif isinstance(tool_choice, ToolChoice):
        tool_choice_value = cast(TOOL_CHOICE_TYPE, tool_choice.value)
    else:
        try:
            tool_choice_value = cast(
                TOOL_CHOICE_TYPE, ToolChoice(tool_choice).value
            )
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
    if not agent_kwargs.get('enable_tracing', True):
        for tool_name, tool_instance in tool_collection.tool_map.items():
            if hasattr(tool_instance, 'enable_tracing'):
                tool_instance.enable_tracing = False

    return ToolCallAgent(**agent_kwargs)
