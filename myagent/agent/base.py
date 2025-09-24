from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from ..llm import LLM
from ..logger import logger
from ..schema import ROLE_TYPE, AgentState, Memory, Message, Role
from ..trace import trace, run, RunType, TraceMetadata, get_trace_manager
from ..trace.decorators import trace_agent_step


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2
    final_response: Optional[str] = Field(
        None, description="Final response after execution"
    )
    
    # Tracing
    enable_tracing: bool = Field(default=True, description="Enable execution tracing")
    trace_metadata: Optional[TraceMetadata] = Field(None, description="Custom trace metadata")

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state

    def update_memory(
        self,
        role: ROLE_TYPE,  # type: ignore
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            base64_image: Optional base64 encoded image.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        # Create message with appropriate parameters based on role
        if role == "system":
            # system_message only accepts content parameter
            self.memory.add_message(message_map[role](content))
        elif role == "tool":
            # tool_message accepts all kwargs
            kwargs = {"base64_image": base64_image, **kwargs}
            self.memory.add_message(message_map[role](content, **kwargs))
        else:
            # user and assistant messages accept base64_image
            kwargs = {"base64_image": base64_image}
            self.memory.add_message(message_map[role](content, **kwargs))

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously.

        Args:
            request: Optional initial user request to process.

        Returns:
            A string summarizing the execution results.

        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            self.update_memory("user", request)

        # Create trace if tracing is enabled
        if self.enable_tracing:
            trace_manager = get_trace_manager()
            metadata = self.trace_metadata or TraceMetadata()
            
            # Add agent info to metadata
            metadata.custom_fields.update({
                "agent_name": self.name,
                "agent_description": self.description,
                "max_steps": self.max_steps
            })
            
            async with trace_manager.trace(
                name=f"{self.name}_execution",
                request=request,
                metadata=metadata
            ) as trace_ctx:
                return await self._run_with_tracing(request, trace_ctx)
        else:
            return await self._run_without_tracing(request)
    
    async def _run_with_tracing(self, request: Optional[str], trace_ctx) -> str:
        """Execute the agent with tracing enabled."""
        results: List[str] = []
        final_state = None
        
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                
                # Trace each step
                step_result = await self._traced_step()

                # Check for stuck state
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            # Capture the final state before state_context reverts it
            final_state = self.state
            
            if self.current_step >= self.max_steps:
                self.current_step = 0
                final_state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")
        
        # Set the final state after exiting state_context
        if final_state:
            self.state = final_state

        last_llm_response = self._get_last_llm_response()
        if last_llm_response is not None:
            self.final_response = last_llm_response
        else:
            self.final_response = results[-1] if results else None

        # Update trace with final response
        trace_ctx.response = self.final_response

        return "\n".join(results) if results else "No steps executed"
    
    async def _run_without_tracing(self, request: Optional[str]) -> str:
        """Execute the agent without tracing (original logic)."""
        results: List[str] = []
        final_state = None
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            # Capture the final state before state_context reverts it
            final_state = self.state
            
            if self.current_step >= self.max_steps:
                self.current_step = 0
                final_state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")
        
        # Set the final state after exiting state_context
        if final_state:
            self.state = final_state

        last_llm_response = self._get_last_llm_response()
        if last_llm_response is not None:
            self.final_response = last_llm_response
        else:
            self.final_response = results[-1] if results else None

        return "\n".join(results) if results else "No steps executed"
    
    async def _traced_step(self) -> str:
        """Execute a single step with tracing."""
        trace_manager = get_trace_manager()
        
        inputs = {
            "step_number": self.current_step,
            "max_steps": self.max_steps,
            "agent_state": str(self.state),
            "memory_size": len(self.memory.messages),
            "all_messages": self._get_recent_messages_summary(),
            "system_prompt": self.system_prompt or "",
            "next_step_prompt": self.next_step_prompt or ""
        }
        
        async with trace_manager.run(
            name=f"step_{self.current_step}",
            run_type=RunType.AGENT,
            inputs=inputs
        ) as run_ctx:
            # Check if this is a ReActAgent to provide detailed tracing
            if hasattr(self, 'think') and hasattr(self, 'act'):
                result = await self._traced_react_step(run_ctx)
            else:
                result = await self.step()
                run_ctx.outputs["result"] = result
            
            return result
    
    async def _traced_react_step(self, parent_run_ctx) -> str:
        """Execute a ReAct step with Think → Tools structure (no Act layer)."""
        trace_manager = get_trace_manager()
        
        async with trace_manager.run(
            name=f"think_step_{self.current_step}",
            run_type=RunType.THINK,
            inputs={},  # Will be updated after think() execution
            parent_run_id=parent_run_ctx.id
        ) as think_run:
            should_act = await self.think()
            
            # Get messages after think() execution for complete trace
            user_msg_after = self._get_last_user_message()
            assistant_msg = self._get_last_assistant_message()
            
            # Update inputs with the final user message (after potential merging in think())
            think_run.inputs.update(user_msg_after.to_dict() if user_msg_after else {})
            
            # Update outputs with assistant message
            think_run.outputs.update(assistant_msg.to_dict() if assistant_msg else {})

            if not should_act:
                parent_run_ctx.outputs["result"] = "Thinking complete - no action needed"
                return "Thinking complete - no action needed"
        
        # Execute actions directly - Tool traces will be recorded as direct children of the step
        result = await self.act()
        parent_run_ctx.outputs["result"] = result
        return result
    
    def _get_recent_messages_summary(self, limit: int = None) -> list:
        """Get a summary of messages for tracing.
        
        Args:
            limit: Maximum number of recent messages to include. 
                   If None, includes all messages in memory.
        
        Returns:
            List of message summaries with tool call information.
        """
        if limit is None:
            # Get all messages
            recent_messages = self.memory.messages
        else:
            # Get limited recent messages
            recent_messages = self.memory.get_recent_messages(limit)
        summary = []
        
        for msg in recent_messages:
            msg_summary = {
                "role": msg.role,
                "content": msg.content[:200] + "..." if msg.content and len(msg.content) > 200 else msg.content,
                "has_tool_calls": bool(msg.tool_calls)
            }
            
            # Add tool call details if present
            if msg.tool_calls:
                msg_summary["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments[:100] + "..." 
                            if len(tool_call.function.arguments) > 100 
                            else tool_call.function.arguments
                        }
                    }
                    for tool_call in msg.tool_calls
                ]
                msg_summary["tool_call_count"] = len(msg.tool_calls)
            
            # Add additional info for tool messages
            if msg.role == "tool":
                msg_summary["tool_name"] = msg.name
                msg_summary["tool_call_id"] = msg.tool_call_id
            
            summary.append(msg_summary)
        
        return summary
    
    def _get_memory_state_summary(self) -> dict:
        """Get a summary of current memory state."""
        tool_stats = self._get_tool_usage_stats()
        return {
            "total_messages": len(self.memory.messages),
            "all_messages": self._get_recent_messages_summary(),
            "message_types": self._count_message_types(),
            "tool_usage": tool_stats
        }
    
    def _count_message_types(self) -> dict:
        """Count messages by type."""
        counts = {}
        for msg in self.memory.messages:
            counts[msg.role] = counts.get(msg.role, 0) + 1
        return counts
    
    def _get_tool_usage_stats(self) -> dict:
        """Get statistics about tool usage in memory."""
        tool_stats = {
            "total_tool_calls": 0,
            "total_tool_responses": 0,
            "tools_used": {},
            "recent_tool_calls": []
        }
        
        for msg in self.memory.messages:
            # Count tool calls from assistant messages
            if msg.role == "assistant" and msg.tool_calls:
                tool_stats["total_tool_calls"] += len(msg.tool_calls)
                
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    tool_stats["tools_used"][tool_name] = tool_stats["tools_used"].get(tool_name, 0) + 1
                    
                    # Add to recent tool calls (last 5)
                    if len(tool_stats["recent_tool_calls"]) < 5:
                        tool_stats["recent_tool_calls"].append({
                            "tool_name": tool_name,
                            "tool_id": tool_call.id,
                            "arguments_preview": tool_call.function.arguments[:50] + "..." 
                            if len(tool_call.function.arguments) > 50 
                            else tool_call.function.arguments
                        })
            
            # Count tool response messages
            elif msg.role == "tool":
                tool_stats["total_tool_responses"] += 1
        
        return tool_stats
    
    def _get_current_context(self) -> dict:
        """Get current agent context for thinking."""
        return {
            "agent_name": self.name,
            "current_step": self.current_step,
            "max_steps": self.max_steps,
            "state": str(self.state),
            "has_system_prompt": bool(self.system_prompt),
            "has_next_step_prompt": bool(self.next_step_prompt)
        }

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logger.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    def _get_last_llm_response(self) -> Optional[str]:
        """Return the most recent assistant message content from memory."""
        for message in reversed(self.memory.messages):
            if message.role == Role.ASSISTANT.value and message.content:
                return message.content
        return None

    def _get_last_user_message(self) -> Optional[Message]:
        """Return the most recent user message from memory."""
        for message in reversed(self.memory.messages):
            if message.role == Role.USER.value:
                return message
        return None

    def _get_last_assistant_message(self) -> Optional[Message]:
        """Return the most recent assistant message from memory."""
        for message in reversed(self.memory.messages):
            if message.role == Role.ASSISTANT.value:
                return message
        return None

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
