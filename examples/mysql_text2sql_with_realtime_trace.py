"""MySQL Text-to-SQL example for myagent with real-time trace printing."""

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

# Rich imports with fallback
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback console for when rich is not available
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
    
    class Table:
        def __init__(self, title=None):
            self.title = title
            self.rows = []
        def add_column(self, *args, **kwargs):
            pass
        def add_row(self, *args):
            self.rows.append(args)
    
    class Panel:
        def __init__(self, content, title=None, style=None, border_style=None):
            self.content = content
            self.title = title

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult
from contextlib import asynccontextmanager
from myagent.trace import (
    TraceManager,
    TraceQueryEngine,
    TraceExporter,
    TraceMetadata,
    get_trace_manager,
    RunType,
    RunStatus
)


REQUIRED_ENV_VARS = (
    "MYSQL_HOST",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
)

# Rich console for beautiful output
console = Console()


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


class RealTimeTracePrinter:
    """Real-time trace printer that monitors and displays trace updates."""
    
    def __init__(self):
        self.trace_manager = get_trace_manager()
        self.current_trace = None
        self.run_count = 0
        self.last_printed_runs = set()
        
    def start_monitoring(self):
        """Start monitoring trace updates."""
        if RICH_AVAILABLE:
            console.print(Panel("🔍 Starting Real-Time Trace Monitor", style="bold green"))
        else:
            console.print("🔍 Starting Real-Time Trace Monitor")
        
    def print_trace_start(self, trace):
        """Print trace start information."""
        self.current_trace = trace
        self.run_count = 0
        self.last_printed_runs.clear()
        
        if RICH_AVAILABLE:
            table = Table(title=f"📊 Trace Started: {trace.name}")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="magenta")
            
            table.add_row("Trace ID", trace.id[:8] + "...")
            table.add_row("Request", trace.request[:50] + "..." if trace.request and len(trace.request) > 50 else trace.request or "N/A")
            table.add_row("Start Time", trace.start_time.strftime("%H:%M:%S"))
            
            console.print(table)
        else:
            console.print(f"📊 Trace Started: {trace.name}")
            console.print(f"  Trace ID: {trace.id[:8]}...")
            console.print(f"  Request: {trace.request[:50] + '...' if trace.request and len(trace.request) > 50 else trace.request or 'N/A'}")
            console.print(f"  Start Time: {trace.start_time.strftime('%H:%M:%S')}")
        console.print()
        
    def print_run_update(self, run):
        """Print run update information."""
        if run.id in self.last_printed_runs:
            return
            
        self.run_count += 1
        self.last_printed_runs.add(run.id)
        
        # Run type icon
        type_icons = {
            RunType.AGENT: "🤖",
            RunType.THINK: "🤔", 
            RunType.ACT: "⚡",
            RunType.TOOL: "🔧",
            RunType.LLM: "🧠",
        }
        icon = type_icons.get(run.run_type, "📋")
        
        if RICH_AVAILABLE:
            # Status styling
            status_style = {
                RunStatus.RUNNING: "yellow",
                RunStatus.SUCCESS: "green", 
                RunStatus.ERROR: "red",
                RunStatus.PENDING: "blue"
            }.get(run.status, "white")
            
            # Create run panel
            run_info = f"[bold]{icon} {run.name}[/bold]\n"
            run_info += f"Type: {run.run_type.value}\n"
            run_info += f"Status: [{status_style}]{run.status.value}[/{status_style}]\n"
            
            if run.inputs:
                input_preview = str(run.inputs)[:100] + "..." if len(str(run.inputs)) > 100 else str(run.inputs)
                run_info += f"Inputs: {input_preview}\n"
                
            if run.outputs:
                output_preview = str(run.outputs)[:100] + "..." if len(str(run.outputs)) > 100 else str(run.outputs)
                run_info += f"Outputs: {output_preview}\n"
                
            if run.duration_ms:
                run_info += f"Duration: {run.duration_ms:.2f}ms\n"
                
            if run.error:
                run_info += f"[red]Error: {run.error}[/red]\n"
            
            panel = Panel(
                run_info.strip(),
                title=f"Step {self.run_count}",
                border_style=status_style
            )
            console.print(panel)
        else:
            # Plain text output
            console.print(f"\n--- Step {self.run_count} ---")
            console.print(f"{icon} {run.name}")
            console.print(f"Type: {run.run_type.value}")
            console.print(f"Status: {run.status.value}")
            
            if run.inputs:
                input_preview = str(run.inputs)[:100] + "..." if len(str(run.inputs)) > 100 else str(run.inputs)
                console.print(f"Inputs: {input_preview}")
                
            if run.outputs:
                output_preview = str(run.outputs)[:100] + "..." if len(str(run.outputs)) > 100 else str(run.outputs)
                console.print(f"Outputs: {output_preview}")
                
            if run.duration_ms:
                console.print(f"Duration: {run.duration_ms:.2f}ms")
                
            if run.error:
                console.print(f"Error: {run.error}")
            console.print("---")
        
    def print_trace_end(self, trace):
        """Print trace completion information."""
        if RICH_AVAILABLE:
            table = Table(title="✅ Trace Completed")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Duration", f"{trace.duration_ms:.2f}ms" if trace.duration_ms else "N/A")
            table.add_row("Total Runs", str(len(trace.runs)))
            table.add_row("Status", trace.status.value)
            
            if trace.total_cost:
                table.add_row("Total Cost", f"${trace.total_cost:.4f}")
            if trace.total_tokens:
                table.add_row("Total Tokens", str(trace.total_tokens))
                
            console.print(table)
        else:
            console.print("\n✅ Trace Completed")
            console.print(f"Duration: {trace.duration_ms:.2f}ms" if trace.duration_ms else "Duration: N/A")
            console.print(f"Total Runs: {len(trace.runs)}")
            console.print(f"Status: {trace.status.value}")
            
            if trace.total_cost:
                console.print(f"Total Cost: ${trace.total_cost:.4f}")
            if trace.total_tokens:
                console.print(f"Total Tokens: {trace.total_tokens}")
                
        console.print()
        
    def monitor_current_trace(self):
        """Monitor and print updates for the current trace."""
        if not self.current_trace:
            return
            
        # Check for new runs
        for run in self.current_trace.runs:
            if run.id not in self.last_printed_runs:
                self.print_run_update(run)


