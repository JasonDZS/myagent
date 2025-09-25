#!/usr/bin/env python3
"""
Independent Agent Runner

This module provides a standalone agent execution environment that communicates
with the WebSocket server through a message-based interface, achieving loose coupling.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, Optional
from contextlib import closing
from dataclasses import dataclass

# Add parent directory to path for myagent imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from myagent import create_react_agent
from myagent.trace import TraceMetadata, set_trace_manager
from myagent.tool.base_tool import BaseTool, ToolResult

import pymysql
from pymysql.cursors import DictCursor

# Import message bridge for loose coupling
from message_bridge import MessageBridge


# MySQL configuration
@dataclass
class MySQLConfig:
    host: str
    user: str
    password: str
    database: str
    port: int = 3306
    charset: str = "utf8mb4"


def _load_mysql_config() -> MySQLConfig:
    """Load MySQL configuration from environment variables"""
    return MySQLConfig(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "test"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4")
    )


def _connect(config: MySQLConfig) -> pymysql.connections.Connection:
    """Create MySQL connection"""
    return pymysql.connect(
        host=config.host,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        charset=config.charset,
        cursorclass=DictCursor,
    )


# MySQL Tools - Extracted from server
class MySQLSchemaTool(BaseTool):
    name: str = "mysql_schema"
    description: str = "Inspect MySQL table structure"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Optional table name to inspect. If not provided, lists all tables."
            }
        }
    }

    async def execute(self, table: Optional[str] = None) -> ToolResult:
        """Execute schema inspection"""
        try:
            def _inspect_schema() -> str:
                config = _load_mysql_config()
                with closing(_connect(config)) as conn:
                    with conn.cursor() as cursor:
                        if table:
                            # Describe specific table
                            cursor.execute("DESCRIBE %s" % table)
                            columns = cursor.fetchall()
                            if not columns:
                                return f"Table '{table}' not found."
                            
                            result = f"Table: {table}\n"
                            result += "-" * 40 + "\n"
                            for col in columns:
                                result += f"Column: {col['Field']}\n"
                                result += f"  Type: {col['Type']}\n"
                                result += f"  Null: {col['Null']}\n"
                                result += f"  Key: {col['Key']}\n"
                                result += f"  Default: {col['Default']}\n"
                                result += f"  Extra: {col['Extra']}\n\n"
                            return result
                        else:
                            # List all tables
                            cursor.execute("SHOW TABLES")
                            tables = cursor.fetchall()
                            if not tables:
                                return "No tables found in database."
                            
                            table_names = [list(t.values())[0] for t in tables]
                            return f"Available tables: {', '.join(table_names)}"

            return ToolResult(result=_inspect_schema())
            
        except Exception as e:
            return ToolResult(error=f"Schema inspection failed: {e}")


class MySQLQueryTool(BaseTool):
    name: str = "mysql_query"
    description: str = "Execute read-only SQL queries"
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "SQL query to execute (SELECT statements only)"},
            "max_rows": {"type": "integer", "default": 20, "description": "Maximum rows to return"}
        },
        "required": ["sql"]
    }

    async def execute(self, sql: str, max_rows: int = 20) -> ToolResult:
        """Execute SQL query"""
        try:
            # Basic safety check - only allow SELECT statements
            sql_trimmed = sql.strip().upper()
            if not sql_trimmed.startswith('SELECT'):
                return ToolResult(error="Only SELECT statements are allowed")

            def _run_query() -> str:
                config = _load_mysql_config()
                with closing(_connect(config)) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(sql)
                        results = cursor.fetchall()
                        
                        if not results:
                            return "Query executed successfully, but returned no results."
                        
                        # Limit results
                        limited_results = results[:max_rows]
                        
                        # Format results as table
                        if limited_results:
                            headers = list(limited_results[0].keys())
                            result = "Query Results:\n"
                            result += "-" * 80 + "\n"
                            
                            # Header
                            result += " | ".join(f"{h:15}" for h in headers) + "\n"
                            result += "-" * 80 + "\n"
                            
                            # Rows
                            for row in limited_results:
                                values = [str(row[h])[:15] for h in headers]
                                result += " | ".join(f"{v:15}" for v in values) + "\n"
                            
                            if len(results) > max_rows:
                                result += f"\n... and {len(results) - max_rows} more rows"
                            
                            return result
                        
                        return "No results returned"

            return ToolResult(result=_run_query())
            
        except Exception as e:
            return ToolResult(error=f"Query execution failed: {e}")


# Import message bridge for loose coupling
from message_bridge import MessageBridge


class StandaloneAgentRunner:
    """Standalone agent runner with message bridge communication"""
    
    def __init__(self, websocket_url: str = "ws://localhost:8234/ws", session_id: str = None):
        self.websocket_url = websocket_url
        self.session_id = session_id or f"agent_{int(asyncio.get_event_loop().time())}"
        self.message_bridge = None
    
    async def run_agent(self, question: str, agent_config: Dict[str, Any] = None) -> str:
        """Run agent with given question"""
        agent_config = agent_config or {}
        
        # Setup message bridge communication
        self.message_bridge = MessageBridge(self.websocket_url, self.session_id)
        await self.message_bridge.start()
        
        try:
            # Create MySQL tools
            schema_tool = MySQLSchemaTool()
            query_tool = MySQLQueryTool()
            
            # Create trace metadata
            metadata = TraceMetadata(
                agent_name="standalone-mysql-agent",
                request=question,
                max_steps=agent_config.get("max_steps", 10),
                metadata={
                    "session_id": self.session_id,
                    "standalone_mode": True,
                    "mysql_host": os.getenv("MYSQL_HOST", "localhost"),
                    "mysql_database": os.getenv("MYSQL_DATABASE", "test")
                }
            )
            
            # Create agent
            agent = create_react_agent(
                name="standalone-mysql-agent",
                tools=[schema_tool, query_tool],
                system_prompt=(
                    "You are a MySQL database assistant. Help users query and analyze database information. "
                    "Always use the mysql_schema tool first to understand table structure, "
                    "then use mysql_query tool to fetch data. "
                    "Be precise and helpful in your analysis."
                ),
                max_steps=agent_config.get("max_steps", 10)
            )
            
            # Setup WebSocket trace manager if available
            try:
                from myagent_ws.websocket_trace_server import WebSocketTraceManager
                # This would need to be adapted for standalone mode
                # For now, we'll use standard trace manager
                pass
            except ImportError:
                pass
            
            # Run agent
            print(f"🤖 Starting agent: {question}")
            
            # Send trace started event via message bridge
            await self.message_bridge.send_agent_message("trace_started", {
                "agent_name": "standalone-mysql-agent",
                "request": question,
                "max_steps": agent_config.get("max_steps", 10)
            })
            
            # Execute agent
            result = await agent.run(question)
            
            print(f"✅ Agent completed: {result[:100]}...")
            
            # Send trace completed event via message bridge
            await self.message_bridge.send_agent_message("trace_completed", {
                "final_response": result,
                "status": "completed"
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Agent execution failed: {e}"
            print(f"❌ {error_msg}")
            
            # Send error event via message bridge
            await self.message_bridge.send_agent_message("trace_completed", {
                "final_response": error_msg,
                "status": "error",
                "error": str(e)
            })
            
            return error_msg
            
        finally:
            # Cleanup
            if self.message_bridge:
                await self.message_bridge.stop()


async def main():
    """Main entry point for standalone agent runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Standalone MySQL Agent Runner")
    parser.add_argument("--question", "-q", default="显示用户表的10条用户数据", 
                       help="Question for the agent")
    parser.add_argument("--websocket-url", "-w", default="ws://localhost:8234/ws",
                       help="WebSocket server URL")
    parser.add_argument("--session-id", "-s", help="Session ID for WebSocket")
    parser.add_argument("--max-steps", "-m", type=int, default=10,
                       help="Maximum steps for agent execution")
    
    args = parser.parse_args()
    
    print("🚀 Starting Standalone MySQL Agent Runner")
    print(f"📝 Question: {args.question}")
    print(f"🔌 WebSocket URL: {args.websocket_url}")
    print(f"🆔 Session ID: {args.session_id or 'auto-generated'}")
    print("-" * 50)
    
    # Create and run agent
    runner = StandaloneAgentRunner(
        websocket_url=args.websocket_url,
        session_id=args.session_id
    )
    
    agent_config = {
        "max_steps": args.max_steps
    }
    
    result = await runner.run_agent(args.question, agent_config)
    
    print("\n" + "="*50)
    print("🎯 Final Result:")
    print(result)
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())