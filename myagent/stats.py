"""Centralized runtime statistics for agents, tools, and model usage.

This module provides a lightweight, generic statistics system to:
 - Track agent lifecycles (created, started, finished, error, cancelled)
 - Track tool executions (start/end, success/failure, duration)
 - Track model call counts and token usage (per model and per agent)

Design goals:
 - Zero external dependencies; simple counters + recent run records
 - Non-intrusive: works via small hooks in BaseAgent, ToolCollection, and LLM
 - Concurrency-safe enough for typical asyncio usage (coarse-grained lock)
 - Easy to query: expose a snapshot() with aggregated counters
"""

from __future__ import annotations

import contextvars
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Context for attributing tool/LLM activity to the current agent run
_current_agent_name: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "stats_current_agent_name", default=None
)
_current_agent_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "stats_current_agent_run_id", default=None
)


@dataclass
class AgentRun:
    id: str
    name: str
    model: str | None
    started_at: str
    start_monotonic: float
    ended_at: str | None = None
    end_monotonic: float | None = None
    status: str = "started"  # started | finished | error | cancelled | terminated
    steps: int = 0
    final_state: str | None = None

    @property
    def duration_ms(self) -> int | None:
        if self.end_monotonic is None:
            return None
        return int((self.end_monotonic - self.start_monotonic) * 1000)


@dataclass
class ToolRun:
    id: str
    tool: str
    agent: str | None
    started_at: str
    start_monotonic: float
    ended_at: str | None = None
    end_monotonic: float | None = None
    success: bool | None = None
    error: str | None = None
    args_size: int | None = None
    output_size: int | None = None

    @property
    def duration_ms(self) -> int | None:
        if self.end_monotonic is None:
            return None
        return int((self.end_monotonic - self.start_monotonic) * 1000)