# Create global printer instance
trace_printer = RealTimeTracePrinter()


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
            tool_result = ToolResult(
                output=result,
                system=f"Schema inspection completed for {'table: ' + table if table else 'all tables'}"
            )
            
            # Print tool execution
            console.print(f"🔧 [bold]mysql_schema[/bold] executed: {table or 'all tables'}")
            console.print(f"📋 Result preview: {result[:100]}...")
            console.print()
            
            return tool_result
        except Exception as exc:
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
            
            # Print tool execution
            console.print(f"🔧 [bold]mysql_query[/bold] executed:")
            console.print(f"📝 SQL: {stripped_sql}")
            console.print(f"📊 Rows returned: {len(result.split(chr(10))) - 3 if result != 'No rows returned.' else 0}")
            console.print()
            
        except Exception as exc:
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
            
            # Print tool execution
            console.print(f"🔧 [bold]mysql_validate_sql[/bold] executed:")
            console.print(f"✅ SQL validated: {stripped_sql}")
            console.print(f"📈 EXPLAIN plan generated successfully")
            console.print()
            
        except Exception as exc:
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


class MonitoringTraceManager(TraceManager):
    """Enhanced TraceManager that provides real-time monitoring."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.printer = trace_printer
        # Override the storage to add monitoring
        original_save_run = self.storage.save_run
        async def monitored_save_run(run):
            # Print run update when it's saved
            asyncio.create_task(self._monitor_run(run))
            return await original_save_run(run)
        self.storage.save_run = monitored_save_run
    
    @asynccontextmanager
    async def trace(self, *args, **kwargs):
        """Override trace method to add monitoring."""
        async with super().trace(*args, **kwargs) as trace_ctx:
            self.printer.print_trace_start(trace_ctx)
            yield trace_ctx
            self.printer.print_trace_end(trace_ctx)
    
    async def _monitor_run(self, run):
        """Monitor a single run for changes."""
        # Wait a bit for run to be populated
        await asyncio.sleep(0.1)
        self.printer.print_run_update(run)


async def main() -> None:
    parser = argparse.ArgumentParser(description="MySQL Text-to-SQL agent example with real-time trace printing")
    parser.add_argument(
        "question",
        nargs="?",
        default="显示用户表的10条用户数据",
        help="Natural-language question to answer with SQL.",
    )
    args = parser.parse_args()

    # Rich availability check
    if not RICH_AVAILABLE:
        print("Note: Rich library not found. Install with 'pip install rich' for enhanced output.")
        print("Continuing with basic output...")
        print()

    # Setup enhanced trace manager with real-time monitoring
    enhanced_manager = MonitoringTraceManager()
    from myagent.trace import set_trace_manager
    set_trace_manager(enhanced_manager)
    
    # Setup trace metadata
    metadata = TraceMetadata(
        user_id="mysql_text2sql_user",
        session_id=f"mysql_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        tags=["mysql", "text2sql", "database_query", "realtime"],
        environment="example",
        custom_fields={
            "example_type": "mysql_text2sql_realtime",
            "database_type": "mysql",
            "question": args.question,
            "monitoring": "enabled"
        }
    )

    schema_tool = MySQLSchemaTool()
    query_tool = MySQLQueryTool()
    validate_tool = MySQLValidateSQLTool()

    agent = create_react_agent(
        name="mysql-text2sql-realtime",
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
        max_steps=15,
        enable_tracing=True,
        trace_metadata=metadata
    )

    # Start monitoring
    trace_printer.start_monitoring()
    
    if RICH_AVAILABLE:
        console.print(Panel(f"🚀 Starting MySQL Text-to-SQL Agent", style="bold blue"))
        console.print(f"[bold]Question:[/bold] {args.question}")
    else:
        console.print("🚀 Starting MySQL Text-to-SQL Agent")
        console.print(f"Question: {args.question}")
    console.print()
    
    # Run agent with real-time monitoring
    result = await agent.run(args.question)
    
    if RICH_AVAILABLE:
        console.print(Panel("✅ Agent Execution Completed", style="bold green"))
        console.print(f"[bold]Result:[/bold] {result}")
    else:
        console.print("\n✅ Agent Execution Completed")
        console.print(f"Result: {result}")
    console.print()

    if query_tool.executed_sql:
        if RICH_AVAILABLE:
            console.print("[bold]📝 Exploration SQL History:[/bold]")
        else:
            console.print("📝 Exploration SQL History:")
        for idx, statement in enumerate(query_tool.executed_sql, start=1):
            console.print(f"  [{idx}] {statement}")
        console.print()

    if validate_tool.final_sql:
        if RICH_AVAILABLE:
            console.print("[bold]✅ Validated Final SQL:[/bold]")
            console.print(f"[green]{validate_tool.final_sql}[/green]")
        else:
            console.print("✅ Validated Final SQL:")
            console.print(validate_tool.final_sql)
    else:
        if RICH_AVAILABLE:
            console.print("[yellow]⚠️ No final SQL was validated. Ensure the agent calls mysql_validate_sql once satisfied.[/yellow]")
        else:
            console.print("⚠️ No final SQL was validated. Ensure the agent calls mysql_validate_sql once satisfied.")
    console.print()

    if RICH_AVAILABLE:
        console.print("[bold]📊 Final Response:[/bold]")
    else:
        console.print("📊 Final Response:")
    console.print(agent.final_response)
    console.print()
    
    # Save trace data to JSON
    await save_traces_to_json("mysql_text2sql_realtime_traces.json", args.question)


async def save_traces_to_json(filename: str, question: str) -> None:
    """Save all traces to a JSON file."""
    console.print(f"💾 Saving trace data to {filename}...")
    
    trace_manager = get_trace_manager()
    query_engine = TraceQueryEngine(trace_manager.storage)
    exporter = TraceExporter(query_engine)
    
    # Export traces to JSON
    json_data = await exporter.export_traces_to_json()
    
    if not os.path.isdir("./workdir/traces"):
        os.makedirs("./workdir/traces")

    # Save to file
    with open(f"./workdir/traces/{filename}", 'w', encoding='utf-8') as f:
        f.write(json_data)
    
    # Get statistics
    stats = await query_engine.get_trace_statistics()
    
    if RICH_AVAILABLE:
        table = Table(title="📊 Trace Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total traces", str(stats['total_traces']))
        table.add_row("Average duration", f"{stats['avg_duration_ms']:.2f}ms")
        table.add_row("Error rate", f"{stats['error_rate']:.2%}")
        
        console.print(table)
    else:
        console.print("📊 Trace Statistics:")
        console.print(f"  Total traces: {stats['total_traces']}")
        console.print(f"  Average duration: {stats['avg_duration_ms']:.2f}ms")
        console.print(f"  Error rate: {stats['error_rate']:.2%}")
    
    # Also save a summary report
    summary_filename = filename.replace('.json', '_summary.md')
    summary = await exporter.export_trace_summary()
    with open(f"./workdir/traces/{summary_filename}", 'w', encoding='utf-8') as f:
        f.write(f"# MySQL Text-to-SQL Real-time Trace Summary\n\n")
        f.write(f"**Question:** {question}\n\n")
        f.write(summary)
    
    console.print(f"✅ Trace data saved to ./workdir/traces/{filename}")
    console.print(f"📋 Summary report saved to ./workdir/traces/{summary_filename}")


if __name__ == "__main__":
    asyncio.run(main())