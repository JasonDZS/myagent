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
            "memory_size": len(self.memory.messages)
        }
        
        async with trace_manager.run(
            name=f"step_{self.current_step}",
            run_type=RunType.AGENT,
            inputs=inputs
        ) as run_ctx:
            result = await self.step()
            run_ctx.outputs["result"] = result
            return result

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

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
