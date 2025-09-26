"""
Decorators for automatic tracing of agent and tool operations.

This module provides decorators that can be applied to methods
to automatically create traces and runs.
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any
from typing import TypeVar

from .manager import get_trace_manager
from .models import RunType

F = TypeVar("F", bound=Callable[..., Any])


def trace_run(
    name: str | None = None,
    run_type: RunType = RunType.CUSTOM,
    include_inputs: bool = True,
    include_outputs: bool = True,
    capture_errors: bool = True,
):
    """
    Decorator to automatically trace function/method execution as a run.

    Args:
        name: Name for the run. If None, uses function name.
        run_type: Type of the run.
        include_inputs: Whether to capture function inputs.
        include_outputs: Whether to capture function outputs.
        capture_errors: Whether to capture and re-raise errors.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            trace_manager = get_trace_manager()
            run_name = name or func.__name__

            # Prepare inputs
            inputs = {}
            if include_inputs:
                # Get function signature
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Convert arguments to serializable format
                for param_name, value in bound_args.arguments.items():
                    try:
                        # Only include serializable values
                        if isinstance(
                            value, (str, int, float, bool, list, dict, type(None))
                        ):
                            inputs[param_name] = value
                        else:
                            inputs[param_name] = str(value)
                    except Exception:
                        inputs[param_name] = f"<{type(value).__name__}>"

            async with trace_manager.run(run_name, run_type, inputs) as run:
                try:
                    if inspect.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    # Capture outputs
                    if include_outputs and result is not None:
                        try:
                            if isinstance(result, (str, int, float, bool, list, dict)):
                                run.outputs["result"] = result
                            else:
                                run.outputs["result"] = str(result)
                        except Exception:
                            run.outputs["result"] = f"<{type(result).__name__}>"

                    return result

                except Exception as e:
                    if capture_errors:
                        run.fail(str(e), type(e).__name__)
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import asyncio

            # Check if we're already in an async context
            try:
                asyncio.get_running_loop()
                # If we get here, we're in an async context, so we need to handle this differently
                return asyncio.create_task(async_wrapper(*args, **kwargs))
            except RuntimeError:
                # Not in an async context, run the async wrapper directly
                return asyncio.run(async_wrapper(*args, **kwargs))

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def trace_agent_step(name: str | None = None, include_memory: bool = False):
    """
    Decorator specifically for tracing agent step methods.

    Args:
        name: Name for the run. If None, uses "agent_step".
        include_memory: Whether to include memory state in inputs.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            trace_manager = get_trace_manager()
            run_name = name or "agent_step"

            # Prepare inputs for agent step
            inputs = {}
            if len(args) > 0 and hasattr(args[0], "__class__"):
                agent = args[0]
                inputs["agent_name"] = getattr(agent, "name", "unknown")
                inputs["current_step"] = getattr(agent, "current_step", 0)
                inputs["max_steps"] = getattr(agent, "max_steps", 0)
                inputs["state"] = str(getattr(agent, "state", "unknown"))

                if include_memory and hasattr(agent, "memory"):
                    inputs["memory_size"] = len(getattr(agent.memory, "messages", []))

            async with trace_manager.run(run_name, RunType.AGENT, inputs) as run:
                try:
                    result = await func(*args, **kwargs)

                    # Capture step result
                    if result:
                        run.outputs["step_result"] = str(result)

                    return result

                except Exception as e:
                    run.fail(str(e), type(e).__name__)
                    raise

        return wrapper

    return decorator


def trace_tool_call(name: str | None = None, capture_tool_metadata: bool = True):
    """
    Decorator specifically for tracing tool executions.

    Args:
        name: Name for the run. If None, uses tool name.
        capture_tool_metadata: Whether to capture tool metadata.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            trace_manager = get_trace_manager()

            # Try to get tool name from self if it's a method
            tool_name = name
            if not tool_name and len(args) > 0 and hasattr(args[0], "name"):
                tool_name = args[0].name
            if not tool_name:
                tool_name = func.__name__

            # Prepare inputs
            inputs = dict(kwargs)

            # Add tool metadata if available
            metadata = {}
            if capture_tool_metadata and len(args) > 0:
                tool = args[0]
                if hasattr(tool, "description"):
                    metadata["tool_description"] = tool.description
                if hasattr(tool, "parameters"):
                    metadata["tool_parameters"] = tool.parameters

            async with trace_manager.run(
                tool_name, RunType.TOOL, inputs, **metadata
            ) as run:
                try:
                    if inspect.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    # Capture tool result
                    if result is not None:
                        if hasattr(result, "output"):
                            # Handle ToolResult objects
                            run.outputs["output"] = str(result.output)
                            if hasattr(result, "error") and result.error:
                                run.outputs["error"] = result.error
                        else:
                            run.outputs["result"] = str(result)

                    return result

                except Exception as e:
                    run.fail(str(e), type(e).__name__)
                    raise

        return wrapper

    return decorator


def trace_llm_call(
    model_name: str | None = None,
    capture_tokens: bool = True,
    capture_cost: bool = True,
):
    """
    Decorator specifically for tracing LLM calls.

    Args:
        model_name: Name of the model. If None, tries to extract from context.
        capture_tokens: Whether to capture token usage.
        capture_cost: Whether to capture cost information.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            trace_manager = get_trace_manager()
            run_name = f"llm_call_{model_name or 'unknown'}"

            # Prepare inputs
            inputs = {}
            if "messages" in kwargs:
                inputs["message_count"] = len(kwargs["messages"])
            if "model" in kwargs:
                inputs["model"] = kwargs["model"]
            if "temperature" in kwargs:
                inputs["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                inputs["max_tokens"] = kwargs["max_tokens"]

            async with trace_manager.run(run_name, RunType.LLM, inputs) as run:
                try:
                    result = await func(*args, **kwargs)

                    # Capture LLM response details
                    if result and hasattr(result, "choices"):
                        # Standard OpenAI-style response
                        if result.choices:
                            choice = result.choices[0]
                            if hasattr(choice, "message"):
                                run.outputs["response"] = choice.message.content

                        # Capture token usage
                        if capture_tokens and hasattr(result, "usage"):
                            usage = result.usage
                            token_usage = {}
                            if hasattr(usage, "prompt_tokens"):
                                token_usage["prompt_tokens"] = usage.prompt_tokens
                            if hasattr(usage, "completion_tokens"):
                                token_usage["completion_tokens"] = (
                                    usage.completion_tokens
                                )
                            if hasattr(usage, "total_tokens"):
                                token_usage["total_tokens"] = usage.total_tokens

                            if token_usage:
                                run.token_usage = token_usage

                    return result

                except Exception as e:
                    run.fail(str(e), type(e).__name__)
                    raise

        return wrapper

    return decorator