class StatsManager:
    """Singleton manager that aggregates runtime statistics.

    Public API (most useful calls):
      - agent_created(name)
      - start_agent_run(name, model) -> run_id
      - finish_agent_run(run_id, status, steps, final_state)
      - start_tool_run(tool, args) -> run_id
      - finish_tool_run(run_id, success, output_size, error)
      - record_llm_call(model, call_type, input_tokens, output_tokens, agent_name)
      - snapshot() -> dict
    """

    def __init__(self) -> None:
        self._lock = RLock()

        # Agent lifecycle aggregates
        self._agent_created: Dict[str, int] = {}
        self._agent_runs_by_id: Dict[str, AgentRun] = {}
        self._agent_aggregates: Dict[str, Dict[str, Any]] = {}

        # Tool execution tracking
        self._tool_runs_by_id: Dict[str, ToolRun] = {}
        self._tool_aggregates: Dict[str, Dict[str, Any]] = {}

        # Model usage aggregates
        self._model_aggregates: Dict[str, Dict[str, int]] = {}
        self._model_by_agent: Dict[str, Dict[str, Dict[str, int]]] = {}

    # ---- Context helpers ----
    def set_current_agent_context(self, agent_name: str | None, run_id: str | None) -> None:
        _current_agent_name.set(agent_name)
        _current_agent_run_id.set(run_id)

    def get_current_agent_name(self) -> str | None:
        return _current_agent_name.get()

    def get_current_agent_run_id(self) -> str | None:
        return _current_agent_run_id.get()

    # ---- Agent lifecycle ----
    def agent_created(self, name: str) -> None:
        with self._lock:
            self._agent_created[name] = self._agent_created.get(name, 0) + 1

    def start_agent_run(self, name: str, model: str | None) -> str:
        run_id = uuid.uuid4().hex
        run = AgentRun(
            id=run_id,
            name=name,
            model=model,
            started_at=_now_iso(),
            start_monotonic=time.monotonic(),
        )
        with self._lock:
            self._agent_runs_by_id[run_id] = run
            agg = self._agent_aggregates.setdefault(
                name,
                {
                    "runs": 0,
                    "success": 0,
                    "error": 0,
                    "cancelled": 0,
                    "terminated": 0,
                    "total_duration_ms": 0,
                    "total_steps": 0,
                    "last_started_at": None,
                    "last_status": None,
                    "model": model,
                },
            )
            agg["runs"] += 1
            agg["last_started_at"] = run.started_at
            agg["last_status"] = "started"

        # Set context so tools/LLM can attribute events
        self.set_current_agent_context(name, run_id)
        return run_id

    def finish_agent_run(
        self,
        *,
        run_id: str,
        status: str,
        steps: int | None = None,
        final_state: str | None = None,
    ) -> None:
        with self._lock:
            run = self._agent_runs_by_id.get(run_id)
            if not run:
                return
            run.status = status
            run.steps = steps or run.steps
            run.final_state = final_state
            run.ended_at = _now_iso()
            run.end_monotonic = time.monotonic()

            agg = self._agent_aggregates.setdefault(
                run.name,
                {
                    "runs": 0,
                    "success": 0,
                    "error": 0,
                    "cancelled": 0,
                    "terminated": 0,
                    "total_duration_ms": 0,
                    "total_steps": 0,
                    "last_started_at": None,
                    "last_status": None,
                    "model": run.model,
                },
            )
            if status == "finished":
                agg["success"] += 1
            elif status == "error":
                agg["error"] += 1
            elif status == "cancelled":
                agg["cancelled"] += 1
            elif status == "terminated":
                agg["terminated"] += 1

            if run.duration_ms is not None:
                agg["total_duration_ms"] += run.duration_ms
            agg["total_steps"] += run.steps
            agg["last_status"] = status

        # Clear context if this run is the current context
        if self.get_current_agent_run_id() == run_id:
            self.set_current_agent_context(None, None)

    # ---- Tool executions ----
    def start_tool_run(self, tool: str, args: dict | None = None) -> str:
        run_id = uuid.uuid4().hex
        agent = self.get_current_agent_name()
        args_size = 0
        try:
            if args is not None:
                args_size = len(str(args))
        except Exception:
            args_size = 0

        rec = ToolRun(
            id=run_id,
            tool=tool,
            agent=agent,
            started_at=_now_iso(),
            start_monotonic=time.monotonic(),
            args_size=args_size,
        )
        with self._lock:
            self._tool_runs_by_id[run_id] = rec
        return run_id

    def finish_tool_run(
        self,
        *,
        run_id: str,
        success: bool,
        output_size: int | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            rec = self._tool_runs_by_id.get(run_id)
            if not rec:
                return
            rec.success = success
            rec.error = error
            rec.output_size = output_size
            rec.ended_at = _now_iso()
            rec.end_monotonic = time.monotonic()

            agg = self._tool_aggregates.setdefault(
                rec.tool,
                {
                    "executions": 0,
                    "success": 0,
                    "failure": 0,
                    "total_duration_ms": 0,
                    "total_args_size": 0,
                    "total_output_size": 0,
                    "last_error": None,
                },
            )
            agg["executions"] += 1
            if success:
                agg["success"] += 1
            else:
                agg["failure"] += 1
                agg["last_error"] = error

            if rec.duration_ms is not None:
                agg["total_duration_ms"] += rec.duration_ms
            if rec.args_size:
                agg["total_args_size"] += rec.args_size
            if output_size:
                agg["total_output_size"] += output_size

    # ---- Model usage ----
    def record_llm_call(
        self,
        *,
        model: str | None,
        call_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        agent_name: str | None = None,
    ) -> None:
        model_key = model or "unknown"
        with self._lock:
            agg = self._model_aggregates.setdefault(
                model_key, {"calls": 0, "input_tokens": 0, "output_tokens": 0}
            )
            agg["calls"] += 1
            agg["input_tokens"] += int(input_tokens or 0)
            agg["output_tokens"] += int(output_tokens or 0)

            if agent_name:
                by_agent = self._model_by_agent.setdefault(agent_name, {})
                aagg = by_agent.setdefault(
                    model_key, {"calls": 0, "input_tokens": 0, "output_tokens": 0}
                )
                aagg["calls"] += 1
                aagg["input_tokens"] += int(input_tokens or 0)
                aagg["output_tokens"] += int(output_tokens or 0)

    # ---- Queries ----
    def snapshot(self) -> dict[str, Any]:
        """Return a read-only snapshot of aggregated metrics."""
        with self._lock:
            # Compute derived averages without mutating live aggregates
            agents = {}
            for name, agg in self._agent_aggregates.items():
                avg_ms = None
                if agg["runs"] > 0 and agg["total_duration_ms"] > 0:
                    avg_ms = int(agg["total_duration_ms"] / max(1, agg["runs"]))
                agents[name] = {
                    **agg,
                    "avg_duration_ms": avg_ms,
                }

            tools = {}
            for tool, agg in self._tool_aggregates.items():
                avg_ms = None
                if agg["executions"] > 0 and agg["total_duration_ms"] > 0:
                    avg_ms = int(agg["total_duration_ms"] / max(1, agg["executions"]))
                tools[tool] = {
                    **agg,
                    "avg_duration_ms": avg_ms,
                }

            models = {
                "by_model": dict(self._model_aggregates),
                "by_agent": {k: dict(v) for k, v in self._model_by_agent.items()},
            }

            return {
                "agents": {
                    "created": dict(self._agent_created),
                    "by_agent": agents,
                },
                "tools": {
                    "by_tool": tools,
                },
                "models": models,
            }

    def reset(self) -> None:
        """Reset all accumulated statistics. Useful in tests or per-session runs."""
        with self._lock:
            self._agent_created.clear()
            self._agent_runs_by_id.clear()
            self._agent_aggregates.clear()
            self._tool_runs_by_id.clear()
            self._tool_aggregates.clear()
            self._model_aggregates.clear()
            self._model_by_agent.clear()


_INSTANCE: StatsManager | None = None


def get_stats_manager() -> StatsManager:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = StatsManager()
    return _INSTANCE
