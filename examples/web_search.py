"""Serper web search example for myagent with trace recording."""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, ClassVar
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool
from myagent.tool.base_tool import ToolResult
from myagent.stats import get_stats_manager

class SerperSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web via Serper (Google results)."
    parameters: ClassVar[dict[str, Any]] = {
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
        snippets: list[str] = []

        def _split_region(value: str | None) -> tuple[str | None, str | None]:
            if not value:
                return None, None
            parts = value.split("-")
            if len(parts) == 1:
                return (parts[0] or None), None
            gl = parts[0] or None
            hl = parts[1] or None
            return gl, hl

        def _search_sync() -> list[dict[str, Any]]:
            api_key = os.environ.get("SERPER_API_KEY")
            if not api_key:
                raise RuntimeError("SERPER_API_KEY environment variable is not set.")

            payload: dict[str, Any] = {
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
                        raise RuntimeError(
                            f"Serper request failed with status {response.status}."
                        )
                    data = json.load(response)
            except (HTTPError, URLError, TimeoutError) as exc:
                raise RuntimeError(f"Serper request failed: {exc}") from exc

            results: list[dict[str, Any]] = [
                {
                    "title": item.get("title"),
                    "href": item.get("link"),
                    "body": item.get("snippet") or item.get("description"),
                }
                for item in data.get("organic", [])
            ]

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

                snippet_lines = [
                    f"- {parts[0]}"
                    + (f" ({href})" if href and href != parts[0] else "")
                ]
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
            system=f"Found {len(snippets)} search results for query: '{query}'",
        )

async def main() -> None:
    # Create agent with tracing enabled
    agent = create_react_agent(
        name="web-searcher",
        tools=[SerperSearchTool()],
        system_prompt="You research user questions and call web_search for up-to-date context.",
        next_step_prompt="Use web_search when you need fresh information before answering.",
    )    
    summary = await agent.run("查找 OpenAI 最新的产品发布,并给出链接。")
    print("\n✅ Agent execution completed:")
    print(summary)

    # Print per-agent LLM call statistics
    try:
        agent_stats = agent.get_statistics()
        print("\n--- Agent LLM Statistics (web-searcher) ---")
        print(
            f"Model: {agent_stats.get('model')} | Total Calls: {agent_stats.get('total_calls')} | "
            f"Input Tokens: {agent_stats.get('total_input_tokens')} | Output Tokens: {agent_stats.get('total_output_tokens')} | "
            f"Total Tokens: {agent_stats.get('total_tokens')}"
        )
        calls = agent_stats.get("calls") or []
        if calls:
            print("Recent Calls:")
            for c in calls[-5:]:  # show last 5
                print(
                    f"  - #{c.get('id')} {c.get('timestamp')} type={c.get('call_type')} "
                    f"in={c.get('input_tokens', 0)} out={c.get('output_tokens', 0)} total={c.get('total_tokens', 0)}"
                )
    except Exception as e:
        print(f"[stats] Failed to get agent statistics: {e}")

    # Print global aggregated statistics (agents/tools/models)
    try:
        snapshot = get_stats_manager().snapshot()
        print("\n--- Global Statistics Snapshot ---")
        # Agents
        created = snapshot.get("agents", {}).get("created", {})
        by_agent = snapshot.get("agents", {}).get("by_agent", {})
        print(f"Agents Created: {created}")
        for name, a in by_agent.items():
            print(
                f"Agent '{name}': runs={a.get('runs')} success={a.get('success')} error={a.get('error')} "
                f"cancelled={a.get('cancelled')} terminated={a.get('terminated')} avg_ms={a.get('avg_duration_ms')} steps={a.get('total_steps')}"
            )

        # Tools
        by_tool = snapshot.get("tools", {}).get("by_tool", {})
        if by_tool:
            print("Tools:")
            for tool, t in by_tool.items():
                print(
                    f"  {tool}: exec={t.get('executions')} ok={t.get('success')} fail={t.get('failure')} avg_ms={t.get('avg_duration_ms')}"
                )

        # Models
        models = snapshot.get("models", {})
        if models:
            print("Models (by model):")
            for model, m in models.get("by_model", {}).items():
                print(
                    f"  {model}: calls={m.get('calls')} in={m.get('input_tokens')} out={m.get('output_tokens')}"
                )
            by_agent_model = models.get("by_agent", {})
            if by_agent_model:
                print("Models (by agent):")
                for aname, models_map in by_agent_model.items():
                    for model, m in models_map.items():
                        print(
                            f"  {aname}@{model}: calls={m.get('calls')} in={m.get('input_tokens')} out={m.get('output_tokens')}"
                        )
    except Exception as e:
        print(f"[stats] Failed to get global statistics: {e}")

if __name__ == "__main__":
    asyncio.run(main())
