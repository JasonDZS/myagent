"""WebSocket agent with user confirmation demo."""

import asyncio
import os
from typing import Any, Dict

from myagent import create_react_agent, logger
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.ws.server import AgentWebSocketServer


class DangerousTool(BaseTool):
    """A tool that requires user confirmation before execution."""
    
    name: str = "dangerous_operation"
    description: str = "Perform a dangerous operation that requires user confirmation"
    user_confirm: bool = True  # This tool requires user confirmation
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "The dangerous operation to perform",
            },
            "target": {
                "type": "string", 
                "description": "The target of the operation",
            },
        },
        "required": ["operation", "target"],
    }
    
    async def execute(self, operation: str, target: str) -> ToolResult:
        """Execute the dangerous operation."""
        result = f"Successfully executed '{operation}' on '{target}'"
        logger.info(f"DangerousTool executed: {result}")
        return ToolResult(output=result)


class SafeTool(BaseTool):
    """A tool that doesn't require user confirmation."""
    
    name: str = "safe_operation"
    description: str = "Perform a safe operation"
    user_confirm: bool = False  # This tool doesn't need confirmation
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "A safe message to display",
            },
        },
        "required": ["message"],
    }
    
    async def execute(self, message: str) -> ToolResult:
        """Execute the safe operation."""
        result = f"Safe operation: {message}"
        logger.info(f"SafeTool executed: {result}")
        return ToolResult(output=result)


def create_confirmation_agent():
    """Create an agent with tools that require confirmation."""
    tools = [
        DangerousTool(),
        SafeTool(),
    ]
    
    llm_config = {
        "model": "gpt-4",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_API_BASE"),
        "temperature": 0.7
    }
    
    return create_react_agent(tools, llm_config=llm_config)


async def main():
    """Run the WebSocket server with confirmation demo."""
    server = AgentWebSocketServer(
        agent_factory_func=create_confirmation_agent,
        host="localhost", 
        port=8890
    )
    
    logger.info("Starting WebSocket server with user confirmation demo on ws://localhost:8890")
    logger.info("Tools available:")
    logger.info("  - dangerous_operation (requires confirmation)")
    logger.info("  - safe_operation (no confirmation needed)")
    logger.info("\nExample messages to test:")
    logger.info("  - 'Please perform a safe operation with message hello world'")
    logger.info("  - 'Delete the important_file.txt file' (will require confirmation)")
    
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())