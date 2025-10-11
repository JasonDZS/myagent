"""High-level orchestration utilities for Plan → Solve style agents.

This module extracts the reusable structure from plan_solve_data2ppt.py
and provides a configurable pipeline similar to create_toolcall_agent.
Developers can implement custom plan and solver agents by subclassing the
PlanAgent and SolverAgent base classes, then assemble them with
create_plan_solver().
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Awaitable, Callable, Sequence

from pydantic import Field

from ..logger import logger
from ..schema import AgentState
from ..ws import get_ws_session_context, send_websocket_message
from ..ws.events import create_event
from .base import BaseAgent

AggregateFn = Callable[["PlanContext", Sequence["SolverRunResult"]], Any]
AsyncAggregateFn = Callable[["PlanContext", Sequence["SolverRunResult"]], Awaitable[Any]]
ProgressCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True)
class PlanContext:
    """Context shared from planning to solving and aggregation stages."""

    name: str
    question: str
    tasks: Sequence[Any]
    plan_summary: str | None
    raw_plan_output: str | None
    plan_statistics: dict[str, Any] | None = None


@dataclass(frozen=True)
class SolverRunResult:
    """Represents the outcome of a single solver agent run."""

    task: Any
    output: Any
    summary: str | None
    raw_output: str | None
    agent_name: str
    statistics: dict[str, Any] | None = None


@dataclass(frozen=True)
class PlanSolveResult:
    """Aggregate outcome of the plan → solve pipeline."""

    context: PlanContext
    solver_results: Sequence[SolverRunResult]
    aggregate_output: Any = None
    statistics: dict[str, Any] | None = None

    @property
    def tasks(self) -> Sequence[Any]:
        return self.context.tasks

    @property
    def plan_summary(self) -> str | None:
        return self.context.plan_summary

    @property
    def plan_statistics(self) -> dict[str, Any] | None:
        return self.context.plan_statistics

    @property
    def question(self) -> str:
        return self.context.question

    @property
    def pipeline_statistics(self) -> dict[str, Any] | None:
        return self.statistics


class PlanAgent:
    """Base class for plan agents used in the plan→solve pipeline.

    Subclasses should override `build_agent` and `extract_tasks`. Optional
    hooks allow custom request construction and summary extraction.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = name or self.__class__.__name__.lower()

    # -- Required hooks -------------------------------------------------
    def build_agent(self) -> BaseAgent:
        """Instantiate and return the underlying agent."""
        raise NotImplementedError("PlanAgent.build_agent must be implemented.")

    def extract_tasks(self, agent: BaseAgent, plan_output: str) -> Sequence[Any]:
        """Extract structured tasks from the planning agent."""
        raise NotImplementedError("PlanAgent.extract_tasks must be implemented.")

    # -- Optional hooks -------------------------------------------------
    def build_request(self, question: str) -> str:
        """Construct the request message for the planning agent."""
        return question

    def extract_summary(self, agent: BaseAgent, plan_output: str) -> str | None:
        """Return a human-readable summary of the plan."""
        if getattr(agent, "final_response", None):
            return agent.final_response  # type: ignore[attr-defined]
        return plan_output


class SolverAgent:
    """Base class for solver agents that execute individual plan tasks."""

    def __init__(self, name: str | None = None) -> None:
        self.name = name or self.__class__.__name__.lower()

    # -- Required hooks -------------------------------------------------
    def build_agent(self, task: Any, *, context: PlanContext) -> BaseAgent:
        """Instantiate an agent configured for the given task."""
        raise NotImplementedError("SolverAgent.build_agent must be implemented.")

    def extract_result(
        self, agent: BaseAgent, solver_output: str, task: Any, *, context: PlanContext
    ) -> Any:
        """Extract the actionable result from the solver agent run."""
        raise NotImplementedError("SolverAgent.extract_result must be implemented.")

    # -- Optional hooks -------------------------------------------------
    def build_request(
        self, task: Any, *, context: PlanContext
    ) -> str:
        """Construct the request message for the solver agent."""
        return str(task)

    def extract_summary(
        self, agent: BaseAgent, solver_output: str, task: Any, *, context: PlanContext
    ) -> str | None:
        """Return a concise summary of the solver outcome."""
        if getattr(agent, "final_response", None):
            return agent.final_response  # type: ignore[attr-defined]
        return solver_output


