from abc import ABC
from abc import abstractmethod
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: dict | None = None
    user_confirm: bool = Field(
        default=False, description="Require user confirmation before execution"
    )

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        # Check if user confirmation is required
        if self.user_confirm:
            confirmed = await self._request_user_confirmation(**kwargs)
            if not confirmed:
                return ToolResult(error="Tool execution cancelled by user")

        return await self.execute(**kwargs)

    async def _request_user_confirmation(self, **kwargs) -> bool:
        """Request user confirmation for tool execution."""
        # Try to get the WebSocket session from the current context
        confirmation_handler = getattr(self, "_confirmation_handler", None)
        if confirmation_handler:
            return await confirmation_handler(self, kwargs)

        # Fallback: no WebSocket context, assume confirmation granted
        # This allows tools to work in non-WebSocket environments
        return True

    def set_confirmation_handler(self, handler):
        """Set the confirmation handler for WebSocket sessions."""
        self._confirmation_handler = handler

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: str | None = Field(default=None)
    base64_image: str | None = Field(default=None)
    system: str | None = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: str | None, other_field: str | None, concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            base64_image=combine_fields(self.base64_image, other.base64_image, False),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""
