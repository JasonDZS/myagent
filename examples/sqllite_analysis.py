"""Generic Database Text-to-SQL example for myagent with trace recording.
Supports both MySQL and SQLite databases."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
from collections.abc import Iterable
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from typing import Any
from typing import ClassVar

import sqlite3
from enum import Enum
from typing import Union

import pymysql
from pydantic import Field
from pymysql.cursors import DictCursor

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool
from myagent.tool.base_tool import ToolResult
from myagent.trace import TraceExporter
from myagent.trace import TraceQueryEngine
from myagent.trace import get_trace_manager

class DatabaseType(str, Enum):
    MYSQL = "mysql"
    SQLITE = "sqlite"

REQUIRED_MYSQL_ENV_VARS = (
    "MYSQL_HOST",
    "MYSQL_USER", 
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
)

REQUIRED_SQLITE_ENV_VARS = (
    "SQLITE_DATABASE",
)

class ToolResultExpanded(ToolResult):
    data: Any | None = None  # Additional structured data, e.g. for visualizations


@dataclass
class DatabaseConfig:
    db_type: DatabaseType
    database: str
    # MySQL specific
    host: str | None = None
    user: str | None = None
    password: str | None = None
    port: int = 3306
    charset: str = "utf8mb4"


def _load_database_config() -> DatabaseConfig:
    db_type = DatabaseType(os.environ.get("DB_TYPE", "sqlite").lower())
    
    if db_type == DatabaseType.MYSQL:
        missing = [var for var in REQUIRED_MYSQL_ENV_VARS if not os.environ.get(var)]
        if missing:
            raise RuntimeError(
                "Missing required MySQL environment variables: " + ", ".join(missing)
            )
        
        port = int(os.environ.get("MYSQL_PORT", "3306"))
        
        return DatabaseConfig(
            db_type=db_type,
            host=os.environ["MYSQL_HOST"],
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            database=os.environ["MYSQL_DATABASE"],
            port=port,
            charset=os.environ.get("MYSQL_CHARSET", "utf8mb4"),
        )
    elif db_type == DatabaseType.SQLITE:
        missing = [var for var in REQUIRED_SQLITE_ENV_VARS if not os.environ.get(var)]
        if missing:
            raise RuntimeError(
                "Missing required SQLite environment variables: " + ", ".join(missing)
            )
        
        return DatabaseConfig(
            db_type=db_type,
            database=os.environ["SQLITE_DATABASE"],
        )
    else:
        raise RuntimeError(f"Unsupported database type: {db_type}")


def _connect(config: DatabaseConfig) -> Union[pymysql.connections.Connection, sqlite3.Connection]:
    if config.db_type == DatabaseType.MYSQL:
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
    elif config.db_type == DatabaseType.SQLITE:
        conn = sqlite3.connect(config.database)
        conn.row_factory = sqlite3.Row  # Enable dict-like row access
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        return conn
    else:
        raise RuntimeError(f"Unsupported database type: {config.db_type}")


def _ensure_read_only(sql: str) -> str | None:
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
    total_rows: int | None = None,
    truncated: bool = False,
) -> str:
    if not rows:
        return "No rows returned."

    stringified: list[list[str]] = [
        ["NULL" if value is None else str(value) for value in row] for row in rows
    ]

    widths = [len(header) for header in headers]
    for row in stringified:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def _format_line(values: Iterable[str]) -> str:
        return " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(values))

    header_line = _format_line(headers)
    separator_line = "-+-".join("-" * width for width in widths)
    row_lines = [_format_line(row) for row in stringified]

    footer_parts: list[str] = []
    if total_rows is not None:
        footer_parts.append(f"rows={total_rows}")
    if truncated:
        footer_parts.append("results truncated")

    footer = f"\n({' | '.join(footer_parts)})" if footer_parts else ""
    return "\n".join([header_line, separator_line, *row_lines]) + footer


class DatabaseSchemaTool(BaseTool):
    name: str = "db_schema"
    description: str = "Inspect table structure from the connected database (MySQL or SQLite)."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "table": {
                "type": "string",
                "description": "Optional table name. When omitted, returns the list of tables in the current database.",
            }
        },
    }

    async def execute(self, table: str | None = None) -> ToolResult:
        config = _load_database_config()

        def _inspect_schema() -> str:
            try:
                with closing(_connect(config)) as connection:
                    if config.db_type == DatabaseType.MYSQL:
                        with closing(connection.cursor()) as cursor:
                            if not table:
                                cursor.execute("SHOW TABLES")
                                tables = [next(iter(row.values())) for row in cursor.fetchall()]
                                return (
                                    "Available tables:\n"
                                    + "\n".join(f"- {name}" for name in tables)
                                    if tables
                                    else "No tables found in the current database."
                                )

                            print(f"Querying table: {table} in database: {config.database}")
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
                            print(f"Found {len(columns)} columns")

                            if not columns:
                                return f"Table '{table}' does not exist in database '{config.database}'."

                            lines = [f"Columns for {table}:"]
                            for idx, col in enumerate(columns):
                                if idx == 0:
                                    print(f"Column keys available: {list(col.keys())}")

                                column_name = col.get("column_name") or col.get("COLUMN_NAME", "unknown")
                                column_type = col.get("column_type") or col.get("COLUMN_TYPE", "unknown")
                                is_nullable = col.get("is_nullable") or col.get("IS_NULLABLE", "unknown")
                                column_key = col.get("column_key") or col.get("COLUMN_KEY", "")
                                column_comment = col.get("column_comment") or col.get("COLUMN_COMMENT", "")

                                nullable = "NULLABLE" if is_nullable == "YES" else "NOT NULL"
                                key = f" {column_key}" if column_key else ""
                                comment = f" -- {column_comment}" if column_comment else ""
                                lines.append(f"- {column_name} ({column_type} {nullable}{key}){comment}")
                            
                            result = "\n".join(lines)
                            print(f"Returning result length: {len(result)}")
                            return result
                    
                    elif config.db_type == DatabaseType.SQLITE:
                        cursor = connection.cursor()
                        if not table:
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                            tables = [row[0] for row in cursor.fetchall()]
                            return (
                                "Available tables:\n"
                                + "\n".join(f"- {name}" for name in tables)
                                if tables
                                else "No tables found in the current database."
                            )

                        print(f"Querying table: {table} in SQLite database")
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = cursor.fetchall()
                        print(f"Found {len(columns)} columns")

                        if not columns:
                            return f"Table '{table}' does not exist in the database."

                        lines = [f"Columns for {table}:"]
                        for col in columns:
                            # SQLite PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
                            column_name = col[1]
                            column_type = col[2]
                            not_null = col[3]
                            is_pk = col[5]
                            
                            nullable = "NOT NULL" if not_null else "NULLABLE"
                            key = " PRIMARY KEY" if is_pk else ""
                            lines.append(f"- {column_name} ({column_type} {nullable}{key})")
                        
                        result = "\n".join(lines)
                        print(f"Returning result length: {len(result)}")
                        return result
                        
            except Exception as e:
                error_msg = f"Database connection or query error: {e}"
                print(f"Error in _inspect_schema: {error_msg}")
                return error_msg

        try:
            result = await asyncio.to_thread(_inspect_schema)
            print(f"Final result from _inspect_schema: {result!r}")

            if result is None:
                return ToolResult(
                    error="Schema inspection returned None - unexpected result"
                )

            return ToolResult(
                output=result,
                system=f"Schema inspection completed for {'table: ' + table if table else 'all tables'}",
            )
        except Exception as exc:  # pragma: no cover - depends on external DB
            import traceback

            error_detail = (
                f"Schema inspection failed: {exc}\nTraceback: {traceback.format_exc()}"
            )
            print(f"Exception in execute: {error_detail}")
            return ToolResult(error=error_detail)


class DatabaseQueryTool(BaseTool):
    name: str = "db_query"
    description: str = "Execute a read-only SQL query against the database (MySQL or SQLite) and return the results."
    parameters: ClassVar[dict[str, Any]] = {
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
    last_sql: str | None = Field(default=None, exclude=True)
    executed_sql: list[str] = Field(default_factory=list, exclude=True)
    output_char_limit: int = Field(default=2000, exclude=True)
    user_confirm: bool = Field(default=True, exclude=True)

    async def execute(self, sql: str, max_rows: int = 20) -> ToolResult:
        stripped_sql = sql.strip().rstrip(";")
        lowered = stripped_sql.lstrip().lower()
        
        config = _load_database_config()
        
        # Different allowed prefixes for different databases
        if config.db_type == DatabaseType.MYSQL:
            allowed_prefixes = ("select", "show", "describe", "explain", "with")
        else:  # SQLite
            allowed_prefixes = ("select", "explain", "pragma", "with")
            
        if not lowered.startswith(allowed_prefixes):
            if config.db_type == DatabaseType.MYSQL:
                return ToolResult(
                    error="Only read-only queries are permitted. Begin with SELECT, SHOW, DESCRIBE, EXPLAIN, or WITH."
                )
            else:
                return ToolResult(
                    error="Only read-only queries are permitted. Begin with SELECT, EXPLAIN, PRAGMA, or WITH."
                )

        read_only_error = _ensure_read_only(stripped_sql)
        if read_only_error:
            return ToolResult(error=read_only_error)

        def _run_query() -> str:
            with closing(_connect(config)) as connection:
                if config.db_type == DatabaseType.MYSQL:
                    with closing(connection.cursor()) as cursor:
                        cursor.execute(stripped_sql)
                        rows = cursor.fetchmany(size=max_rows)
                        total_rows = cursor.rowcount if cursor.rowcount != -1 else None
                        headers = (
                            [col[0] for col in cursor.description] if cursor.description else []
                        )
                        data_rows: list[Sequence[Any]] = [tuple(row.values()) for row in rows]
                        
                elif config.db_type == DatabaseType.SQLITE:
                    cursor = connection.cursor()
                    cursor.execute(stripped_sql)
                    rows = cursor.fetchmany(size=max_rows)
                    total_rows = len(rows)  # SQLite doesn't provide accurate rowcount for SELECT
                    headers = (
                        [col[0] for col in cursor.description] if cursor.description else []
                    )
                    data_rows: list[Sequence[Any]] = [tuple(row) for row in rows]
                
                truncated = len(data_rows) == max_rows
                return _format_table(
                    headers, data_rows, total_rows=total_rows, truncated=truncated
                )

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
                system=f"Query executed successfully with {max_rows} max rows (output truncated)",
            )

        return ToolResult(
            output=result,
            system=f"Query executed successfully: {stripped_sql[:100]}{'...' if len(stripped_sql) > 100 else ''}",
        )


class DataVisualTool(BaseTool):
    name: str = "data_visual"
    description: str = "Execute SQL query and create data visualization. Supports pie, line, scatter, bar charts with customizable x/y fields."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "SQL SELECT statement to get data for visualization.",
            },
            "chart_type": {
                "type": "string",
                "enum": ["pie", "line", "scatter", "bar"],
                "description": "Type of chart to create: pie, line, scatter, or bar.",
            },
            "x_field": {
                "type": "string",
                "description": "Column name for x-axis (not needed for pie charts).",
            },
            "y_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of column names for y-axis values. For pie charts, use first field as values and x_field as labels.",
            },
            "title": {
                "type": "string",
                "description": "Chart title (optional).",
            }
        },
        "required": ["sql", "chart_type", "y_fields"],
    }

    async def execute(self, sql: str, chart_type: str, y_fields: list[str], x_field: str | None = None, title: str | None = None) -> ToolResultExpanded:
        stripped_sql = sql.strip().rstrip(";")
        lowered = stripped_sql.lstrip().lower()
        
        config = _load_database_config()
        
        # Different allowed prefixes for different databases
        if config.db_type == DatabaseType.MYSQL:
            allowed_prefixes = ("select", "with")
        else:  # SQLite
            allowed_prefixes = ("select", "with")
            
        if not lowered.startswith(allowed_prefixes):
            return ToolResultExpanded(error="Only SELECT or WITH statements are allowed for visualization.")

        read_only_error = _ensure_read_only(stripped_sql)
        if read_only_error:
            return ToolResultExpanded(error=read_only_error)

        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            import pandas as pd
            from datetime import datetime
            import os
        except ImportError as e:
            return ToolResult(error=f"Required visualization libraries not installed: {e}. Please install matplotlib and pandas.")

        def _get_data_and_visualize() -> str:
            with closing(_connect(config)) as connection:
                if config.db_type == DatabaseType.MYSQL:
                    with closing(connection.cursor()) as cursor:
                        cursor.execute(stripped_sql)
                        rows = cursor.fetchall()
                        columns = [col[0] for col in cursor.description] if cursor.description else []
                        data = [dict(row) for row in rows]
                        
                elif config.db_type == DatabaseType.SQLITE:
                    cursor = connection.cursor()
                    cursor.execute(stripped_sql)
                    rows = cursor.fetchall()
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    data = [dict(zip(columns, row)) for row in rows]
                
                if not data:
                    return "No data returned from query."
                
                # Convert to pandas DataFrame
                df = pd.DataFrame(data)
                
                # Validate fields exist
                missing_fields = [field for field in y_fields if field not in df.columns]
                if chart_type != "pie" and x_field and x_field not in df.columns:
                    missing_fields.append(x_field)
                elif chart_type == "pie" and x_field and x_field not in df.columns:
                    missing_fields.append(x_field)
                    
                if missing_fields:
                    return f"Missing fields in query result: {missing_fields}. Available fields: {list(df.columns)}"
                
                # Create visualization
                plt.figure(figsize=(10, 6))
                
                if chart_type == "pie":
                    # For pie chart, use x_field as labels and first y_field as values
                    labels = df[x_field] if x_field else df.index
                    values = df[y_fields[0]]
                    plt.pie(values, labels=labels, autopct='%1.1f%%')
                    
                elif chart_type == "bar":
                    x_data = df[x_field] if x_field else df.index
                    for y_field in y_fields:
                        plt.bar(x_data, df[y_field], label=y_field, alpha=0.7)
                    plt.xlabel(x_field or 'Index')
                    plt.ylabel('Values')
                    if len(y_fields) > 1:
                        plt.legend()
                        
                elif chart_type == "line":
                    x_data = df[x_field] if x_field else df.index
                    for y_field in y_fields:
                        plt.plot(x_data, df[y_field], label=y_field, marker='o')
                    plt.xlabel(x_field or 'Index')
                    plt.ylabel('Values')
                    if len(y_fields) > 1:
                        plt.legend()
                        
                elif chart_type == "scatter":
                    if not x_field:
                        return "Scatter plot requires x_field to be specified."
                    x_data = df[x_field]
                    for y_field in y_fields:
                        plt.scatter(x_data, df[y_field], label=y_field, alpha=0.6)
                    plt.xlabel(x_field)
                    plt.ylabel('Values')
                    if len(y_fields) > 1:
                        plt.legend()
                
                # Set title
                if title:
                    plt.title(title)
                else:
                    plt.title(f'{chart_type.title()} Chart')
                
                # Save to file
                os.makedirs('./workdir/charts', exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'chart_{timestamp}_{chart_type}.png'
                filepath = f'./workdir/charts/{filename}'
                plt.tight_layout()
                plt.savefig(filepath, dpi=300, bbox_inches='tight')
                plt.close()
                
                return (
                    f"Visualization created successfully. Chart saved to: {filepath}\nData rows: {len(df)}, Chart type: {chart_type}",
                    df.to_dict(orient='records')
                )

        try:
            result, df_records = await asyncio.to_thread(_get_data_and_visualize)
            return ToolResultExpanded(
                output=result,
                data=df_records,
                system=f"Data visualization completed: {chart_type} chart with {len(y_fields)} y-field(s)",
            )
        except Exception as e:
            return ToolResultExpanded(error=f"Visualization failed: {e}")


schema_tool = DatabaseSchemaTool()
query_tool = DatabaseQueryTool()
visual_tool = DataVisualTool()

agent = create_react_agent(
    name="database-text2sql",
    tools=[schema_tool, query_tool, visual_tool],
    system_prompt=(
        "You are a database expert that translates natural language questions into SQL for both MySQL and SQLite databases. "
        "Always inspect the schema first with db_schema if structure details are unclear. "
        "Use db_query for lightweight exploratory reads and keep outputs concise. "
        "For data visualization needs, use data_visual to create charts (pie, line, scatter, bar) with specified SQL queries and chart parameters. "
        "CRITICAL: When queries involve user names, person names, or any textual identifiers, you MUST: "
        "1) NEVER hardcode numeric IDs - always look up IDs through JOINs "
        "2) Generate complete JOIN queries that connect related tables in a single statement "
        "3) Use proper table aliases for readability "
        "4) Be aware of database-specific SQL syntax differences between MySQL and SQLite "
        "For example, if asked about 'Jason's heart rate', write: "
        "SELECT h.Time, h.Value FROM heartrate_seconds_merged h JOIN users u ON h.Id = u.Id WHERE u.name = 'Jason' ORDER BY h.Time "
        "NOT: SELECT Time, Value FROM heartrate_seconds_merged WHERE Id = 123456 ORDER BY Time"
    ),
    next_step_prompt=(
        "Call db_schema for structure, db_query for data exploration, "
        "and data_visual to create charts when visualization is needed. "
        "When you have completed the task and provided the answer, use the terminate tool to end the task. "
        "Remember: Always use JOINs to connect tables instead of hardcoding IDs!"
    ),
    max_steps=15,
    enable_tracing=False,
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Database Text-to-SQL agent example with trace recording (supports MySQL and SQLite)"
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="显示用户表的10条用户数据",
        help="Natural-language question to answer with SQL.",
    )
    args = parser.parse_args()
    
    config = _load_database_config()
    print(f"🔍 Starting {config.db_type.upper()} Text-to-SQL with trace recording...")
    print(f"Question: {args.question}")

    result = await agent.run(args.question)
    print("\n✅ Agent execution completed:")
    print(result)

    if query_tool.executed_sql:
        print("\n📝 Exploration SQL history:")
        for idx, statement in enumerate(query_tool.executed_sql, start=1):
            print(f"- [{idx}] {statement}")

    print("\n✅ Agent execution completed. Check workdir/charts/ for any generated visualizations.")

    print("\n📊 Final response:")
    print(agent.final_response)

    # Save trace data to JSON
    await save_traces_to_json(f"{config.db_type}_text2sql_traces.json", args.question)


async def save_traces_to_json(filename: str, question: str) -> None:
    """Save all traces to a JSON file."""
    print(f"\n💾 Saving trace data to {filename}...")

    trace_manager = get_trace_manager()
    query_engine = TraceQueryEngine(trace_manager.storage)
    exporter = TraceExporter(query_engine)

    # Export traces to JSON
    json_data = await exporter.export_traces_to_json()

    if not os.path.isdir("./workdir/traces"):
        os.makedirs("./workdir/traces")

    # Save to file
    with open(f"./workdir/traces/{filename}", "w", encoding="utf-8") as f:
        f.write(json_data)

    # Get statistics
    stats = await query_engine.get_trace_statistics()

    print(f"✅ Saved trace data to {filename}")
    print("📊 Trace Statistics:")
    print(f"  - Total traces: {stats['total_traces']}")
    print(f"  - Average duration: {stats['avg_duration_ms']:.2f}ms")
    print(f"  - Error rate: {stats['error_rate']:.2%}")

    # Also save a summary report
    summary_filename = filename.replace(".json", "_summary.md")
    summary = await exporter.export_trace_summary()
    config = _load_database_config()
    with open(f"./workdir/traces/{summary_filename}", "w", encoding="utf-8") as f:
        f.write(f"# {config.db_type.upper()} Text-to-SQL Trace Summary\n\n")
        f.write(f"**Question:** {question}\n\n")
        f.write(summary)
    print(f"📋 Summary report saved to ./workdir/traces/{summary_filename}")


if __name__ == "__main__":
    asyncio.run(main())
