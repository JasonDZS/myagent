"""Fixed WebSocket agent with user confirmation demo."""

import asyncio
import os
from typing import Any, Dict

from myagent import create_react_agent, logger
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.ws.server import AgentWebSocketServer


class MySQLQueryTool(BaseTool):
    """MySQL query tool that requires user confirmation."""
    
    name: str = "mysql_query"
    description: str = "Execute a read-only SQL query against the MySQL database and return the results."
    user_confirm: bool = True  # This tool requires user confirmation
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "SQL query to execute",
            },
            "max_rows": {
                "type": "integer", 
                "description": "Maximum rows to return",
                "default": 10
            },
        },
        "required": ["sql"],
    }
    
    async def execute(self, sql: str, max_rows: int = 10) -> ToolResult:
        """Execute the SQL query."""
        # Simulate database query execution
        result = f"Query executed: {sql}\nReturned {max_rows} rows (simulated)"
        logger.info(f"MySQLQueryTool executed: {sql}")
        return ToolResult(output=result)


class SafeInfoTool(BaseTool):
    """A safe tool that doesn't require confirmation."""
    
    name: str = "get_info"
    description: str = "Get safe information"
    user_confirm: bool = False  # This tool doesn't need confirmation
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "Topic to get information about",
            },
        },
        "required": ["topic"],
    }
    
    async def execute(self, topic: str) -> ToolResult:
        """Get safe information."""
        result = f"Information about {topic}: This is safe, no confirmation needed."
        logger.info(f"SafeInfoTool executed: {topic}")
        return ToolResult(output=result)


def create_fixed_agent():
    """Create an agent with fixed confirmation tools."""
    tools = [
        MySQLQueryTool(),
        SafeInfoTool(),
    ]
    
    llm_config = {
        "model": "gpt-4",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_API_BASE"),
        "temperature": 0.7
    }
    
    return create_react_agent(tools, llm_config=llm_config)


async def main():
    """Run the fixed WebSocket server."""
    server = AgentWebSocketServer(
        agent_factory_func=create_fixed_agent,
        host="localhost", 
        port=8892
    )
    
    logger.info("Starting FIXED WebSocket server on ws://localhost:8892")
    logger.info("Tools available:")
    logger.info("  - mysql_query (requires confirmation)")
    logger.info("  - get_info (no confirmation needed)")
    logger.info("\nTest messages:")
    logger.info("  - 'Get information about weather'")
    logger.info("  - 'Execute SQL: SELECT Id, Name FROM userid WHERE Name LIKE \"%Jason%\"'")
    
    await server.start_server()


if __name__ == "__main__":
    asyncio.run(main())