class PlanSolverPipeline:
    """Coordinates a planning agent with multiple solver agents."""

    def __init__(
        self,
        *,
        name: str = "plan_solver",
        planner: PlanAgent,
        solver: SolverAgent,
        aggregator: AggregateFn | AsyncAggregateFn | None = None,
        concurrency: int | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.name = name
        self.planner = planner
        self.solver = solver
        self.aggregator = aggregator
        self.concurrency = concurrency
        self.progress_callback = progress_callback

    async def run(self, question: str) -> PlanSolveResult:
        """Execute the plan → solve pipeline for the provided question."""
        await self._notify("plan.start", {"question": question})

        plan_agent = self.planner.build_agent()
        plan_request = self.planner.build_request(question)
        plan_output = await plan_agent.run(plan_request)
        tasks = list(self.planner.extract_tasks(plan_agent, plan_output))

        if not tasks:
            raise RuntimeError(
                f"Planner '{self.planner.name}' produced no tasks for question: {question}"
            )

        plan_summary = self.planner.extract_summary(plan_agent, plan_output)
        plan_statistics = None
        if hasattr(plan_agent, "get_statistics"):
            try:
                plan_statistics = plan_agent.get_statistics()
            except Exception as exc:  # pragma: no cover - safeguard
                logger.debug(
                    "Failed to collect planner statistics (%s): %s",
                    getattr(plan_agent, "name", self.planner.name),
                    exc,
                )
        context = PlanContext(
            name=self.name,
            question=question,
            tasks=tasks,
            plan_summary=plan_summary,
            raw_plan_output=plan_output,
            plan_statistics=plan_statistics,
        )

        await self._notify(
            "plan.completed",
            {
                "tasks": tasks,
                "plan_summary": plan_summary,
                "statistics": plan_statistics,
            },
        )

        solver_results = await self._run_solvers(tasks, context)
        aggregate_output = await self._run_aggregator(context, solver_results)
        pipeline_statistics = self._build_pipeline_statistics(
            plan_statistics, solver_results
        )

        await self._notify(
            "pipeline.completed",
            {
                "context": context,
                "solver_results": solver_results,
                "aggregate_output": aggregate_output,
                "statistics": pipeline_statistics,
            },
        )

        return PlanSolveResult(
            context=context,
            solver_results=solver_results,
            aggregate_output=aggregate_output,
            statistics=pipeline_statistics,
        )

    async def _run_solvers(
        self, tasks: Sequence[Any], context: PlanContext
    ) -> list[SolverRunResult]:
        semaphore = (
            asyncio.Semaphore(self.concurrency) if self.concurrency else None
        )

        async def _execute(task: Any) -> SolverRunResult:
            await self._notify("solver.start", {"task": task})

            async def _run() -> SolverRunResult:
                agent = self.solver.build_agent(task, context=context)
                request = self.solver.build_request(task, context=context)
                solver_output = await agent.run(request)
                output = self.solver.extract_result(
                    agent, solver_output, task, context=context
                )
                summary = self.solver.extract_summary(
                    agent, solver_output, task, context=context
                )
                statistics = None
                if hasattr(agent, "get_statistics"):
                    try:
                        statistics = agent.get_statistics()
                    except Exception as exc:  # pragma: no cover - safeguard
                        logger.debug(
                            "Failed to collect solver statistics (%s): %s",
                            getattr(agent, "name", "unknown"),
                            exc,
                        )
                result = SolverRunResult(
                    task=task,
                    output=output,
                    summary=summary,
                    raw_output=solver_output,
                    agent_name=getattr(agent, "name", self.solver.name),
                    statistics=statistics,
                )
                sanitized_result = {
                    "output": result.output,
                    "summary": result.summary,
                    "agent_name": result.agent_name,
                }
                if statistics is not None:
                    sanitized_result["statistics"] = statistics
                await self._notify(
                    "solver.completed",
                    {"task": task, "result": sanitized_result},
                )
                return result

            if semaphore:
                async with semaphore:
                    return await _run()
            return await _run()

        coroutines = [_execute(task) for task in tasks]
        return await asyncio.gather(*coroutines)

    async def _run_aggregator(
        self, context: PlanContext, results: Sequence[SolverRunResult]
    ) -> Any:
        if not self.aggregator:
            return None
        await self._notify(
            "aggregate.start", {"context": context, "solver_results": results}
        )
        aggregate = self.aggregator(context, results)
        if inspect.isawaitable(aggregate):
            aggregate = await aggregate  # type: ignore[assignment]
        await self._notify(
            "aggregate.completed",
            {"context": context, "solver_results": results, "output": aggregate},
        )
        return aggregate

    def _build_pipeline_statistics(
        self,
        plan_statistics: dict[str, Any] | None,
        solver_results: Sequence[SolverRunResult],
    ) -> dict[str, Any] | None:
        has_plan = bool(plan_statistics)
        solver_stats = [res for res in solver_results if res.statistics]
        if not has_plan and not solver_stats:
            return None

        total_calls = 0
        total_input_tokens = 0
        total_output_tokens = 0
        combined_calls: list[dict[str, Any]] = []

        def _accumulate(stat: dict[str, Any] | None, origin: str, agent_name: str) -> None:
            nonlocal total_calls, total_input_tokens, total_output_tokens, combined_calls
            if not stat:
                return
            total_calls += int(stat.get("total_calls", 0) or 0)

            def _resolve_total(key: str) -> int:
                value = stat.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
                running = stat.get("running_totals", {})
                if isinstance(running, dict):
                    running_val = running.get("input_tokens" if key == "total_input_tokens" else "output_tokens")
                    if isinstance(running_val, (int, float)):
                        return int(running_val)
                return 0

            total_input_tokens += _resolve_total("total_input_tokens")
            total_output_tokens += _resolve_total("total_output_tokens")

            calls = stat.get("calls")
            if isinstance(calls, list):
                for call in calls:
                    if isinstance(call, dict):
                        call_entry = call.copy()
                        call_entry.setdefault("origin", origin)
                        call_entry.setdefault("agent", agent_name)
                        combined_calls.append(call_entry)

        if plan_statistics:
            _accumulate(plan_statistics, "plan", plan_statistics.get("agent", self.planner.name))

        solver_statistics_entries: list[dict[str, Any]] = []
        for result in solver_stats:
            stats = result.statistics
            agent_name = result.agent_name
            _accumulate(stats, "solver", agent_name)
            solver_statistics_entries.append(
                {
                    "task": result.task,
                    "agent_name": agent_name,
                    "statistics": stats,
                }
            )

        totals = {
            "total_calls": total_calls,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }
        payload = {
            "plan": plan_statistics,
            "solvers": solver_statistics_entries,
            "totals": totals,
        }
        if combined_calls:
            payload["calls"] = combined_calls

        return payload

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Register a callback for pipeline progress events."""
        self.progress_callback = callback

    async def _notify(self, event: str, payload: dict[str, Any]) -> None:
        if not self.progress_callback:
            return
        try:
            outcome = self.progress_callback(event, payload)
            if inspect.isawaitable(outcome):
                await outcome  # type: ignore[func-returns-value]
        except Exception as exc:  # pragma: no cover - safeguard
            logger.debug(
                "PlanSolverPipeline progress callback failed (%s): %s", event, exc
            )


def create_plan_solver(
    *,
    name: str = "plan_solver",
    planner: PlanAgent,
    solver: SolverAgent,
    aggregator: AggregateFn | AsyncAggregateFn | None = None,
    concurrency: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> PlanSolverPipeline:
    """Factory helper for constructing plan→solve pipelines.

    Args:
        name: Identifier for the plan/solve pipeline.
        planner: Concrete PlanAgent implementation.
        solver: Concrete SolverAgent implementation used for each task.
        aggregator: Optional function combining all solver results.
        concurrency: Max concurrent solver executions (None = unlimited).
        progress_callback: Optional coroutine/callback for pipeline progress events.

    Returns:
        Configured PlanSolverPipeline ready to execute via `run()`.
    """

    if concurrency is not None and concurrency <= 0:
        raise ValueError("concurrency must be a positive integer when provided.")

    if not isinstance(planner, PlanAgent):
        raise TypeError("planner must be an instance of PlanAgent.")
    if not isinstance(solver, SolverAgent):
        raise TypeError("solver must be an instance of SolverAgent.")

    return PlanSolverPipeline(
        name=name,
        planner=planner,
        solver=solver,
        aggregator=aggregator,
        concurrency=concurrency,
        progress_callback=progress_callback,
    )


class PlanSolverSessionAgent(BaseAgent):
    """Wrap PlanSolverPipeline as a WebSocket-aware BaseAgent."""

    pipeline: PlanSolverPipeline
    event_namespace: str | None = Field(
        default=None,
        description="Optional prefix for emitted WebSocket events (e.g., plan.plan.start)",
    )
    broadcast_tasks: bool = Field(
        default=True,
        description="Whether to include full task payloads in plan.completed events",
    )

    class Config:
        arbitrary_types_allowed = True

    async def run(self, question: str | None = None) -> str:
        if not question:
            raise ValueError("PlanSolverSessionAgent requires a question to run.")

        self.update_memory("user", question)

        if self.state not in (AgentState.IDLE, AgentState.FINISHED):
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        self.state = AgentState.RUNNING
        self.pipeline.set_progress_callback(self._progress_callback)

        try:
            result = await self.pipeline.run(question)
            summary = result.plan_summary or "Plan & Solve pipeline completed."
            self.final_response = summary
            return summary
        finally:
            self.pipeline.set_progress_callback(None)
            self.state = AgentState.FINISHED

    async def step(self) -> str:
        raise NotImplementedError("PlanSolverSessionAgent executes via run().")

    async def _progress_callback(self, event: str, payload: dict[str, Any]) -> None:
        content = self._make_serializable(payload)

        if not self.broadcast_tasks and event == "plan.completed":
            content = {k: v for k, v in content.items() if k != "tasks"}

        await self._emit_event(event, content)

    async def _emit_event(self, event: str, content: Any) -> None:
        session = get_ws_session_context()
        if not session:
            return

        if self.event_namespace:
            event_type = f"{self.event_namespace}.{event}"
        else:
            event_type = event
        session_id = getattr(session, "session_id", None)
        ws_event = create_event(event_type, session_id=session_id, content=content)

        if hasattr(session, "_send_event"):
            await session._send_event(ws_event)  # type: ignore[attr-defined]
        else:
            await send_websocket_message(session.websocket, ws_event)  # type: ignore[attr-defined]

    def _make_serializable(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return {k: self._make_serializable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._make_serializable(v) for v in value]
        if hasattr(value, "dict"):
            try:
                return value.dict()
            except Exception:  # pragma: no cover - best effort
                pass
        if hasattr(value, "__dict__"):
            return {
                k: self._make_serializable(v)
                for k, v in vars(value).items()
                if not k.startswith("_")
            }
        return str(value)


def create_plan_solver_session_agent(
    pipeline: PlanSolverPipeline,
    *,
    name: str | None = None,
    event_namespace: str | None = None,
    broadcast_tasks: bool = True,
    max_retry_attempts: int = 0,
    retry_delay_seconds: float = 0.0,
) -> PlanSolverSessionAgent:
    """Factory to wrap a PlanSolverPipeline for WebSocket usage.

    Args:
        pipeline: The configured plan→solve pipeline to wrap.
        name: Optional agent name override.
        event_namespace: Prefix for emitted WebSocket events.
        broadcast_tasks: Whether to include full task payloads in events.
        max_retry_attempts: Number of retries allowed when execution fails.
        retry_delay_seconds: Delay between retries emitted by the session layer.
    """

    agent_name = name or pipeline.name
    namespace = event_namespace if event_namespace is not None else None

    return PlanSolverSessionAgent(
        name=agent_name,
        pipeline=pipeline,
        event_namespace=namespace,
        broadcast_tasks=broadcast_tasks,
        max_retry_attempts=max_retry_attempts,
        retry_delay_seconds=retry_delay_seconds,
    )
