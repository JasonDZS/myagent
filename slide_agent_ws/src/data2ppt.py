"""Database to PPT example for myagent.
Analyzes database data and generates PPT slides in JSON format.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from contextlib import closing
from dataclasses import dataclass
from enum import Enum
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from typing import Any, ClassVar, Union

import sqlite3

try:
    import pymysql
    from pymysql.cursors import DictCursor
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False
    pymysql = None
    DictCursor = None

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult


class DatabaseType(str, Enum):
    MYSQL = "mysql"
    SQLITE = "sqlite"
    API = "api"


REQUIRED_MYSQL_ENV_VARS = (
    "MYSQL_HOST",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
)

REQUIRED_SQLITE_ENV_VARS = ("SQLITE_DATABASE",)

# API mode env vars (when DB_TYPE=api)
REQUIRED_API_ENV_VARS = (
    "API_BASE_URL",  # e.g. http://127.0.0.1:2818/api
)


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
    # API specific
    api_base_url: str | None = None
    api_dataset_id: int | None = None
    api_auth_token: str | None = None
    api_auth_scheme: str | None = None  # e.g. Bearer, Token


def _load_database_config() -> DatabaseConfig:
    db_type = DatabaseType(os.environ.get("DB_TYPE", "sqlite").lower())

    if db_type == DatabaseType.MYSQL:
        if not HAS_PYMYSQL:
            raise RuntimeError(
                "pymysql is not installed. Install it with: pip install pymysql"
            )
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
    elif db_type == DatabaseType.API:
        # API base URL is required; dataset/auth can be provided later via server session init
        missing = [var for var in REQUIRED_API_ENV_VARS if not os.environ.get(var)]
        if missing:
            raise RuntimeError(
                "Missing required API environment variables: " + ", ".join(missing)
            )

        dataset_id_env = os.environ.get("API_DATASET_ID")
        dataset_id: int | None = None
        try:
            if dataset_id_env is not None and str(dataset_id_env).strip():
                dataset_id = int(str(dataset_id_env).strip())
        except Exception:
            dataset_id = None

        auth_token = os.environ.get("API_AUTH_TOKEN")
        auth_scheme = os.environ.get("API_AUTH_SCHEME", "Bearer").strip() or "Bearer"

        return DatabaseConfig(
            db_type=db_type,
            database="api",
            api_base_url=os.environ["API_BASE_URL"].rstrip("/"),
            api_dataset_id=dataset_id,
            api_auth_token=auth_token,
            api_auth_scheme=auth_scheme,
        )
    else:
        raise RuntimeError(f"Unsupported database type: {db_type}")


def _connect(
    config: DatabaseConfig,
) -> Union[pymysql.connections.Connection, sqlite3.Connection]:
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
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    else:
        raise RuntimeError(f"Unsupported database type: {config.db_type}")


class DatabaseSchemaTool(BaseTool):
    name: str = "db_schema"
    description: str = (
        "Inspect table structure (MySQL/SQLite) or dataset tables via API when DB_TYPE=api."
    )
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
                # API-backed schema inspection
                if config.db_type == DatabaseType.API:
                    base = config.api_base_url or ""
                    dataset_id = config.api_dataset_id
                    if not dataset_id:
                        def _mask(tok: str | None) -> str:
                            if not tok:
                                return "<unset>"
                            s = str(tok)
                            if len(s) <= 8:
                                return "*" * len(s)
                            return s[:4] + "*" * (len(s) - 8) + s[-4:]
                        debug = (
                            f"API_BASE_URL={base or '<unset>'}; "
                            f"API_DATASET_ID={dataset_id or '<unset>'}; "
                            f"API_AUTH_SCHEME={(config.api_auth_scheme or '<unset>')}; "
                            f"API_AUTH_TOKEN={_mask(config.api_auth_token)}"
                        )
                        return (
                            "API mode requires dataset id. Provide via server session init or set API_DATASET_ID.\n"
                            f"Debug => {debug}"
                        )
                    url = urljoin(base + "/", f"datasets/{dataset_id}/tables")
                    headers = {"Content-Type": "application/json"}
                    if config.api_auth_token:
                        headers["Authorization"] = f"{config.api_auth_scheme or 'Bearer'} {config.api_auth_token}"
                    req = urllib_request.Request(url, headers=headers, method="GET")
                    try:
                        with urllib_request.urlopen(req, timeout=20) as resp:
                            raw = resp.read().decode("utf-8")
                        payload = json.loads(raw)
                    except HTTPError as he:
                        return f"API schema request failed: HTTP {he.code}"
                    except URLError as ue:
                        return f"API schema request failed: {ue.reason}"
                    except Exception as e:  # noqa: BLE001
                        return f"API schema request failed: {e}"

                    if not isinstance(payload, list):
                        return "Unexpected API response for tables list"
                    if not payload:
                        return "No tables found in the current dataset (API)."

                    if table:
                        # Find by duckdb_table
                        match = None
                        for t in payload:
                            if isinstance(t, dict) and t.get("duckdb_table") == table:
                                match = t
                                break
                        if not match:
                            return f"Table '{table}' not found in dataset (API)."
                        table_id = match.get("id")
                        if not isinstance(table_id, int):
                            return f"Table '{table}' missing id; cannot preview columns."
                        pv_url = urljoin(base + "/", f"tables/{table_id}/preview?limit=1")
                        pv_req = urllib_request.Request(pv_url, headers=headers, method="GET")
                        try:
                            with urllib_request.urlopen(pv_req, timeout=20) as resp2:
                                raw2 = resp2.read().decode("utf-8")
                            pv = json.loads(raw2)
                        except Exception as e:  # noqa: BLE001
                            return f"Failed to fetch table preview: {e}"
                        cols = pv.get("columns") or []
                        lines = [f"Columns for {table}:"]
                        for col in cols:
                            if isinstance(col, dict):
                                cname = col.get("name", "")
                                cdtype = col.get("dtype") or "unknown"
                                lines.append(f"- {cname} ({cdtype})")
                        return "\n".join(lines)

                    # No specific table: list names
                    lines = ["Available tables (API mode):"]
                    for t in payload:
                        if isinstance(t, dict):
                            duck = t.get("duckdb_table") or t.get("name")
                            lines.append(f"- {duck}")
                    return "\n".join(lines)

                # Direct DB schema inspection (MySQL / SQLite)
                with closing(_connect(config)) as connection:
                    if config.db_type == DatabaseType.MYSQL:
                        with closing(connection.cursor()) as cursor:
                            if not table:
                                cursor.execute("SHOW TABLES")
                                tables = [
                                    next(iter(row.values())) for row in cursor.fetchall()
                                ]
                                return (
                                    "Available tables:\n"
                                    + "\n".join(f"- {name}" for name in tables)
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
                                column_name = col.get("column_name") or col.get(
                                    "COLUMN_NAME", "unknown"
                                )
                                column_type = col.get("column_type") or col.get(
                                    "COLUMN_TYPE", "unknown"
                                )
                                is_nullable = col.get("is_nullable") or col.get(
                                    "IS_NULLABLE", "unknown"
                                )
                                column_key = col.get("column_key") or col.get(
                                    "COLUMN_KEY", ""
                                )
                                column_comment = col.get("column_comment") or col.get(
                                    "COLUMN_COMMENT", ""
                                )

                                nullable = "NULLABLE" if is_nullable == "YES" else "NOT NULL"
                                key = f" {column_key}" if column_key else ""
                                comment = f" -- {column_comment}" if column_comment else ""
                                lines.append(
                                    f"- {column_name} ({column_type} {nullable}{key}){comment}"
                                )

                            return "\n".join(lines)

                    elif config.db_type == DatabaseType.SQLITE:
                        cursor = connection.cursor()
                        if not table:
                            cursor.execute(
                                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                            )
                            tables = [row[0] for row in cursor.fetchall()]
                            return (
                                "Available tables:\n"
                                + "\n".join(f"- {name}" for name in tables)
                                if tables
                                else "No tables found in the current database."
                            )

                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = cursor.fetchall()

                        if not columns:
                            return f"Table '{table}' does not exist in the database."

                        lines = [f"Columns for {table}:"]
                        for col in columns:
                            column_name = col[1]
                            column_type = col[2]
                            not_null = col[3]
                            is_pk = col[5]

                            nullable = "NOT NULL" if not_null else "NULLABLE"
                            key = " PRIMARY KEY" if is_pk else ""
                            lines.append(
                                f"- {column_name} ({column_type} {nullable}{key})"
                            )

                        return "\n".join(lines)

            except Exception as e:
                return f"Database connection or query error: {e}"

        try:
            result = await asyncio.to_thread(_inspect_schema)
            if result is None:
                return ToolResult(
                    error="Schema inspection returned None - unexpected result"
                )

            return ToolResult(
                output=result,
                system=f"Schema inspection completed for {'table: ' + table if table else 'all tables'}",
            )
        except Exception as exc:
            return ToolResult(error=f"Schema inspection failed: {exc}")


class DatabaseQueryTool(BaseTool):
    name: str = "db_query"
    description: str = "Execute a read-only SQL query and return structured data for analysis."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Complete SQL SELECT statement.",
            },
            "max_rows": {
                "type": "integer",
                "description": "Maximum number of rows to return.",
                "default": 100,
                "minimum": 1,
                "maximum": 1000,
            },
        },
        "required": ["sql"],
    }

    async def execute(self, sql: str, max_rows: int = 100) -> ToolResult:
        stripped_sql = sql.strip().rstrip(";")
        lowered = stripped_sql.lstrip().lower()

        config = _load_database_config()

        if config.db_type == DatabaseType.MYSQL:
            allowed_prefixes = ("select", "show", "describe", "explain", "with")
        elif config.db_type == DatabaseType.SQLITE:
            allowed_prefixes = ("select", "explain", "pragma", "with")
        else:
            # API mode follows backend rules: single SELECT/CTE
            allowed_prefixes = ("select", "with")

        if not lowered.startswith(allowed_prefixes):
            return ToolResult(error="Only read-only queries are permitted.")

        def _run_query() -> dict[str, Any]:
            if config.db_type == DatabaseType.API:
                base = (config.api_base_url or "").rstrip("/")
                dataset_id = config.api_dataset_id
                if not base:
                    raise RuntimeError("API_BASE_URL is required for DB_TYPE=api")
                if not dataset_id:
                    raise RuntimeError("API_DATASET_ID is not set for API mode")
                url = urljoin(base + "/", f"datasets/{dataset_id}/sql")
                headers = {"Content-Type": "application/json"}
                if config.api_auth_token:
                    headers["Authorization"] = f"{config.api_auth_scheme or 'Bearer'} {config.api_auth_token}"
                body = json.dumps({"sql": stripped_sql, "limit": max_rows, "wrap_limit": True}).encode("utf-8")
                req = urllib_request.Request(url, data=body, headers=headers, method="POST")
                try:
                    with urllib_request.urlopen(req, timeout=30) as resp:
                        raw = resp.read().decode("utf-8")
                except HTTPError as he:
                    # try to read error body
                    try:
                        raw_err = he.read().decode("utf-8")
                        try:
                            err_obj = json.loads(raw_err)
                            detail = err_obj.get("detail") if isinstance(err_obj, dict) else raw_err
                        except Exception:
                            detail = raw_err
                    except Exception:
                        detail = f"HTTP {he.code}"
                    raise RuntimeError(f"Backend API error: {detail}") from he
                except URLError as ue:
                    raise RuntimeError(f"API request failed: {ue.reason}") from ue
                except Exception as e:
                    raise RuntimeError(f"API request failed: {e}") from e

                try:
                    payload = json.loads(raw)
                except Exception as e:  # noqa: BLE001
                    raise RuntimeError(f"Invalid JSON from API: {e}") from e

                cols = payload.get("columns") or []
                colnames = [c.get("name") if isinstance(c, dict) else str(c) for c in cols]
                rows = payload.get("rows") or []
                data = []
                if isinstance(rows, list):
                    for r in rows:
                        if isinstance(r, dict):
                            data.append(r)
                        elif isinstance(r, (list, tuple)):
                            data.append(dict(zip(colnames, r)))
                        else:
                            data.append({"value": r})
                return {"columns": colnames, "data": data, "row_count": len(data)}

            with closing(_connect(config)) as connection:
                if config.db_type == DatabaseType.MYSQL:
                    with closing(connection.cursor()) as cursor:
                        cursor.execute(stripped_sql)
                        rows = cursor.fetchmany(size=max_rows)
                        columns = (
                            [col[0] for col in cursor.description]
                            if cursor.description
                            else []
                        )
                        data = [dict(row) for row in rows]

                elif config.db_type == DatabaseType.SQLITE:
                    cursor = connection.cursor()
                    cursor.execute(stripped_sql)
                    rows = cursor.fetchmany(size=max_rows)
                    columns = (
                        [col[0] for col in cursor.description]
                        if cursor.description
                        else []
                    )
                    data = [dict(zip(columns, row)) for row in rows]

                return {"columns": columns, "data": data, "row_count": len(data)}

        try:
            result = await asyncio.to_thread(_run_query)
            return ToolResult(
                output=json.dumps(result, ensure_ascii=False, indent=2),
                system=f"Query executed: {len(result['data'])} rows returned",
            )
        except Exception as exc:
            return ToolResult(error=f"Query failed: {exc}")


class GeneratePPTTool(BaseTool):
    name: str = "generate_ppt"
    description: str = "Generate PPT slides in JSON format based on data analysis insights."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "slides": {
                "type": "array",
                "description": "Array of slide objects to generate PPT presentation.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "Unique slide identifier (starting from 1)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Slide title",
                        },
                        "text": {
                            "type": "string",
                            "description": "Slide content text (single paragraph, <=100 characters, inline markdown ok)",
                        },
                        "charts": {
                            "type": "array",
                            "description": "Optional charts array (maximum 2 charts)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["bar", "line", "pie", "area"],
                                        "description": "Chart type (default: bar)",
                                    },
                                    "title": {
                                        "type": "string",
                                        "description": "Chart title",
                                    },
                                    "data": {
                                        "type": "array",
                                        "description": "Chart data points",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "value": {"type": "number"},
                                            },
                                            "required": ["name", "value"],
                                        },
                                    },
                                    "horizontal": {
                                        "type": "boolean",
                                        "description": "For bar charts, whether to display horizontally",
                                    },
                                },
                                "required": ["data"],
                            },
                        },
                        "layout": {
                            "type": "string",
                            "enum": ["single", "double"],
                            "description": "Chart layout: single (1 chart) or double (2 charts side-by-side)",
                        },
                    },
                    "required": ["id", "title", "text"],
                },
            }
        },
        "required": ["slides"],
    }

    async def execute(self, slides: list[dict[str, Any]]) -> ToolResult:
        try:
            # Validate slide structure
            for slide in slides:
                if "id" not in slide or "title" not in slide or "text" not in slide:
                    return ToolResult(
                        error="Invalid slide structure. Each slide must have id, title, and text fields."
                    )

                text_value = str(slide["text"]).strip()
                if len(text_value) > 100:
                    return ToolResult(
                        error=f"Slide {slide['id']} text must be 100 characters or fewer."
                    )
                if "\n" in text_value or "\r" in text_value:
                    return ToolResult(
                        error=f"Slide {slide['id']} text must be a single paragraph without line breaks."
                    )
                stripped_text = text_value.lstrip()
                bullet_starts = ("-", "*", "•")
                if stripped_text.startswith(bullet_starts) or any(stripped_text.startswith(f"{i}. ") for i in range(1, 10)):
                    return ToolResult(
                        error=f"Slide {slide['id']} text must be a sentence, not a list."
                    )

                if "charts" in slide:
                    charts = slide["charts"]
                    if not isinstance(charts, list):
                        return ToolResult(
                            error=f"Invalid chart structure in slide {slide['id']}. Charts must be a list."
                        )
                    if len(charts) > 2:
                        return ToolResult(
                            error=f"Slide {slide['id']} cannot contain more than 2 charts."
                        )
                    for chart in charts:
                        if "data" not in chart:
                            return ToolResult(
                                error=f"Invalid chart in slide {slide['id']}. Each chart must have a 'data' field."
                            )
                        for data_point in chart["data"]:
                            if "name" not in data_point or "value" not in data_point:
                                return ToolResult(
                                    error=f"Invalid chart data in slide {slide['id']}. Each data point must have 'name' and 'value'."
                                )

            # Generate JSON output
            ppt_json = json.dumps(slides, ensure_ascii=False, indent=2)

            # Save to file
            os.makedirs("./workdir/ppt", exist_ok=True)
            output_file = "./workdir/ppt/presentation.json"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(ppt_json)

            return ToolResult(
                output=f"PPT JSON generated successfully!\n\nFile saved to: {output_file}\n\nSlide count: {len(slides)}\n\nJSON Preview:\n{ppt_json}",
                system=f"PPT generation completed with {len(slides)} slides",
            )
        except Exception as exc:
            return ToolResult(error=f"PPT generation failed: {exc}")


# Initialize tools
schema_tool = DatabaseSchemaTool()
query_tool = DatabaseQueryTool()
ppt_tool = GeneratePPTTool()

# Create agent
agent = create_react_agent(
    name="data2ppt",
    tools=[schema_tool, query_tool, ppt_tool],
    system_prompt=(
        "You are a data analyst expert that analyzes database data and generates professional PPT presentations. "
        "Your workflow should be:\n"
        "1. Use db_schema to understand the database structure and available tables\n"
        "2. Use db_query to fetch relevant data for analysis\n"
        "3. Analyze the data to extract key insights, trends, and patterns\n"
        "4. Use generate_ppt to create a structured PPT presentation in JSON format\n\n"
        "PPT Format Guidelines:\n"
        "- Each slide must have: id (integer), title (string), text (string)\n"
        "- Optional charts array with data points (name, value)\n"
        "- Slide text must be a single paragraph (<=100 characters). Inline Markdown for bold/italic/color is allowed; avoid lists or line breaks.\n"
        "- Limit each slide to at most two charts.\n"
        "- Chart types: 'bar', 'line', 'pie', 'area' (default: bar)\n"
        "- Layout: 'single' (1 chart) or 'double' (2 charts side-by-side)\n"
        "- For bar charts, use 'horizontal: true' for horizontal bars\n\n"
        "Create insightful, data-driven presentations with clear visualizations."
    ),
    next_step_prompt=(
        "Use db_schema to explore tables, db_query to fetch data, and generate_ppt to create the final presentation. "
        "When you have completed the analysis and generated the PPT JSON, use the terminate tool to end the task."
    ),
    max_steps=20,
    enable_tracing=False,
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Database to PPT generator - analyzes data and creates PPT slides in JSON format"
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="分析数据库中的数据，生成一个包含数据洞察的PPT报告",
        help="Analysis request for PPT generation",
    )
    args = parser.parse_args()

    config = _load_database_config()
    print(f"Database: {config.database} ({config.db_type.value})")
    print(f"Question: {args.question}\n")

    result = await agent.run(args.question)
    print("\n✅ Agent execution completed:")
    print(result)

    print("\n📊 Final response:")
    print(agent.final_response)

    print(
        "\n💡 Tip: Check ./workdir/ppt/presentation.json for the generated PPT slides"
    )


if __name__ == "__main__":
    asyncio.run(main())
