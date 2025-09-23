from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ..trace import get_trace_manager, RunType
from ..trace.decorators import trace_tool_call


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None
    enable_tracing: bool = Field(default=True, description="Enable execution tracing")

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        if self.enable_tracing:
            return await self._traced_execute(**kwargs)
        else:
            return await self.execute(**kwargs)
    
    async def _traced_execute(self, **kwargs) -> Any:
        """Execute the tool with tracing enabled."""
        trace_manager = get_trace_manager()
        
        # Prepare inputs for tracing
        inputs = dict(kwargs)
        
        # Prepare metadata
        metadata = {
            "tool_description": self.description,
            "tool_parameters": self.parameters
        }
        
        async with trace_manager.run(
            name=self.name,
            run_type=RunType.TOOL,
            inputs=inputs,
            **metadata
        ) as run_ctx:
            try:
                result = await self.execute(**kwargs)
                
                # Capture tool result
                if result is not None:
                    if hasattr(result, 'output'):
                        # Handle ToolResult objects
                        run_ctx.outputs["output"] = str(result.output)
                        if hasattr(result, 'error') and result.error:
                            run_ctx.outputs["error"] = result.error
                            run_ctx.metadata["has_error"] = True
                    else:
                        run_ctx.outputs["result"] = str(result)
                
                return result
            
            except Exception as e:
                run_ctx.fail(str(e), type(e).__name__)
                raise

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
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
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
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
