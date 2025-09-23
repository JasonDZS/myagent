"""Serper web search example for myagent with trace recording."""
import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.trace import (
    TraceManager,
    TraceQueryEngine,
    TraceExporter,
    TraceMetadata,
    get_trace_manager
)


class SerperSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web via Serper (Google results)."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keywords.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of snippets to return.",
                "default": 3,
                "minimum": 1,
                "maximum": 10,
            },
            "region": {
                "type": "string",
                "description": "Serper region code (e.g. 'us', 'cn-zh').",
                "default": "us",
            },
        },
        "required": ["query"],
    }

    async def execute(
        self,
        query: str,
        max_results: int = 3,
        region: str = "us",
    ) -> ToolResult:
        snippets: List[str] = []

        def _split_region(value: str | None) -> Tuple[str | None, str | None]:
            if not value:
                return None, None
            parts = value.split("-")
            if len(parts) == 1:
                return (parts[0] or None), None
            gl = parts[0] or None
            hl = parts[1] or None
            return gl, hl

        def _search_sync() -> List[Dict[str, Any]]:
            api_key = os.environ.get("SERPER_API_KEY")
            if not api_key:
                raise RuntimeError("SERPER_API_KEY environment variable is not set.")

            payload: Dict[str, Any] = {
                "q": query,
                "num": max(1, min(max_results, 10)),
            }

            gl, hl = _split_region(region)
            if gl:
                payload["gl"] = gl
            if hl:
                payload["hl"] = hl

            request = Request(
                "https://google.serper.dev/search",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-API-KEY": api_key,
                },
                method="POST",
            )

            try:
                with urlopen(request, timeout=10) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Serper request failed with status {response.status}.")
                    data = json.load(response)
            except (HTTPError, URLError, TimeoutError) as exc:
                raise RuntimeError(f"Serper request failed: {exc}") from exc

            results: List[Dict[str, Any]] = []
            for item in data.get("organic", []):
                results.append(
                    {
                        "title": item.get("title"),
                        "href": item.get("link"),
                        "body": item.get("snippet") or item.get("description"),
                    }
                )

            return results

        try:
            results = await asyncio.to_thread(_search_sync)

            for entry in results:
                title = entry.get("title")
                href = entry.get("href")
                body = entry.get("body")

                parts = [part for part in (title, href) if part]
                if not parts:
                    continue

                snippet_lines = [f"- {parts[0]}" + (f" ({href})" if href and href != parts[0] else "")]
                if body:
                    snippet_lines.append(f"  {body}")

                snippets.append("\n".join(snippet_lines))
                if len(snippets) >= max_results:
                    break
        except Exception as exc:  # pragma: no cover - network variability
            return ToolResult(error=f"Search failed: {exc}")

        result_text = "\n".join(snippets) if snippets else "No live web results found."
        return ToolResult(
            output=result_text,
            system=f"Found {len(snippets)} search results for query: '{query}'"
        )


async def main() -> None:
    # Setup trace manager with metadata
    metadata = TraceMetadata(
        user_id="web_search_user",
        session_id=f"web_search_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        tags=["web_search", "serper", "openai_research"],
        environment="example",
        custom_fields={
            "example_type": "web_search",
            "search_engine": "serper"
        }
    )
    
    # Create agent with tracing enabled
    agent = create_react_agent(
        name="web-searcher",
        tools=[SerperSearchTool()],
        system_prompt="You research user questions and call web_search for up-to-date context.",
        next_step_prompt="Use web_search when you need fresh information before answering.",
        enable_tracing=True,
        trace_metadata=metadata
    )

    print("🔍 Starting web search with trace recording...")
    summary = await agent.run("查找 OpenAI 最新的产品发布，并给出链接。")
    print("\n✅ Agent execution completed:")
    print(summary)
    
    # Save trace data to JSON
    await save_traces_to_json("web_search_traces.json")


async def save_traces_to_json(filename: str) -> None:
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
    with open(f"./workdir/traces/{filename}", 'w', encoding='utf-8') as f:
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
    with open(f"./workdir/traces/{summary_filename}", 'w', encoding='utf-8') as f:
        f.write(summary)
    print(f"📋 Summary report saved to ./workdir/traces/{summary_filename}")

if __name__ == "__main__":
    asyncio.run(main())
