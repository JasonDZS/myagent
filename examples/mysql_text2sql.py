"""MySQL Text-to-SQL example for myagent with trace recording."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pydantic import Field

import pymysql
from pymysql.cursors import DictCursor

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.trace import (
    TraceManager,
    TraceQueryEngine,
    TraceExporter,
    TraceMetadata,
    get_trace_manager
)


REQUIRED_ENV_VARS = (
    "MYSQL_HOST",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
)


@dataclass
class MySQLConfig:
    host: str
    user: str
    password: str
    database: str
    port: int = 3306
    charset: str = "utf8mb4"


def _load_mysql_config() -> MySQLConfig:
    missing = [var for var in REQUIRED_ENV_VARS if not os.environ.get(var)]
    if missing:
        raise RuntimeError(
            "Missing required MySQL environment variables: " + ", ".join(missing)
        )

    port = int(os.environ.get("MYSQL_PORT", "3306"))

    return MySQLConfig(
        host=os.environ["MYSQL_HOST"],
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        port=port,
        charset=os.environ.get("MYSQL_CHARSET", "utf8mb4"),
    )


def _connect(config: MySQLConfig) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=config.host,
        user=config.user,
        password=config.password,
        database=config.database,
        port=config.port,
        charset=config.charset,
        autocommit=True,
        cursorclass=DictCursor,
    )


def _ensure_read_only(sql: str) -> Optional[str]:
    normalized = sql.strip().lower()
    disallowed_pattern = re.compile(
        r"(?<![a-z0-9_])(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke|call|merge|handler|load|rename|lock|unlock)(?![a-z0-9_])"
    )
    if ";" in sql:
        return "Multiple statements are not allowed; remove any ';' characters."
    if " for update" in normalized or " for share" in normalized:
        return "Row locking clauses like FOR UPDATE/SHARE are not permitted."
    match = disallowed_pattern.search(normalized)
    if match:
        return f"Disallowed keyword detected: '{match.group(1)}'. Only read-only queries are permitted."
    return None


def _format_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    total_rows: Optional[int] = None,
    truncated: bool = False,
) -> str:
    if not rows:
        return "No rows returned."

    stringified: List[List[str]] = []
    for row in rows:
        stringified.append(["NULL" if value is None else str(value) for value in row])

    widths = [len(header) for header in headers]
    for row in stringified:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def _format_line(values: Iterable[str]) -> str:
        return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values))

    header_line = _format_line(headers)
    separator_line = "-+-".join("-" * width for width in widths)
    row_lines = [_format_line(row) for row in stringified]

    footer_parts: List[str] = []
    if total_rows is not None:
        footer_parts.append(f"rows={total_rows}")
    if truncated:
        footer_parts.append("results truncated")

    footer = f"\n({' | '.join(footer_parts)})" if footer_parts else ""
    return "\n".join([header_line, separator_line, *row_lines]) + footer


class MySQLSchemaTool(BaseTool):
    name: str = "mysql_schema"
    description: str = "Inspect table structure from the connected MySQL database."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Optional table name. When omitted, returns the list of tables in the current database.",
            }
        },
    }

    async def execute(self, table: Optional[str] = None) -> ToolResult:
        config = _load_mysql_config()

        def _inspect_schema() -> str:
            with closing(_connect(config)) as connection, closing(connection.cursor()) as cursor:
                if not table:
                    cursor.execute("SHOW TABLES")
                    tables = [next(iter(row.values())) for row in cursor.fetchall()]
                    return (
                        "Available tables:\n" + "\n".join(f"- {name}" for name in tables)
                        if tables
                        else "No tables found in the current database."
                    )

                cursor.execute(
                    """
                    SELECT column_name, data_type, is_nullable, column_key, column_type, column_comment
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (config.database, table),
                )
                columns = cursor.fetchall()
                if not columns:
                    return f"Table '{table}' does not exist in database '{config.database}'."

                lines = [f"Columns for {table}:"]
                for col in columns:
                    nullable = "NULLABLE" if col["is_nullable"] == "YES" else "NOT NULL"
                    key = f" {col['column_key']}" if col["column_key"] else ""
                    comment = f" -- {col['column_comment']}" if col["column_comment"] else ""
                    lines.append(
                        f"- {col['column_name']} ({col['column_type']} {nullable}{key}){comment}"
                    )
                return "\n".join(lines)

        try:
            result = await asyncio.to_thread(_inspect_schema)
            return ToolResult(
                output=result,
                system=f"Schema inspection completed for {'table: ' + table if table else 'all tables'}"
            )
        except Exception as exc:  # pragma: no cover - depends on external DB
            return ToolResult(error=f"Schema inspection failed: {exc}")


