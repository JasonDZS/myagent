import asyncio
import json
import os
import re
from typing import Any

from pydantic import Field

from myagent.exceptions import TokenLimitExceeded
from myagent.logger import logger
from myagent.prompt.toolcall import NEXT_STEP_PROMPT
from myagent.prompt.toolcall import SUMMARY_PROMPT
from myagent.prompt.toolcall import SYSTEM_PROMPT
from myagent.schema import TOOL_CHOICE_TYPE
from myagent.schema import AgentState
from myagent.schema import Message
from myagent.schema import ToolCall
from myagent.schema import ToolChoice
from myagent.tool import Terminate
from myagent.tool import ToolCollection
from .react import ReActAgent

try:
    from myagent.trace import get_ws_session_context

    TRACE_AVAILABLE = True
except ImportError:
    TRACE_AVAILABLE = False

TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Agent that implements the ReAct pattern (Reasoning + Acting) using tool calls.

    This agent combines thinking (reasoning) and tool execution (acting) in a unified workflow.
    It inherits from ReActAgent but provides a complete implementation of the ReAct pattern
    through the think() and act() methods.

    The agent operates in cycles:
    1. Think: Analyze the current situation and decide which tools to use
    2. Act: Execute the selected tools and process their results
    3. Repeat until the task is completed or max steps are reached
    """

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection()
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: list[ToolCall] = Field(default_factory=list)
    _current_base64_image: str | None = None

    max_steps: int = 30
    max_observe: int | bool | None = None

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        # Check if we need to add next_step_prompt to the last user message
        if self.next_step_prompt and self.messages:
            last_msg = self.messages[-1]
            # If the last message is a user message, append next_step_prompt to it
            if last_msg.role == "user" and not any(
                self.next_step_prompt in msg.content
                for msg in self.messages
                if msg.role == "user"
            ):
                # Update the last user message content
                combined_content = (
                    f"Question: {last_msg.content}\n\nGuide: {self.next_step_prompt}"
                )
                # Replace the last message with updated content
                self.messages[-1] = Message.user_message(combined_content)
            elif last_msg.role != "user":
                # If last message is not user message, add as separate message
                user_msg = Message.user_message(self.next_step_prompt)
                self.messages += [user_msg]

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=(
                    [Message.system_message(self.system_prompt)]
                    if self.system_prompt
                    else None
                ),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {token_limit_error!s}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

        # Send thinking content via WebSocket if available
        await self._send_thinking_event(content)

        # Send LLM_MESSAGE event after LLM call
        await self._send_llm_message_event()

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {content}")
        logger.info(
            f"🛠️ {self.name} selected {len(tool_calls) if tool_calls else 0} tools to use"
        )
        if tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in tool_calls]}"
            )
            logger.info(f"🔧 Tool arguments: {tool_calls[0].function.arguments}")

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(f"Error encountered while processing: {e!s}")
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            # Reset base64_image for each tool call
            self._current_base64_image = None

            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image,
            )
            self.memory.add_message(tool_msg)
            results.append(result)

        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        logger.info(
            f"🛠️ Preparing to execute tool: '{name}' with arguments: {command.function.arguments}"
        )
        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'..., {type(args)}")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Handle special tools
            await self._handle_special_tool(name=name, result=result)

            # Check if result is a ToolResult with base64_image
            if hasattr(result, "base64_image") and result.base64_image:
                # Store the base64_image for later use in tool_message
                self._current_base64_image = result.base64_image

            # Format result for display (standard case)
            observation = (
                f"Observed output of cmd `{name}` executed:\n{result!s}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {e!s}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Generate summary before finishing
            await self._generate_final_summary()

            # Send LLM_MESSAGE event if enabled
            await self._send_llm_message_event()

            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**_kwargs) -> bool:  # pylint: disable=unused-argument
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def _generate_final_summary(self):
        """Generate a final summary of the conversation and task execution"""
        try:
            # Find the current conversation's user question (last user message before summary prompt)
            original_question = None
            # Look for the last user message that's not the summary prompt or next step prompt
            for msg in reversed(self.memory.messages):
                if (
                    msg.role == "user"
                    and SUMMARY_PROMPT not in msg.content
                    and self.next_step_prompt != msg.content
                ):
                    # If the message contains next_step_prompt, extract the original question part
                    if "Question:" in msg.content and "Guide:" in msg.content:
                        # Extract the question part from combined content
                        question_part = (
                            msg.content.split("Guide:")[0]
                            .replace("Question:", "")
                            .strip()
                        )
                        original_question = question_part
                    else:
                        original_question = msg.content
                    break

            # Create summary prompt including original question
            summary_prompt_with_question = SUMMARY_PROMPT
            if original_question:
                summary_prompt_with_question = (
                    f"Original Question: {original_question}\n\n{SUMMARY_PROMPT}"
                )

            # Add user message to prompt for summary generation
            summary_user_msg = Message.user_message(summary_prompt_with_question)
            self.memory.add_message(summary_user_msg)

            logger.info("📝 Generating final summary of the conversation...")

            # Clean messages to ensure valid tool_calls sequence for LLM API
            clean_messages = self._get_clean_messages_for_summary()

            # Check if we have WebSocket streaming capabilities
            ws_session = None

            # Try to get WebSocket session from trace manager
            if TRACE_AVAILABLE:
                try:
                    from myagent.trace import get_ws_session_context
                    ws_session = get_ws_session_context()
                except Exception as e:
                    logger.debug(f"Could not get WebSocket session: {e}")

            # Use streaming if WebSocket session is available
            if ws_session:
                logger.info("📡 Using WebSocket streaming for summary generation")
                summary_content = await self._generate_streaming_summary(
                    clean_messages, ws_session
                )
            else:
                logger.info("📝 Using regular LLM call for summary generation")
                summary_content = await self._generate_regular_summary(clean_messages)

            if summary_content:
                # Add the summary as assistant message
                summary_msg = Message.assistant_message(summary_content)
                self.memory.add_message(summary_msg)
                logger.info(f"✨ Final summary generated: {summary_content[:200]}...")

                # Store the summary as final response
                self.final_response = summary_content
            else:
                logger.warning("⚠️ Failed to generate summary - no response from LLM")

        except Exception as e:
            logger.error(f"🚨 Error generating final summary: {e}")
            # Don't fail the entire process if summary generation fails
            pass

    def _get_clean_messages_for_summary(self):
        """Get cleaned messages ensuring valid tool_calls sequence for summary generation.

        This removes any incomplete tool_calls sequences that could cause API errors.
        """
        messages = self.memory.messages[:]  # Copy the messages
        clean_messages = []

        i = 0
        while i < len(messages):
            msg = messages[i]

            # If this is an assistant message with tool_calls
            if msg.role == "assistant" and msg.tool_calls:
                tool_call_ids = {tc.id for tc in msg.tool_calls}

                # Look ahead to find corresponding tool messages
                j = i + 1
                found_tool_responses = set()

                while j < len(messages) and messages[j].role == "tool":
                    if messages[j].tool_call_id in tool_call_ids:
                        found_tool_responses.add(messages[j].tool_call_id)
                    j += 1

                # If all tool_calls have responses, include the sequence
                if found_tool_responses == tool_call_ids:
                    # Add the assistant message and all its tool responses
                    clean_messages.append(msg)
                    for k in range(i + 1, j):
                        if (
                            messages[k].role == "tool"
                            and messages[k].tool_call_id in tool_call_ids
                        ):
                            clean_messages.append(messages[k])
                    i = j
                else:
                    # Skip incomplete tool_calls sequence - convert to plain assistant message
                    clean_msg = Message.assistant_message(msg.content or "")
                    clean_messages.append(clean_msg)
                    i += 1
            else:
                # For non-tool_calls messages, add as-is (except tool messages without corresponding assistant)
                if msg.role != "tool" or any(
                    prev_msg.role == "assistant"
                    and prev_msg.tool_calls
                    and any(tc.id == msg.tool_call_id for tc in prev_msg.tool_calls)
                    for prev_msg in clean_messages
                ):
                    clean_messages.append(msg)
                i += 1

        return clean_messages

    async def _generate_regular_summary(self, clean_messages):
        """Generate summary using regular LLM call without streaming."""
        response = await self.llm.ask(
            messages=clean_messages,
            system_msgs=(
                [Message.system_message(self.system_prompt)]
                if self.system_prompt
                else None
            ),
            stream=False,  # Explicitly disable streaming for regular call
        )

        # Send LLM_MESSAGE event after LLM call
        await self._send_llm_message_event()

        # Handle different response formats
        if response:
            if isinstance(response, str):
                return response
            elif hasattr(response, "content") and response.content:
                return response.content
        return None

    async def _generate_streaming_summary(self, clean_messages, ws_session):
        """Generate summary with WebSocket streaming support."""
        try:
            from myagent.ws.events import AgentEvents
            from myagent.ws.events import create_event

            # Send thinking event
            await ws_session._send_event(
                create_event(
                    AgentEvents.THINKING,
                    session_id=ws_session.session_id,
                    content="正在生成最终总结...",
                    metadata={"streaming": True},
                )
            )

            # Create a custom streaming LLM call
            summary_content = await self._stream_llm_with_websocket(
                clean_messages, ws_session
            )

            return summary_content

        except Exception as e:
            logger.error(f"Error in streaming summary generation: {e}")
            # Fallback to regular summary
            return await self._generate_regular_summary(clean_messages)

    async def _stream_llm_with_websocket(self, clean_messages, ws_session):
        """Stream LLM response via WebSocket with partial_answer events."""
        try:
            from myagent.ws.events import AgentEvents
            from myagent.ws.events import create_event

            # Check if the model supports images
            supports_images = self.llm.model in [
                "gpt-4-vision-preview",
                "gpt-4o",
                "gpt-4o-mini",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ]

            # Format messages
            system_msgs = (
                [Message.system_message(self.system_prompt)]
                if self.system_prompt
                else None
            )
            if system_msgs:
                formatted_system = self.llm.format_messages(
                    system_msgs, supports_images
                )
                formatted_messages = formatted_system + self.llm.format_messages(
                    clean_messages, supports_images
                )
            else:
                formatted_messages = self.llm.format_messages(
                    clean_messages, supports_images
                )

            # Calculate input token count and check limits
            input_tokens = self.llm.count_message_tokens(formatted_messages)
            if not self.llm.check_token_limit(input_tokens):
                error_message = self.llm.get_limit_error_message(input_tokens)
                raise TokenLimitExceeded(error_message)

            # Set up streaming parameters
            params = {
                "model": self.llm.model,
                "messages": formatted_messages,
                "stream": True,
            }

            # Add model-specific parameters
            if self.llm.model in ["o1", "o3-mini", "Qwen/Qwen3-32B"]:
                params["max_completion_tokens"] = self.llm.max_tokens
            else:
                params["max_tokens"] = self.llm.max_tokens
                params["temperature"] = self.llm.temperature

            # Update token count for streaming
            self.llm.update_token_count(input_tokens)

            # Start streaming
            response = await self.llm.client.chat.completions.create(**params)

            collected_content = []
            chunk_buffer = ""
            word_count = 0

            async for chunk in response:
                chunk_content = chunk.choices[0].delta.content or ""
                if not chunk_content:
                    continue

                collected_content.append(chunk_content)
                chunk_buffer += chunk_content

                # Send partial answer every few words or when we hit sentence boundaries
                if (
                    " " in chunk_content
                    or "。" in chunk_content
                    or "." in chunk_content
                    or "\n" in chunk_content
                    or len(chunk_buffer) > 50
                ):
                    word_count += len(chunk_buffer.split())

                    # Send partial answer event
                    await ws_session._send_event(
                        create_event(
                            AgentEvents.PARTIAL_ANSWER,
                            session_id=ws_session.session_id,
                            content=chunk_buffer,
                            metadata={
                                "is_streaming": True,
                                "word_count": word_count,
                                "is_final": False,
                            },
                        )
                    )

                    chunk_buffer = ""

            # Send any remaining content
            if chunk_buffer:
                await ws_session._send_event(
                    create_event(
                        AgentEvents.PARTIAL_ANSWER,
                        session_id=ws_session.session_id,
                        content=chunk_buffer,
                        metadata={
                            "is_streaming": True,
                            "word_count": word_count + len(chunk_buffer.split()),
                            "is_final": False,
                        },
                    )
                )

            full_response = "".join(collected_content).strip()
            if not full_response:
                raise ValueError("Empty response from streaming LLM")

            # Send final partial answer to mark completion
            await ws_session._send_event(
                create_event(
                    AgentEvents.PARTIAL_ANSWER,
                    session_id=ws_session.session_id,
                    content="",
                    metadata={
                        "is_streaming": True,
                        "is_final": True,
                        "total_length": len(full_response),
                    },
                )
            )

            # Estimate completion tokens
            completion_tokens = self.llm.count_tokens(full_response)
            self.llm.total_completion_tokens += completion_tokens

            logger.info(
                f"✅ Streaming summary completed: {len(full_response)} characters"
            )

            # Send LLM_MESSAGE event after streaming LLM call
            await self._send_llm_message_event()

            return full_response

        except Exception as e:
            logger.error(f"Error in WebSocket streaming: {e}")
            # Send error event
            await ws_session._send_event(
                create_event(
                    AgentEvents.ERROR,
                    session_id=ws_session.session_id,
                    content=f"流式生成出错: {e!s}",
                )
            )
            raise

    async def _send_thinking_event(self, content: str):
        """Send thinking event via WebSocket if available"""
        if not content:
            return

        # Check if we have WebSocket streaming capabilities
        ws_session = None

        # Try to get WebSocket session from trace manager
        if TRACE_AVAILABLE:
            try:
                from myagent.trace import get_ws_session_context
                ws_session = get_ws_session_context()
                logger.debug(f"WebSocket session in think(): {ws_session is not None}")
            except Exception as e:
                logger.debug(f"Could not get WebSocket session: {e}")

        if ws_session:
            try:
                from myagent.ws.events import AgentEvents
                from myagent.ws.events import create_event

                await ws_session._send_event(
                    create_event(
                        AgentEvents.THINKING,
                        session_id=ws_session.session_id,
                        content=content,
                        metadata={"step": getattr(self, "_current_step", 0)},
                    )
                )
            except Exception as e:
                logger.debug(f"Failed to send thinking event: {e}")

    async def _send_llm_message_event(self):
        """Send LLM_MESSAGE event with memory messages if environment variable is enabled"""
        # Check if SEND_LLM_MESSAGE environment variable is set to enable this feature
        if os.getenv("SEND_LLM_MESSAGE", "").lower() not in ("true", "1", "yes", "on"):
            return

        # Check if we have WebSocket streaming capabilities
        ws_session = None

        # Try to get WebSocket session from trace manager
        if TRACE_AVAILABLE:
            try:
                from myagent.trace import get_ws_session_context
                ws_session = get_ws_session_context()
            except Exception as e:
                logger.debug(f"Could not get WebSocket session for LLM_MESSAGE: {e}")

        if ws_session:
            try:
                from myagent.ws.events import AgentEvents
                from myagent.ws.events import create_event

                # Convert memory messages to dict format
                messages_dict = self.memory.to_dict_list()

                # Send LLM_MESSAGE event with all conversation messages
                await ws_session._send_event(
                    create_event(
                        AgentEvents.LLM_MESSAGE,
                        session_id=ws_session.session_id,
                        content={
                            "messages": messages_dict,
                            "total_messages": len(messages_dict),
                        },
                        metadata={
                            "agent_name": self.name,
                            "agent_state": self.state.value,
                            "final_response": getattr(self, "final_response", None),
                        },
                    )
                )

                logger.info(
                    f"📤 Sent LLM_MESSAGE event with {len(messages_dict)} messages"
                )

            except Exception as e:
                logger.error(f"Failed to send LLM_MESSAGE event: {e}")

    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(
                        f"🚨 Error cleaning up tool '{tool_name}': {e}", exc_info=True
                    )
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")

    async def run(self, request: str | None = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            result = await super().run(request)
            
            # Check if we reached max steps and need to generate summary
            if self.current_step >= self.max_steps and self.state != AgentState.FINISHED:
                logger.info(f"🏁 Reached max steps ({self.max_steps}), generating final summary...")
                await self._generate_final_summary()
                await self._send_llm_message_event()
                self.state = AgentState.FINISHED
            
            return result
        finally:
            await self.cleanup()
