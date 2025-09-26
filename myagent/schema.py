from enum import Enum
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class Role(str, Enum):
    """Message role options"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]  # type: ignore


class ToolChoice(str, Enum):
    """Tool choice options"""

    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]  # type: ignore


class AgentState(str, Enum):
    """Agent execution states"""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class Function(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    """Represents a tool/function call in a message"""

    id: str
    type: str = "function"
    function: Function


class Message(BaseModel):
    """Represents a chat message in the conversation"""

    role: ROLE_TYPE = Field(...)  # type: ignore
    content: str | None = Field(default=None)
    tool_calls: list[ToolCall] | None = Field(default=None)
    name: str | None = Field(default=None)
    tool_call_id: str | None = Field(default=None)
    base64_image: str | None = Field(default=None)

    def __add__(self, other) -> list["Message"]:
        """支持 Message + list 或 Message + Message 的操作"""
        if isinstance(other, list):
            return [self, *other]
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> list["Message"]:
        """支持 list + Message 的操作"""
        if isinstance(other, list):
            return [*other, self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.dict() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        if self.base64_image is not None:
            message["base64_image"] = self.base64_image
        return message

    @classmethod
    def user_message(cls, content: str, base64_image: str | None = None) -> "Message":
        """Create a user message"""
        return cls(role=Role.USER.value, content=content, base64_image=base64_image)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role=Role.SYSTEM.value, content=content)

    @classmethod
    def assistant_message(
        cls, content: str | None = None, base64_image: str | None = None
    ) -> "Message":
        """Create an assistant message"""
        return cls(
            role=Role.ASSISTANT.value, content=content, base64_image=base64_image
        )

    @classmethod
    def tool_message(
        cls, content: str, name, tool_call_id: str, base64_image: str | None = None
    ) -> "Message":
        """Create a tool message"""
        return cls(
            role=Role.TOOL.value,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            base64_image=base64_image,
        )

    @classmethod
    def from_tool_calls(
        cls,
        tool_calls: list[Any],
        content: str | list[str] = "",
        base64_image: str | None = None,
        **kwargs,
    ):
        """Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
            base64_image: Optional base64 encoded image
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role=Role.ASSISTANT.value,
            content=content,
            tool_calls=formatted_calls,
            base64_image=base64_image,
            **kwargs,
        )


class Memory(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: list[Message]) -> None:
        """Add multiple messages to memory"""
        self.messages.extend(messages)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> list[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> list[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]

    def clean_incomplete_tool_calls(self) -> None:
        """Clean incomplete tool_calls messages to fix OpenAI API compatibility.

        Removes:
        1. Assistant messages with tool_calls that don't have corresponding tool response messages
        2. Orphaned tool messages that don't have a preceding assistant message with tool_calls

        This fixes API errors in multi-turn conversations.
        """
        if not self.messages:
            return

        # First pass: identify all valid tool_call_ids that have complete chains
        valid_tool_call_ids = set()

        for i, msg in enumerate(self.messages):
            if (
                msg.role == Role.ASSISTANT.value
                and msg.tool_calls is not None
                and len(msg.tool_calls) > 0
            ):
                tool_call_ids = {tc.id for tc in msg.tool_calls}
                found_responses = set()

                # Check subsequent messages for tool responses
                j = i + 1
                while j < len(self.messages):
                    next_msg = self.messages[j]

                    if (
                        next_msg.role == Role.TOOL.value
                        and next_msg.tool_call_id in tool_call_ids
                    ):
                        found_responses.add(next_msg.tool_call_id)
                    elif next_msg.role in [Role.ASSISTANT.value, Role.USER.value]:
                        break
                    j += 1

                # If all tool calls have responses, mark them as valid
                if found_responses == tool_call_ids:
                    valid_tool_call_ids.update(tool_call_ids)

        # Second pass: keep only messages that are valid
        cleaned_messages = []

        for msg in self.messages:
            if msg.role == Role.TOOL.value:
                # Keep tool messages only if they respond to valid tool calls
                if msg.tool_call_id in valid_tool_call_ids:
                    cleaned_messages.append(msg)
                # Otherwise skip orphaned tool messages
            elif (
                msg.role == Role.ASSISTANT.value
                and msg.tool_calls is not None
                and len(msg.tool_calls) > 0
            ):
                # Keep assistant messages with tool_calls only if all their calls are valid
                tool_call_ids = {tc.id for tc in msg.tool_calls}
                if tool_call_ids.issubset(valid_tool_call_ids):
                    cleaned_messages.append(msg)
                # Otherwise skip incomplete tool_calls messages
            else:
                # Keep all other messages (user, system, assistant without tool_calls)
                cleaned_messages.append(msg)

        # Update messages with cleaned version
        self.messages = cleaned_messages
