"""WebSocket session management for MyAgent."""

import asyncio
from datetime import datetime
from typing import Any

from websockets.server import WebSocketServerProtocol

from myagent.agent.base import BaseAgent
from myagent.logger import logger
from myagent.schema import AgentState
from .events import AgentEvents
from .events import SystemEvents
from .events import create_event
from .utils import is_websocket_closed
from .utils import send_websocket_message


class AgentSession:
    """Manage WebSocket session for a single Agent instance"""

    def __init__(
        self,
        session_id: str,
        connection_id: str,
        agent: BaseAgent,
        websocket: WebSocketServerProtocol,
    ):
        self.session_id = session_id
        self.connection_id = connection_id
        self.agent = agent
        self.websocket = websocket
        self.state = "idle"
        self.created_at = datetime.now()
        self.current_task: asyncio.Task | None = None
        self.step_counter = 0
        max_attempts = getattr(agent, "max_retry_attempts", 0)
        delay_seconds = getattr(agent, "retry_delay_seconds", 0.0)

        try:
            self.max_retry_attempts = max(0, int(max_attempts))
        except (TypeError, ValueError):
            logger.debug(
                "Invalid max_retry_attempts on agent %s: %r. Falling back to 0.",
                getattr(agent, "name", "unknown"),
                max_attempts,
            )
            self.max_retry_attempts = 0

        try:
            self.retry_delay_seconds = max(0.0, float(delay_seconds))
        except (TypeError, ValueError):
            logger.debug(
                "Invalid retry_delay_seconds on agent %s: %r. Falling back to 0.0.",
                getattr(agent, "name", "unknown"),
                delay_seconds,
            )
            self.retry_delay_seconds = 0.0

        # Set up agent callbacks to monitor execution status
        self._setup_agent_callbacks()

    def _setup_agent_callbacks(self):
        """Set up Agent execution callbacks"""
        original_step = getattr(self.agent, "step", None)

        if original_step:

            async def wrapped_step(*args, **kwargs):
                # Set current step counter for agent to use
                self.agent._current_step = self.step_counter

                try:
                    result = await original_step(*args, **kwargs)
                    self.step_counter += 1
                    return result
                except Exception as e:
                    # Log error but don't send event here to avoid async issues in sync context
                    logger.error(
                        f"Agent step execution error in session {self.session_id}: {e!s}"
                    )
                    raise

            self.agent.step = wrapped_step

    async def execute_streaming(self, user_input: str) -> None:
        """Execute Agent in streaming mode and push status in real-time"""
        if self.state == "running":
            await self._send_event(
                create_event(
                    AgentEvents.ERROR,
                    session_id=self.session_id,
                    content="Agent is currently running, please try again later",
                )
            )
            return

        self.state = "running"
        self.step_counter = 0

        try:
            # Create execution task (Agent will send its own thinking events with actual content)
            self.current_task = asyncio.create_task(
                self._run_agent_with_streaming(user_input)
            )

            await self.current_task

        except asyncio.CancelledError:
            # Don't send another interrupted event here, as it's already sent in cancel() method
            logger.debug(f"Task cancelled for session {self.session_id}")
        except Exception as e:
            logger.error(f"Session {self.session_id} execution error: {e}")
            await self._send_event(
                create_event(
                    AgentEvents.ERROR,
                    session_id=self.session_id,
                    content=f"Execution error: {e!s}",
                )
            )
        finally:
            self.state = "idle"
            self.current_task = None

    async def execute_solve_tasks(
        self,
        tasks: list[dict] | dict | list | Any,
        *,
        question: str | None = None,
        plan_summary: str | None = None,
    ) -> None:
        """Execute solver-only flow with client-provided tasks and stream updates."""
        if self.state == "running":
            await self._send_event(
                create_event(
                    AgentEvents.ERROR,
                    session_id=self.session_id,
                    content="Agent is currently running, please try again later",
                )
            )
            return

        # Must have an agent supporting solve_tasks
        if not hasattr(self.agent, "solve_tasks"):
            await self._send_event(
                create_event(
                    AgentEvents.ERROR,
                    session_id=self.session_id,
                    content="Agent does not support direct task solving",
                )
            )
            return

        self.state = "running"
        self.step_counter = 0

        try:
            self.current_task = asyncio.create_task(
                self._run_agent_solve_tasks(tasks, question=question, plan_summary=plan_summary)
            )
            await self.current_task
        except asyncio.CancelledError:
            logger.debug(f"Task cancelled for session {self.session_id}")
        except Exception as e:
            logger.error(f"Session {self.session_id} solve_tasks execution error: {e}")
            await self._send_event(
                create_event(
                    AgentEvents.ERROR,
                    session_id=self.session_id,
                    content=f"Execution error: {e!s}",
                )
            )
        finally:
            self.state = "idle"
            self.current_task = None

    async def _run_agent_with_streaming(self, user_input: str) -> None:
        """Run Agent and stream status updates, retrying on failure when configured."""
        total_attempts = self.max_retry_attempts + 1
        last_error: Exception | None = None

        for attempt in range(1, total_attempts + 1):
            try:
                await self._execute_agent_attempt(user_input, attempt, total_attempts)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - runtime safeguard
                last_error = exc
                if attempt == total_attempts:
                    break
                await self._handle_retry(attempt, total_attempts, exc)

        if last_error:
            raise last_error

    async def _run_agent_solve_tasks(
        self,
        tasks: list[dict] | dict | list | Any,
        *,
        question: str | None = None,
        plan_summary: str | None = None,
    ) -> None:
        """Run agent.solve_tasks with retries and streaming."""
        total_attempts = self.max_retry_attempts + 1
        last_error: Exception | None = None

        for attempt in range(1, total_attempts + 1):
            try:
                await self._execute_agent_solve_tasks_attempt(tasks, attempt, total_attempts, question=question, plan_summary=plan_summary)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - runtime safeguard
                last_error = exc
                if attempt == total_attempts:
                    break
                await self._handle_retry(attempt, total_attempts, exc)

        if last_error:
            raise last_error

    async def _execute_agent_attempt(
        self, user_input: str, attempt: int, total_attempts: int
    ) -> None:
        """Execute a single agent attempt and stream updates."""
        try:
            if self.agent.state in (AgentState.FINISHED, AgentState.ERROR):
                logger.info(
                    "Resetting agent state from %s to IDLE for session %s before attempt %s/%s",
                    self.agent.state,
                    self.session_id,
                    attempt,
                    total_attempts,
                )
                self.agent.state = AgentState.IDLE
                self.agent.current_step = 0

                memory = getattr(self.agent, "memory", None)
                if memory:
                    messages_before = len(getattr(memory, "messages", []))
                    try:
                        memory.clean_incomplete_tool_calls()
                    except Exception as clean_exc:  # pragma: no cover - best effort
                        logger.debug(
                            "Failed to clean incomplete tool calls for session %s: %s",
                            self.session_id,
                            clean_exc,
                        )
                    else:
                        messages_after = len(getattr(memory, "messages", []))
                        logger.info(
                            "Cleaned incomplete tool_calls from agent memory for session %s: %s -> %s messages",
                            self.session_id,
                            messages_before,
                            messages_after,
                        )

            # Monitor Agent tool calls only once per tool collection
            self._wrap_tool_calls()

            # Ensure final response is fresh for this attempt
            if hasattr(self.agent, "final_response"):
                self.agent.final_response = None

            # Set WebSocket session in context and agent for streaming support
            try:
                from .context import set_ws_session_context

                set_ws_session_context(self)
                self.agent.ws_session = self
                logger.info(
                    "Set WebSocket session for agent: session_id=%s (attempt %s/%s)",
                    self.session_id,
                    attempt,
                    total_attempts,
                )
            except Exception as e:  # pragma: no cover - runtime safeguard
                logger.error(f"Could not set WebSocket session: {e}")

            # 执行 Agent
            if hasattr(self.agent, "arun"):
                result = await self.agent.arun(user_input)
            elif hasattr(self.agent, "run"):
                run_method = self.agent.run(user_input)
                if asyncio.iscoroutine(run_method):
                    result = await run_method
                else:
                    result = run_method
            else:
                raise AttributeError("Agent has no run or arun method")

            final_content = (
                getattr(self.agent, "final_response", None) or str(result)
                if result
                else "Execution completed"
            )
            await self._send_event(
                create_event(
                    AgentEvents.FINAL_ANSWER,
                    session_id=self.session_id,
                    content=final_content,
                )
            )

        except Exception as e:
            logger.error(
                "Agent execution error for session %s on attempt %s/%s: %s",
                self.session_id,
                attempt,
                total_attempts,
                e,
            )
            raise
        finally:
            # Clean up WebSocket session from context and agent
            try:
                from .context import clear_ws_session_context

                clear_ws_session_context()
                self.agent.ws_session = None
                logger.debug("Cleaned up WebSocket session")
            except Exception as e:  # pragma: no cover - best effort
                logger.debug(f"Could not clean up WebSocket session: {e}")

    async def _execute_agent_solve_tasks_attempt(
        self,
        tasks: list[dict] | dict | list | Any,
        attempt: int,
        total_attempts: int,
        *,
        question: str | None = None,
        plan_summary: str | None = None,
    ) -> None:
        """Execute a single attempt of solve_tasks and stream final answer."""
        try:
            if self.agent.state in (AgentState.FINISHED, AgentState.ERROR):
                logger.info(
                    "Resetting agent state from %s to IDLE for session %s before attempt %s/%s",
                    self.agent.state,
                    self.session_id,
                    attempt,
                    total_attempts,
                )
                self.agent.state = AgentState.IDLE
                self.agent.current_step = 0

                memory = getattr(self.agent, "memory", None)
                if memory:
                    messages_before = len(getattr(memory, "messages", []))
                    try:
                        memory.clean_incomplete_tool_calls()
                    except Exception as clean_exc:  # pragma: no cover - best effort
                        logger.debug(
                            "Failed to clean incomplete tool calls for session %s: %s",
                            self.session_id,
                            clean_exc,
                        )
                    else:
                        messages_after = len(getattr(memory, "messages", []))
                        logger.info(
                            "Cleaned incomplete tool_calls from agent memory for session %s: %s -> %s messages",
                            self.session_id,
                            messages_before,
                            messages_after,
                        )

            # Monitor Agent tool calls only once per tool collection
            self._wrap_tool_calls()

            # Ensure final response is fresh for this attempt
            if hasattr(self.agent, "final_response"):
                self.agent.final_response = None

            # Set WebSocket session in context and agent for streaming support
            try:
                from .context import set_ws_session_context

                set_ws_session_context(self)
                self.agent.ws_session = self
                logger.info(
                    "Set WebSocket session for agent: session_id=%s (attempt %s/%s)",
                    self.session_id,
                    attempt,
                    total_attempts,
                )
            except Exception as e:  # pragma: no cover - runtime safeguard
                logger.error(f"Could not set WebSocket session: {e}")

            # Execute solve_tasks on agent (direct-task mode)
            if hasattr(self.agent, "solve_tasks"):
                result = await self.agent.solve_tasks(tasks, question=question, plan_summary=plan_summary)  # type: ignore[attr-defined]
            else:
                raise AttributeError("Agent does not implement solve_tasks")
            # Do not send agent.final_answer in direct-task mode; solver.* events suffice

        except Exception as e:
            logger.error(
                "Agent solve_tasks error for session %s on attempt %s/%s: %s",
                self.session_id,
                attempt,
                total_attempts,
                e,
            )
            raise
        finally:
            # Clean up WebSocket session from context and agent
            try:
                from .context import clear_ws_session_context

                clear_ws_session_context()
                self.agent.ws_session = None
                logger.debug("Cleaned up WebSocket session")
            except Exception as e:  # pragma: no cover - best effort
                logger.debug(f"Could not clean up WebSocket session: {e}")

    async def _handle_retry(
        self, failed_attempt: int, total_attempts: int, error: Exception
    ) -> None:
        """Handle retry workflow between failed attempts."""
        next_attempt = failed_attempt + 1
        logger.warning(
            "Agent execution failed for session %s (attempt %s/%s). Retrying attempt %s/%s after %.2fs. Error: %s",
            self.session_id,
            failed_attempt,
            total_attempts,
            next_attempt,
            total_attempts,
            self.retry_delay_seconds,
            error,
        )

        await self._send_retry_notice(failed_attempt, total_attempts, error)
        await self._reset_agent_between_attempts()

        if self.retry_delay_seconds > 0:
            await asyncio.sleep(self.retry_delay_seconds)

    async def _send_retry_notice(
        self, failed_attempt: int, total_attempts: int, error: Exception
    ) -> None:
        """Notify clients that a retry will be attempted."""
        error_text = str(error)
        if len(error_text) > 500:
            error_text = f"{error_text[:497]}..."

        metadata = {
            "attempt": failed_attempt,
            "total_attempts": total_attempts,
            "next_attempt": failed_attempt + 1,
            "retry_delay_seconds": self.retry_delay_seconds,
            "error_type": error.__class__.__name__,
            "error": error_text,
        }

        content = (
            f"Attempt {failed_attempt}/{total_attempts} failed. "
            f"Retrying attempt {failed_attempt + 1}/{total_attempts}."
        )

        await self._send_event(
            create_event(
                SystemEvents.NOTICE,
                session_id=self.session_id,
                content=content,
                metadata=metadata,
            )
        )

    async def _reset_agent_between_attempts(self) -> None:
        """Reset agent state between retry attempts."""
        reset_handler = getattr(self.agent, "reset_for_retry", None)
        if reset_handler:
            try:
                outcome = reset_handler()
                if asyncio.iscoroutine(outcome):
                    await outcome
                return
            except Exception as exc:  # pragma: no cover - fallback safeguard
                logger.debug(
                    "Custom reset_for_retry failed for session %s: %s",
                    self.session_id,
                    exc,
                )

        try:
            self.agent.state = AgentState.IDLE
        except Exception as exc:  # pragma: no cover - fallback safeguard
            logger.debug(
                "Failed to reset agent state for retry in session %s: %s",
                self.session_id,
                exc,
            )

        try:
            self.agent.current_step = 0
        except Exception as exc:  # pragma: no cover - fallback safeguard
            logger.debug(
                "Failed to reset agent current_step for retry in session %s: %s",
                self.session_id,
                exc,
            )

        if hasattr(self.agent, "final_response"):
            self.agent.final_response = None

        memory = getattr(self.agent, "memory", None)
        if memory:
            try:
                if hasattr(memory, "clear_for_retry"):
                    outcome = memory.clear_for_retry()
                    if asyncio.iscoroutine(outcome):
                        await outcome
                elif hasattr(memory, "clear"):
                    memory.clear()
            except Exception as exc:  # pragma: no cover - fallback safeguard
                logger.debug(
                    "Failed to reset agent memory for retry in session %s: %s",
                    self.session_id,
                    exc,
                )

            if hasattr(memory, "clean_incomplete_tool_calls"):
                try:
                    memory.clean_incomplete_tool_calls()
                except Exception as exc:  # pragma: no cover - fallback safeguard
                    logger.debug(
                        "Failed to clean incomplete tool calls during retry reset for session %s: %s",
                        self.session_id,
                        exc,
                    )

    def _wrap_tool_calls(self):
        """Wrap tool calls to provide real-time feedback"""
        if not hasattr(self.agent, "available_tools"):
            logger.debug("Agent has no available_tools attribute")
            return

        tools = self.agent.available_tools

        # Setup confirmation handlers for tools that require user confirmation
        self._setup_confirmation_handlers(tools)

        # Check if it's a ToolCollection and wrap its execute method
        if hasattr(tools, "execute") and hasattr(tools, "tool_map"):
            if getattr(tools, "_ws_wrapped", False):
                logger.debug(
                    "ToolCollection already wrapped for session %s. Skipping re-wrap.",
                    self.session_id,
                )
                return

            original_execute = tools.execute
            logger.info(
                f"Wrapping ToolCollection.execute with {len(tools.tool_map)} tools: {list(tools.tool_map.keys())}"
            )

            async def wrapped_collection_execute(*, name: str, tool_input: dict | None = None):
                step_id = f"step_{self.step_counter}_{name}"
                self.step_counter += 1

                # Send tool call start event
                await self._send_event(
                    create_event(
                        AgentEvents.TOOL_CALL,
                        session_id=self.session_id,
                        step_id=step_id,
                        content=f"Calling tool: {name}",
                        metadata={
                            "tool": name,
                            "args": tool_input or {},
                            "status": "running",
                        },
                    )
                )

                try:
                    result = await original_execute(name=name, tool_input=tool_input)

                    # Send tool result event
                    # Determine if the tool execution was successful
                    is_success = True
                    if (
                        hasattr(result, "error") and result.error is not None
                    ) or result.__class__.__name__ == "ToolFailure":
                        is_success = False

                    # Prepare metadata with tool execution details
                    tool_metadata = {
                        "tool": name,
                        "status": "success" if is_success else "failed",
                        "error": (
                            str(result.error)
                            if hasattr(result, "error") and result.error
                            else None
                        ),
                    }
                    
                    # Include data field if present (for ToolResultExpanded)
                    if hasattr(result, "data") and result.data is not None:
                        tool_metadata["data"] = result.data
                    
                    await self._send_event(
                        create_event(
                            AgentEvents.TOOL_RESULT,
                            session_id=self.session_id,
                            step_id=step_id,
                            content=(
                                str(result.output)
                                if hasattr(result, "output")
                                else str(result)
                            ),
                            metadata=tool_metadata,
                        )
                    )

                    return result

                except Exception as e:
                    # Send tool error event
                    await self._send_event(
                        create_event(
                            AgentEvents.TOOL_RESULT,
                            session_id=self.session_id,
                            step_id=step_id,
                            content=f"Tool execution failed: {e!s}",
                            metadata={
                                "tool": name,
                                "status": "failed",
                                "error": str(e),
                            },
                        )
                    )
                    raise

            # Replace the ToolCollection's execute method
            tools.execute = wrapped_collection_execute
            setattr(tools, "_ws_wrapped", True)
            logger.info("Successfully wrapped ToolCollection.execute method")
        else:
            logger.warning(f"Unknown tools structure: {type(tools)}, cannot wrap")

    def _setup_confirmation_handlers(self, tools):
        """Setup confirmation handlers for tools that require user confirmation."""
        if hasattr(tools, "tool_map"):
            # ToolCollection
            for tool_name, tool in tools.tool_map.items():
                if hasattr(tool, "user_confirm") and tool.user_confirm:
                    tool.set_confirmation_handler(self._handle_tool_confirmation)
                    logger.info(f"Setup confirmation handler for tool: {tool_name}")
        elif hasattr(tools, "__iter__"):
            # List of tools
            for tool in tools:
                if hasattr(tool, "user_confirm") and tool.user_confirm:
                    tool.set_confirmation_handler(self._handle_tool_confirmation)
                    logger.info(f"Setup confirmation handler for tool: {tool.name}")
        else:
            logger.debug(
                f"Tools structure {type(tools)} not recognized for confirmation setup"
            )

    async def _handle_tool_confirmation(self, tool, kwargs):
        """Handle user confirmation for a tool execution."""
        # Use a unique UUID-based step_id to avoid conflicts with regular tool step_ids
        import uuid

        step_id = f"confirm_{uuid.uuid4().hex[:8]}_{tool.name}"

        logger.info(
            f"Requesting user confirmation for tool '{tool.name}' with step_id: {step_id}"
        )

        # Send user confirmation request
        await self._send_event(
            create_event(
                AgentEvents.USER_CONFIRM,
                session_id=self.session_id,
                step_id=step_id,
                content=f"Confirm tool execution: {tool.name}",
                metadata={
                    "tool_name": tool.name,
                    "tool_description": tool.description,
                    "tool_args": kwargs,
                    "requires_confirmation": True,
                },
            )
        )

        # Wait for user response
        try:
            confirmation_result = await self._wait_for_user_response(step_id)
            confirmed = confirmation_result.get("confirmed", False)
            logger.info(
                f"User {'confirmed' if confirmed else 'denied'} tool execution for '{tool.name}'"
            )
            return confirmed
        except Exception as e:
            logger.error(f"Error waiting for user response for step_id {step_id}: {e}")
            return False

    async def _wait_for_user_response(self, step_id: str, timeout: int = 300):
        """Wait for user response with timeout."""
        if not hasattr(self, "_pending_confirmations"):
            self._pending_confirmations = {}

        future = asyncio.Future()
        self._pending_confirmations[step_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(
                f"User confirmation timeout for step {step_id} after {timeout}s"
            )
            return {"confirmed": False, "reason": "timeout"}
        except Exception as e:
            logger.error(
                f"Exception while waiting for user response for step_id {step_id}: {e}"
            )
            return {"confirmed": False, "reason": f"error: {e!s}"}
        finally:
            self._pending_confirmations.pop(step_id, None)

    async def handle_user_response(self, step_id: str, response_data: dict):
        """Handle user response for confirmations."""
        if not hasattr(self, "_pending_confirmations"):
            self._pending_confirmations = {}

        future = self._pending_confirmations.get(step_id)
        if future:
            if not future.done():
                future.set_result(response_data)
                logger.debug(f"User response processed for step {step_id}")
            else:
                logger.warning(f"Future for step_id {step_id} is already done")
        else:
            logger.warning(f"No pending confirmation found for step {step_id}")
            logger.warning(
                f"Available pending confirmations: {list(self._pending_confirmations.keys())}"
            )

    async def cancel(self) -> None:
        """Cancel current execution"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

        self.state = "idle"
        
        # Reset agent state to allow reuse after cancellation
        from myagent.schema import AgentState
        if hasattr(self.agent, 'state'):
            logger.info(
                f"Resetting agent state from {self.agent.state} to IDLE after cancellation for session {self.session_id}"
            )
            self.agent.state = AgentState.IDLE
            self.agent.current_step = 0
            
            # Clean incomplete tool_calls messages
            if hasattr(self.agent, 'memory'):
                messages_before = len(self.agent.memory.messages)
                self.agent.memory.clean_incomplete_tool_calls()
                messages_after = len(self.agent.memory.messages)
                logger.info(
                    f"Cleaned incomplete tool_calls after cancellation for session {self.session_id}: {messages_before} -> {messages_after} messages"
                )

        await self._send_event(
            create_event(
                AgentEvents.INTERRUPTED,
                session_id=self.session_id,
                content="Execution cancelled",
            )
        )

    async def _send_event(self, event: dict[str, Any]) -> None:
        """Send event to client"""
        if is_websocket_closed(self.websocket):
            logger.debug(
                "WebSocket already closed for session %s, skipping event %s",
                self.session_id,
                event.get("event", "unknown"),
            )
            return

        success = await send_websocket_message(self.websocket, event)
        if not success:
            logger.warning(
                f"Failed to send event to session {self.session_id}: {event.get('event', 'unknown')}"
            )

    def is_active(self) -> bool:
        """Check if session is still active"""
        # If there are pending confirmation requests, consider session still active
        if hasattr(self, "_pending_confirmations") and self._pending_confirmations:
            return True

        return not is_websocket_closed(self.websocket) and self.state != "closed"

    async def close(self) -> None:
        """Close session"""
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

        self.state = "closed"

        await self._send_event(
            create_event(
                AgentEvents.SESSION_END,
                session_id=self.session_id,
                content="Session closed",
            )
        )