class MySQLQueryTool(BaseTool):
    name: str = "mysql_query"
    description: str = "Execute a read-only SQL query against the MySQL database and return the results."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Complete SQL statement. Must be a single read-only query (SELECT/SHOW/DESCRIBE/EXPLAIN).",
            },
            "max_rows": {
                "type": "integer",
                "description": "Maximum number of rows to return.",
                "default": 20,
                "minimum": 1,
                "maximum": 200,
            },
        },
        "required": ["sql"],
    }
    last_sql: Optional[str] = Field(default=None, exclude=True)
    executed_sql: List[str] = Field(default_factory=list, exclude=True)
    output_char_limit: int = Field(default=2000, exclude=True)

    async def execute(self, sql: str, max_rows: int = 20) -> ToolResult:
        stripped_sql = sql.strip().rstrip(";")
        lowered = stripped_sql.lstrip().lower()
        allowed_prefixes = ("select", "show", "describe", "explain", "with")
        if not lowered.startswith(allowed_prefixes):
            return ToolResult(
                error="Only read-only queries are permitted. Begin with SELECT, SHOW, DESCRIBE, EXPLAIN, or WITH."
            )

        read_only_error = _ensure_read_only(stripped_sql)
        if read_only_error:
            return ToolResult(error=read_only_error)

        config = _load_mysql_config()

        def _run_query() -> str:
            with closing(_connect(config)) as connection, closing(connection.cursor()) as cursor:
                cursor.execute(stripped_sql)
                rows = cursor.fetchmany(size=max_rows)
                total_rows = cursor.rowcount if cursor.rowcount != -1 else None
                headers = [col[0] for col in cursor.description] if cursor.description else []

            data_rows: List[Sequence[Any]] = [tuple(row.values()) for row in rows]
            truncated = len(data_rows) == max_rows and (total_rows is None or total_rows > max_rows)
            return _format_table(headers, data_rows, total_rows=total_rows, truncated=truncated)

        try:
            result = await asyncio.to_thread(_run_query)
        except Exception as exc:  # pragma: no cover - depends on external DB
            return ToolResult(error=f"Query failed: {exc}")

        self.last_sql = stripped_sql
        self.executed_sql.append(stripped_sql)
        
        if len(result) > self.output_char_limit:
            truncated_result = (
                result[: self.output_char_limit]
                + "\n... (truncated output to protect context length)"
            )
            return ToolResult(
                output=truncated_result,
                system=f"Query executed successfully with {max_rows} max rows (output truncated)"
            )
        
        return ToolResult(
            output=result,
            system=f"Query executed successfully: {stripped_sql[:100]}{'...' if len(stripped_sql) > 100 else ''}"
        )


class MySQLValidateSQLTool(BaseTool):
    name: str = "mysql_validate_sql"
    description: str = "Validate the final SQL without fetching full results. Records the last approved SQL."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Final read-only SQL statement to validate (SELECT/CTE).",
            }
        },
        "required": ["sql"],
    }
    final_sql: Optional[str] = Field(default=None, exclude=True)

    async def execute(self, sql: str) -> ToolResult:
        stripped_sql = sql.strip().rstrip(";")
        lowered = stripped_sql.lstrip().lower()
        allowed_prefixes = ("select", "with")
        if not lowered.startswith(allowed_prefixes):
            return ToolResult(error="Final SQL must begin with SELECT or WITH.")

        read_only_error = _ensure_read_only(stripped_sql)
        if read_only_error:
            return ToolResult(error=read_only_error)

        config = _load_mysql_config()

        def _validate() -> str:
            with closing(_connect(config)) as connection, closing(connection.cursor()) as cursor:
                cursor.execute(f"EXPLAIN {stripped_sql}")
                plan_rows = cursor.fetchall()
                headers = [col[0] for col in cursor.description] if cursor.description else []

            formatted = _format_table(headers, [tuple(row.values()) for row in plan_rows])
            return formatted or "EXPLAIN returned no plan."

        try:
            explain_output = await asyncio.to_thread(_validate)
        except Exception as exc:  # pragma: no cover - depends on external DB
            return ToolResult(error=f"Validation failed: {exc}")

        self.final_sql = stripped_sql
        if len(explain_output) > 1200:
            explain_output = (
                explain_output[:1200]
                + "\n... (EXPLAIN output truncated to protect context length)"
            )
        
        return ToolResult(
            output="EXPLAIN succeeded. Execution plan:\n" + explain_output,
            system=f"SQL validation completed for: {stripped_sql[:100]}{'...' if len(stripped_sql) > 100 else ''}"
        )


