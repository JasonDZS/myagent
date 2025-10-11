from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..llm import LLM
from ..logger import logger
from ..schema import ROLE_TYPE, AgentState, Memory, Message, Role


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: str | None = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: str | None = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: str | None = Field(
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
    max_retry_attempts: int = Field(
        default=0,
        ge=0,
        description="Number of additional retries allowed after an execution failure",
    )
    retry_delay_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Delay between retry attempts in seconds",
    )

    duplicate_threshold: int = 1
    final_response: str | None = Field(
        None, description="Final response after execution"
    )

    # WebSocket session for streaming support
    ws_session: Any | None = Field(
        None, description="WebSocket session for real-time event streaming"
    )

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
        base64_image: str | None = None,
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

    async def run(self, request: str | None = None) -> str:
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

        results: list[str] = []
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

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    def handle_stuck_state(self):
        """Handle stuck state with stronger intervention"""
        stuck_prompt = (
            "IMPORTANT: You are repeating identical responses. "
            "Change your approach completely. Consider: "
            "1) Different tool usage, 2) Different analysis angle, "
            "3) Skip to final answer if enough info available."
        )

        # Stronger intervention - replace instead of append to ensure it's seen
        original_prompt = self.next_step_prompt or ""
        self.next_step_prompt = (
            f"{stuck_prompt}\n\nOriginal guide: {original_prompt}"
            if original_prompt
            else stuck_prompt
        )

        # Also add a system message to memory for immediate impact
        system_msg = Message.system_message(
            "System: Detected repetitive responses. Please change your approach immediately."
        )
        self.memory.add_message(system_msg)

        logger.warning(
            f"Agent {self.name} detected stuck state. Strong intervention applied."
        )

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate assistant content"""
        if len(self.memory.messages) < 2:
            return False

        # Get all assistant messages with content
        assistant_messages = [
            msg
            for msg in self.memory.messages
            if msg.role == "assistant" and msg.content
        ]

        if len(assistant_messages) < 2:
            return False

        # Check the last assistant message for duplicates
        last_assistant_message = assistant_messages[-1]

        # Count identical content occurrences in previous assistant messages
        duplicate_count = sum(
            1
            for msg in assistant_messages[:-1]  # Exclude the last one
            if msg.content == last_assistant_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    def _get_last_llm_response(self) -> str | None:
        """Return the most recent assistant message content from memory."""
        for message in reversed(self.memory.messages):
            if message.role == Role.ASSISTANT.value and message.content:
                return message.content
        return None

    def _get_last_user_message(self) -> Message | None:
        """Return the most recent user message from memory."""
        for message in reversed(self.memory.messages):
            if message.role == Role.USER.value:
                return message
        return None

    def _get_last_assistant_message(self) -> Message | None:
        """Return the most recent assistant message from memory."""
        for message in reversed(self.memory.messages):
            if message.role == Role.ASSISTANT.value:
                return message
        return None

    @property
    def messages(self) -> list[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: list[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value

    def get_statistics(self) -> dict[str, Any]:
        """Return accumulated LLM usage statistics for this agent."""
        call_history: list[dict[str, Any]] = getattr(self.llm, "call_history", [])

        total_input_tokens = sum(
            record.get("input_tokens", 0) for record in call_history
        )
        total_output_tokens = sum(
            record.get("output_tokens", 0) for record in call_history
        )

        calls: list[dict[str, Any]] = []
        for record in call_history:
            record_copy = record.copy()
            metadata = record_copy.get("metadata")
            if isinstance(metadata, dict):
                record_copy["metadata"] = metadata.copy()
            calls.append(record_copy)

        return {
            "agent": self.name,
            "model": getattr(self.llm, "model", None),
            "total_calls": len(call_history),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "running_totals": {
                "input_tokens": getattr(self.llm, "total_input_tokens", 0),
                "output_tokens": getattr(self.llm, "total_completion_tokens", 0),
                "max_input_tokens": getattr(self.llm, "max_input_tokens", None),
            },
            "calls": calls,
        }
