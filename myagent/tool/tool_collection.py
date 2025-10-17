"""Collection classes for managing multiple tools."""

from typing import Any

from ..exceptions import ToolError
from ..logger import logger
from ..stats import get_stats_manager
from .base_tool import BaseTool
from .base_tool import ToolFailure
from .base_tool import ToolResult


class ToolCollection:
    """A collection of defined tools."""

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, *tools: BaseTool):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    def __iter__(self):
        return iter(self.tools)

    def to_params(self) -> list[dict[str, Any]]:
        return [tool.to_param() for tool in self.tools]

    async def execute(
        self, *, name: str, tool_input: dict[str, Any] | None = None
    ) -> ToolResult:
        tool = self.tool_map.get(name)
        if not tool:
            return ToolFailure(error=f"Tool {name} is invalid")
        stats = get_stats_manager()
        run_id = None
        try:
            # Record tool call start
            run_id = stats.start_tool_run(name, args=tool_input or {})
        except Exception:
            run_id = None

        try:
            result = await tool(**(tool_input or {}))

            # Determine success based on ToolResult
            is_success = not (
                hasattr(result, "error") and getattr(result, "error") is not None
            ) and result.__class__.__name__ != "ToolFailure"

            # Record tool call end
            try:
                if run_id:
                    output_size = None
                    try:
                        output = getattr(result, "output", None)
                        output_size = len(str(output)) if output is not None else None
                    except Exception:
                        output_size = None
                    stats.finish_tool_run(
                        run_id=run_id,
                        success=bool(is_success),
                        output_size=output_size,
                        error=(getattr(result, "error", None) if not is_success else None),
                    )
            except Exception:
                pass

            return result
        except ToolError as e:
            # Record tool failure
            try:
                if run_id:
                    stats.finish_tool_run(
                        run_id=run_id, success=False, output_size=None, error=e.message
                    )
            except Exception:
                pass
            return ToolFailure(error=e.message)
        except Exception as e:  # unexpected error path
            try:
                if run_id:
                    stats.finish_tool_run(
                        run_id=run_id, success=False, output_size=None, error=str(e)
                    )
            except Exception:
                pass
            raise

    async def execute_all(self) -> list[ToolResult]:
        """Execute all tools in the collection sequentially."""
        results = []
        for tool in self.tools:
            try:
                result = await tool()
                results.append(result)
            except ToolError as e:
                results.append(ToolFailure(error=e.message))
        return results

    def get_tool(self, name: str) -> BaseTool:
        return self.tool_map.get(name)

    def add_tool(self, tool: BaseTool):
        """Add a single tool to the collection.

        If a tool with the same name already exists, it will be skipped and a warning will be logged.
        """
        if tool.name in self.tool_map:
            logger.warning(f"Tool {tool.name} already exists in collection, skipping")
            return self

        self.tools += (tool,)
        self.tool_map[tool.name] = tool
        return self

    def add_tools(self, *tools: BaseTool):
        """Add multiple tools to the collection.

        If any tool has a name conflict with an existing tool, it will be skipped and a warning will be logged.
        """
        for tool in tools:
            self.add_tool(tool)
        return self