async def main() -> None:
    parser = argparse.ArgumentParser(description="MySQL Text-to-SQL agent example with trace recording")
    parser.add_argument(
        "question",
        nargs="?",
        default="显示用户表的10条用户数据",
        help="Natural-language question to answer with SQL.",
    )
    args = parser.parse_args()

    # Setup trace manager with metadata
    metadata = TraceMetadata(
        user_id="mysql_text2sql_user",
        session_id=f"mysql_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        tags=["mysql", "text2sql", "database_query"],
        environment="example",
        custom_fields={
            "example_type": "mysql_text2sql",
            "database_type": "mysql",
            "question": args.question
        }
    )

    schema_tool = MySQLSchemaTool()
    query_tool = MySQLQueryTool()
    validate_tool = MySQLValidateSQLTool()

    agent = create_react_agent(
        name="mysql-text2sql",
        tools=[schema_tool, query_tool, validate_tool],
        system_prompt=(
            "You are a MySQL expert that translates natural language questions into SQL. "
            "Always inspect the schema first with mysql_schema if structure details are unclear. "
            "Use mysql_query for lightweight exploratory reads and keep outputs concise. "
            "When you have the final answer query, validate it with mysql_validate_sql to record it instead of fetching full results. "
            "After validation, summarize the findings and cite the final SQL in your reply."
        ),
        next_step_prompt=(
            "Call mysql_schema for structure, mysql_query for small exploratory checks, "
            "and mysql_validate_sql to finalize the SQL answer without retrieving large result sets."
        ),
        max_steps=8,
        enable_tracing=True,
        trace_metadata=metadata
    )

    print(f"🔍 Starting MySQL Text-to-SQL with trace recording...")
    print(f"Question: {args.question}")
    
    result = await agent.run(args.question)
    print("\n✅ Agent execution completed:")
    print(result)

    if query_tool.executed_sql:
        print("\n📝 Exploration SQL history:")
        for idx, statement in enumerate(query_tool.executed_sql, start=1):
            print(f"- [{idx}] {statement}")

    if validate_tool.final_sql:
        print("\n✅ Validated final SQL:")
        print(validate_tool.final_sql)
    else:
        print("\n⚠️ No final SQL was validated. Ensure the agent calls mysql_validate_sql once satisfied.")

    print("\n📊 Final response:")
    print(agent.final_response)
    
    # Save trace data to JSON
    await save_traces_to_json("mysql_text2sql_traces.json", args.question)


async def save_traces_to_json(filename: str, question: str) -> None:
    """Save all traces to a JSON file."""
    print(f"\n💾 Saving trace data to {filename}...")
    
    trace_manager = get_trace_manager()
    query_engine = TraceQueryEngine(trace_manager.storage)
    exporter = TraceExporter(query_engine)
    
    # Export traces to JSON
    json_data = await exporter.export_traces_to_json()
    
    # Save to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(json_data)
    
    # Get statistics
    stats = await query_engine.get_trace_statistics()
    
    print(f"✅ Saved trace data to {filename}")
    print(f"📊 Trace Statistics:")
    print(f"  - Total traces: {stats['total_traces']}")
    print(f"  - Average duration: {stats['avg_duration_ms']:.2f}ms")
    print(f"  - Error rate: {stats['error_rate']:.2%}")
    
    # Also save a summary report
    summary_filename = filename.replace('.json', '_summary.md')
    summary = await exporter.export_trace_summary()
    with open(summary_filename, 'w', encoding='utf-8') as f:
        f.write(f"# MySQL Text-to-SQL Trace Summary\n\n")
        f.write(f"**Question:** {question}\n\n")
        f.write(summary)
    print(f"📋 Summary report saved to {summary_filename}")
    
    # Save detailed tree view for the latest trace if available
    traces = await query_engine.query_traces()
    if traces.results:
        latest_trace = traces.results[0]
        tree_filename = filename.replace('.json', '_tree.txt')
        tree = exporter.export_trace_tree(latest_trace)
        with open(tree_filename, 'w', encoding='utf-8') as f:
            f.write(f"MySQL Text-to-SQL Execution Tree\n")
            f.write(f"Question: {question}\n")
            f.write("=" * 50 + "\n\n")
            f.write(tree)
        print(f"🌳 Execution tree saved to {tree_filename}")


if __name__ == "__main__":
    asyncio.run(main())
