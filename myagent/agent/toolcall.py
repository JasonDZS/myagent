import asyncio
import json
import re
from typing import Any, List, Optional, Union

from pydantic import Field

from .react import ReActAgent
from ..exceptions import TokenLimitExceeded
from ..logger import logger
from ..prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT, SUMMARY_PROMPT
from ..schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from ..tool import ToolCollection, Terminate

try:
    from ..trace import get_trace_manager
    TRACE_AVAILABLE = True
except ImportError:
    TRACE_AVAILABLE = False


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection()
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        # Check if we need to add next_step_prompt to the last user message
        if self.next_step_prompt and self.messages:
            last_msg = self.messages[-1]
            # If the last message is a user message, append next_step_prompt to it
            if last_msg.role == "user" and not any(self.next_step_prompt in msg.content for msg in self.messages if msg.role == "user"):
                # Update the last user message content
                combined_content = f"Question: {last_msg.content}\n\nGuide: {self.next_step_prompt}"
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
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

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
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
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

        logger.info(f"🛠️ Preparing to execute tool: '{name}' with arguments: {command.function.arguments}")
        try:
            # Parse arguments
            try:
                args = json.loads(command.function.arguments or "{}")
            except Exception as e:
                logger.error(e)
                text = command.function.arguments
                pattern = rf'["\']?{re.escape("retriveled_knowledge")}["\']?\s*:\s*("((?:\\.|[^"\\])*)"|\'((?:\\.|[^\'\\])*)\'|([^\s,}}]+))'
                m = re.search(pattern, text)
                for grp in m.groups()[1:]:
                    if grp:
                        # args = {"retriveled_knowledge":grp}
                        args = {"min_similarity": 0.5, "query": "企业信贷评估模板 融资需求评估", "top_k": 3}

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
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
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
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Generate summary before finishing
            await self._generate_final_summary()
            
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def _generate_final_summary(self):
        """Generate a final summary of the conversation and task execution"""
        try:
            # Add user message to prompt for summary generation
            summary_user_msg = Message.user_message(SUMMARY_PROMPT)
            self.memory.add_message(summary_user_msg)
            
            logger.info("📝 Generating final summary of the conversation...")
            
            # Clean messages to ensure valid tool_calls sequence for LLM API
            clean_messages = self._get_clean_messages_for_summary()
            
            # Check if we have WebSocket streaming capabilities
            websocket_manager = None
            session_id = None
            stream_context = None
            
            # Try to get WebSocket manager from trace manager
            if TRACE_AVAILABLE:
                try:
                    trace_manager = get_trace_manager()
                    if hasattr(trace_manager, 'connection_manager') and hasattr(trace_manager, 'current_session_id'):
                        websocket_manager = trace_manager.connection_manager
                        session_id = trace_manager.current_session_id
                        
                        # Get current trace context for streaming
                        current_trace = getattr(trace_manager, '_current_trace', None)
                        current_run = getattr(trace_manager, '_current_run', None)
                        if current_trace and current_run:
                            stream_context = {
                                "trace_id": current_trace.trace_id,
                                "run_id": current_run.run_id,
                                "parent_run_id": current_run.parent_run_id
                            }
                except Exception as e:
                    logger.debug(f"Could not get WebSocket manager: {e}")
            
            # Get summary from LLM using streaming if available, otherwise fallback to regular ask
            if websocket_manager and session_id and hasattr(self.llm, 'ask_with_streaming'):
                logger.info("🌊 Using real-time streaming for summary generation")
                response = await self.llm.ask_with_streaming(
                    messages=clean_messages,
                    system_msgs=(
                        [Message.system_message(self.system_prompt)]
                        if self.system_prompt
                        else None
                    ),
                    websocket_manager=websocket_manager,
                    session_id=session_id,
                    stream_context=stream_context
                )
            else:
                logger.info("📝 Using regular LLM call for summary generation")
                response = await self.llm.ask(
                    messages=clean_messages,
                    system_msgs=(
                        [Message.system_message(self.system_prompt)]
                        if self.system_prompt
                        else None
                    )
                )
            
            # Handle different response formats
            summary_content = None
            if response:
                if isinstance(response, str):
                    # Response is a direct string
                    summary_content = response
                elif hasattr(response, 'content') and response.content:
                    # Response is an object with content attribute
                    summary_content = response.content
                else:
                    logger.warning("⚠️ Response received but no content found")
            
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
                        if messages[k].role == "tool" and messages[k].tool_call_id in tool_call_ids:
                            clean_messages.append(messages[k])
                    i = j
                else:
                    # Skip incomplete tool_calls sequence - convert to plain assistant message
                    clean_msg = Message.assistant_message(msg.content or "")
                    clean_messages.append(clean_msg)
                    i += 1
            else:
                # For non-tool_calls messages, add as-is (except tool messages without corresponding assistant)
                if msg.role != "tool" or any(prev_msg.role == "assistant" and prev_msg.tool_calls 
                                           and any(tc.id == msg.tool_call_id for tc in prev_msg.tool_calls)
                                           for prev_msg in clean_messages):
                    clean_messages.append(msg)
                i += 1
        
        return clean_messages

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

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            return await super().run(request)
        finally:
            await self.cleanup()
