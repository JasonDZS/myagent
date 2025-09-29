"""Simple demo agent for API testing."""

from myagent import create_react_agent
from myagent.tool import BaseTool, ToolResult


class DemoTool(BaseTool):
    """Simple demo tool."""
    
    name: str = "demo"
    description: str = "A demo tool for testing"
    
    async def execute(self, text: str = "Hello") -> ToolResult:
        return ToolResult(
            success=True,
            content=f"Demo tool executed: {text}",
            metadata={"input": text, "timestamp": "2025-09-28T18:30:00Z"}
        )


def create_agent():
    """Create demo agent."""
    return create_react_agent(
        name="api-demo-agent",
        tools=[DemoTool()],
        system_prompt="You are a demo agent for API testing.",
    )
