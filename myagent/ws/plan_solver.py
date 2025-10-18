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

from myagent.logger import logger
from myagent.schema import AgentState
from myagent.ws import get_ws_session_context, send_websocket_message
from myagent.ws.events import (
    create_event,
    AgentEvents,
    PlanEvents,
    SolverEvents,
    AggregateEvents,
    PipelineEvents,
)
from myagent.agent.base import BaseAgent
from myagent.stats import get_stats_manager

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
    # List of per-call statistics (each item is one LLM call record)
    plan_statistics: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class SolverRunResult:
    """Represents the outcome of a single solver agent run."""

    task: Any
    output: Any
    summary: str | None
    raw_output: str | None
    agent_name: str
    # List of per-call statistics for this solver run
    statistics: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class PlanSolveResult:
    """Aggregate outcome of the plan → solve pipeline."""

    context: PlanContext
    solver_results: Sequence[SolverRunResult]
    aggregate_output: Any = None
    # Unified list of per-call statistics across the pipeline
    statistics: list[dict[str, Any]] | None = None
    # Aggregated runtime metrics snapshot (agents/tools/models)
    metrics: dict[str, Any] | None = None

    @property
    def tasks(self) -> Sequence[Any]:
        return self.context.tasks

    @property
    def plan_summary(self) -> str | None:
        return self.context.plan_summary

    @property
    def plan_statistics(self) -> list[dict[str, Any]] | None:
        return self.context.plan_statistics

    @property
    def question(self) -> str:
        return self.context.question

    @property
    def pipeline_statistics(self) -> list[dict[str, Any]] | None:
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

    # -- Optional hook -------------------------------------------------
    def coerce_tasks(self, tasks: Sequence[Any]) -> Sequence[Any]:
        """Optionally coerce user-provided/edited tasks into the planner's task type.

        Default implementation returns tasks unchanged. Concrete planners can
        override this to convert dictionaries into domain-specific task objects
        (e.g., dataclasses) to satisfy solver expectations.
        """
        return tasks


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
        # Runtime management for per-task control
        self._active_solver_tasks: dict[str, asyncio.Task] = {}
        self._task_key_map: dict[str, Any] = {}
        self._cancel_requests: set[str] = set()
        self._restart_requests: set[str] = set()
        self._results_map: dict[str, SolverRunResult] = {}
        self._lock = asyncio.Lock()

    async def run(self, question: str) -> PlanSolveResult:
        """Execute the plan → solve pipeline for the provided question.

        Backwards-compatible wrapper that performs planning, then solving+aggregation.
        """
        context = await self.plan(question)
        return await self.solve_and_aggregate(context)

    async def plan(self, question: str) -> PlanContext:
        """Run planning stage and emit plan events, returning a PlanContext."""
        await self._notify(PlanEvents.START, {"question": question})

        plan_agent = self.planner.build_agent()
        plan_request = self.planner.build_request(question)
        plan_output = await plan_agent.run(plan_request)
        tasks = list(self.planner.extract_tasks(plan_agent, plan_output))

        if not tasks:
            raise RuntimeError(
                f"Planner '{self.planner.name}' produced no tasks for question: {question}"
            )

        plan_summary = self.planner.extract_summary(plan_agent, plan_output)
        plan_statistics: list[dict[str, Any]] | None = None
        if hasattr(plan_agent, "get_statistics"):
            try:
                stats_obj = plan_agent.get_statistics()
                # Prefer per-call records; fall back to wrapping the object
                calls = []
                if isinstance(stats_obj, dict):
                    maybe_calls = stats_obj.get("calls")
                    if isinstance(maybe_calls, list):
                        calls = [c.copy() for c in maybe_calls if isinstance(c, dict)]
                if not calls and isinstance(stats_obj, dict):
                    calls = [stats_obj]

                # Annotate origin/agent for easier downstream attribution
                agent_name = getattr(plan_agent, "name", self.planner.name)
                stats_model = None
                try:
                    if isinstance(stats_obj, dict):
                        stats_model = stats_obj.get("model")
                except Exception:
                    stats_model = None
                if not stats_model:
                    # Fallback to the agent's configured LLM model
                    stats_model = getattr(getattr(plan_agent, "llm", None), "model", None)
                for c in calls:
                    c.setdefault("origin", "plan")
                    c.setdefault("agent", agent_name)
                    # Ensure model name is present for UI display
                    if isinstance(c, dict) and not c.get("model"):
                        if stats_model:
                            c["model"] = stats_model
                plan_statistics = calls or None
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

        # Best-effort global metrics snapshot after planning phase
        metrics_snapshot = None
        try:
            metrics_snapshot = get_stats_manager().snapshot()
        except Exception:
            metrics_snapshot = None

        await self._notify(
            PlanEvents.COMPLETED,
            {
                "tasks": tasks,
                "plan_summary": plan_summary,
                # statistics is a List[Dict] (per-call records); may be omitted if None
                **({"statistics": plan_statistics} if plan_statistics is not None else {}),
                **({"metrics": metrics_snapshot} if metrics_snapshot is not None else {}),
            },
        )

        return context

    async def solve_and_aggregate(self, context: PlanContext) -> PlanSolveResult:
        """Execute solver stage for the given context and aggregate results."""
        tasks = list(context.tasks)
        solver_results = await self._run_solvers(tasks, context)
        aggregate_output = await self._run_aggregator(context, solver_results)
        pipeline_statistics = self._build_pipeline_statistics(
            context.plan_statistics, solver_results
        )
        # Best-effort global metrics snapshot for the entire pipeline
        metrics_snapshot = None
        try:
            metrics_snapshot = get_stats_manager().snapshot()
        except Exception:
            metrics_snapshot = None

        await self._notify(
            PipelineEvents.COMPLETED,
            {
                "context": context,
                "solver_results": solver_results,
                "aggregate_output": aggregate_output,
                **({"statistics": pipeline_statistics} if pipeline_statistics is not None else {}),
                **({"metrics": metrics_snapshot} if metrics_snapshot is not None else {}),
            },
        )

        return PlanSolveResult(
            context=context,
            solver_results=solver_results,
            aggregate_output=aggregate_output,
            statistics=pipeline_statistics,
            metrics=metrics_snapshot,
        )

    async def _run_solvers(
        self, tasks: Sequence[Any], context: PlanContext
    ) -> list[SolverRunResult]:
        """Run solvers with per-task cancel/restart support.

        This implementation launches a task per slide and then waits
        dynamically for completions, while allowing external cancellation
        and restart requests to affect individual tasks without impacting
        others.
        """
        semaphore = asyncio.Semaphore(self.concurrency) if self.concurrency else None

        async def _execute(task: Any) -> SolverRunResult:

            async def _run() -> SolverRunResult:
                # Emit start only when the task actually acquires a slot
                await self._notify(SolverEvents.START, {"task": task})
                agent = self.solver.build_agent(task, context=context)
                request = self.solver.build_request(task, context=context)
                solver_output = await agent.run(request)
                output = self.solver.extract_result(
                    agent, solver_output, task, context=context
                )
                summary = self.solver.extract_summary(
                    agent, solver_output, task, context=context
                )
                statistics: list[dict[str, Any]] | None = None
                if hasattr(agent, "get_statistics"):
                    try:
                        stats_obj = agent.get_statistics()
                        calls = []
                        if isinstance(stats_obj, dict):
                            maybe_calls = stats_obj.get("calls")
                            if isinstance(maybe_calls, list):
                                calls = [c.copy() for c in maybe_calls if isinstance(c, dict)]
                        if not calls and isinstance(stats_obj, dict):
                            calls = [stats_obj]
                        # Annotate origin/agent for downstream attribution
                        stats_model = None
                        try:
                            if isinstance(stats_obj, dict):
                                stats_model = stats_obj.get("model")
                        except Exception:
                            stats_model = None
                        if not stats_model:
                            stats_model = getattr(getattr(agent, "llm", None), "model", None)
                        for c in calls:
                            c.setdefault("origin", "solver")
                            c.setdefault("agent", getattr(agent, "name", self.solver.name))
                            if isinstance(c, dict) and not c.get("model") and stats_model:
                                c["model"] = stats_model
                        statistics = calls or None
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
                # Attach model used by the solver agent for easier client display
                try:
                    if 'stats_model' in locals() and stats_model:
                        sanitized_result["model"] = stats_model
                    else:
                        maybe_model = getattr(getattr(agent, "llm", None), "model", None)
                        if maybe_model:
                            sanitized_result["model"] = maybe_model
                except Exception:
                    pass
                if statistics is not None:
                    # statistics is a List[Dict] (per-call records)
                    sanitized_result["statistics"] = statistics
                await self._notify(
                    SolverEvents.COMPLETED,
                    {"task": task, "result": sanitized_result},
                )
                return result

            if semaphore:
                async with semaphore:
                    return await _run()
            return await _run()

        # Helpers to bind keys
        def _task_key(task: Any) -> str:
            try:
                tid = getattr(task, "id", None)
                if tid is None and isinstance(task, dict):
                    tid = task.get("id")
                return f"task:{tid}" if tid is not None else f"task_obj:{id(task)}"
            except Exception:
                return f"task_obj:{id(task)}"

        async def _launch(task: Any) -> None:
            key = _task_key(task)
            coro = _execute(task)
            fut = asyncio.create_task(coro)
            async with self._lock:
                self._active_solver_tasks[key] = fut
                self._task_key_map[key] = task

        # Initialize
        async with self._lock:
            self._active_solver_tasks.clear()
            self._task_key_map = { _task_key(t): t for t in tasks }
            self._cancel_requests.clear()
            self._restart_requests.clear()
            self._results_map.clear()

        for t in tasks:
            await _launch(t)

        # Dynamic wait loop
        while True:
            async with self._lock:
                pending = list(self._active_solver_tasks.items())
                restart_keys = list(self._restart_requests)

            if not pending and not restart_keys:
                break

            # Schedule restarts that are requested but not active
            for rkey in restart_keys:
                async with self._lock:
                    is_active = rkey in self._active_solver_tasks
                    task_obj = self._task_key_map.get(rkey)
                    if task_obj is None:
                        # Unknown key; ignore
                        self._restart_requests.discard(rkey)
                        continue
                if not is_active:
                    await self._notify(SolverEvents.RESTARTED, {"task": task_obj})
                    await _launch(task_obj)
                    async with self._lock:
                        self._restart_requests.discard(rkey)

            # Recompute pending set after possible launches
            async with self._lock:
                futures = list(self._active_solver_tasks.items())

            if not futures:
                continue

            # Wait for any completion
            done, _pending = await asyncio.wait(
                {f for _, f in futures}, return_when=asyncio.FIRST_COMPLETED
            )

            # Process completed
            for done_fut in done:
                # Find key by value
                key_for_done = None
                for k, f in futures:
                    if f is done_fut:
                        key_for_done = k
                        break
                if key_for_done is None:
                    continue

                async with self._lock:
                    # Remove from active
                    self._active_solver_tasks.pop(key_for_done, None)
                    task_obj = self._task_key_map.get(key_for_done)

                try:
                    res: SolverRunResult = await done_fut
                except asyncio.CancelledError:
                    # Cancelled: emit event and continue; restart is handled above
                    await self._notify(SolverEvents.CANCELLED, {"task": task_obj})
                    continue
                except Exception as exc:  # pragma: no cover - safeguard
                    logger.error("Solver task failed for %s: %s", key_for_done, exc)
                    continue

                # Store successful result
                async with self._lock:
                    self._results_map[key_for_done] = res

        # Collect results in original order (where available)
        results: list[SolverRunResult] = []
        for t in tasks:
            key = _task_key(t)
            res = self._results_map.get(key)
            if res is not None:
                results.append(res)
        # Also include any restarted-only completions (if original was cancelled)
        known_keys = { _task_key(t) for t in tasks }
        for k, res in self._results_map.items():
            if k not in known_keys:
                results.append(res)

        return results

    # ---- External control API for per-task management ----
    def _task_key(self, task: Any) -> str:
        try:
            tid = getattr(task, "id", None)
            if tid is None and isinstance(task, dict):
                tid = task.get("id")
            return f"task:{tid}" if tid is not None else f"task_obj:{id(task)}"
        except Exception:
            return f"task_obj:{id(task)}"

    async def request_cancel_solver_task(self, task_id: int | str) -> bool:
        """Cancel a running solver task by id (slide id).

        Returns True if a matching active task was found and cancelled.
        """
        # Build key candidates
        key = f"task:{task_id}"
        async with self._lock:
            fut = self._active_solver_tasks.get(key)
        if fut and not fut.done():
            fut.cancel()
            return True
        return False

    async def request_restart_solver_task(self, task_id: int | str) -> bool:
        """Request a solver task to be restarted (cancel if running, then relaunch)."""
        key = f"task:{task_id}"
        async with self._lock:
            self._restart_requests.add(key)
            fut = self._active_solver_tasks.get(key)
        if fut and not fut.done():
            fut.cancel()
        return True

    async def _run_aggregator(
        self, context: PlanContext, results: Sequence[SolverRunResult]
    ) -> Any:
        if not self.aggregator:
            return None
        await self._notify(
            AggregateEvents.START, {"context": context, "solver_results": results}
        )
        aggregate = self.aggregator(context, results)
        if inspect.isawaitable(aggregate):
            aggregate = await aggregate  # type: ignore[assignment]
        await self._notify(
            AggregateEvents.COMPLETED,
            {"context": context, "solver_results": results, "output": aggregate},
        )
        return aggregate

    def _build_pipeline_statistics(
        self,
        plan_statistics: list[dict[str, Any]] | None,
        solver_results: Sequence[SolverRunResult],
    ) -> list[dict[str, Any]] | None:
        """Build unified per-call statistics list for the entire pipeline.

        Returns a List[Dict], where each dict represents a single LLM call.
        """
        combined_calls: list[dict[str, Any]] = []

        # Helper to append calls while ensuring origin/agent annotations
        def _append_calls(calls: list[dict[str, Any]] | None, origin: str, agent_name: str) -> None:
            if not calls:
                return
            for call in calls:
                if not isinstance(call, dict):
                    continue
                entry = call.copy()
                entry.setdefault("origin", origin)
                entry.setdefault("agent", agent_name)
                combined_calls.append(entry)

        if plan_statistics:
            # Try to infer agent name from any call entry; fallback to planner name
            agent_name = self.planner.name
            if isinstance(plan_statistics, list) and plan_statistics:
                a = plan_statistics[0]
                if isinstance(a, dict) and isinstance(a.get("agent"), str):
                    agent_name = a.get("agent") or agent_name
            _append_calls(plan_statistics, "plan", agent_name)

        for result in solver_results:
            if result.statistics:
                _append_calls(result.statistics, "solver", result.agent_name)

        return combined_calls or None

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
    require_plan_confirmation: bool = Field(
        default=False,
        description="If true, waits for user confirmation after planning to allow editing tasks before solving.",
    )
    plan_confirmation_timeout: int = Field(
        default=300,
        description="Timeout (seconds) for plan confirmation before proceeding or aborting.",
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
        # Internal control flags/state
        self._planning_task: asyncio.Task | None = None
        self._last_plan_confirm_step_id: str | None = None
        self._replan_requested: bool = False
        self._replan_question: str | None = None
        self._solving_started: bool = False
        # Keep last context and results for post-completion single-task rerun
        self._last_context: PlanContext | None = None
        self._last_solver_results: list[SolverRunResult] = []

        try:
            if not self.require_plan_confirmation:
                # Simple mode: plan+solve in one shot
                result = await self.pipeline.run(question)
                summary = result.plan_summary or "Plan & Solve pipeline completed."
                self.final_response = summary
                return summary

            # Plan/Confirm with replan support
            context: PlanContext | None = None
            while True:
                # Launch planning as a task so it can be cancelled
                plan_question = self._replan_question or question
                self._planning_task = asyncio.create_task(self.pipeline.plan(plan_question))
                try:
                    context = await self._planning_task
                except asyncio.CancelledError:
                    await self._emit_event(PlanEvents.CANCELLED, {"reason": "cancelled"})
                    if self._replan_requested:
                        # Clear flag and re-run planning
                        self._replan_requested = False
                        # Keep any updated question across loops
                        continue
                    summary = "Plan was cancelled"
                    self.final_response = summary
                    return summary
                finally:
                    self._planning_task = None

                # Ask user to confirm/edit tasks
                edited_tasks, proceed = await self._await_plan_confirmation(context)
                if not proceed:
                    # If a replan was requested during confirmation, loop to replan
                    if self._replan_requested:
                        self._replan_requested = False
                        continue
                    summary = "Plan was declined by user."
                    self.final_response = summary
                    return summary

                # If replan was requested during confirmation, loop to replan
                if self._replan_requested:
                    self._replan_requested = False
                    continue

                # Coerce edited tasks if provided
                if edited_tasks is not None:
                    try:
                        edited_tasks = list(self.pipeline.planner.coerce_tasks(edited_tasks))
                    except Exception as exc:
                        await self._emit_event(
                            PlanEvents.COERCION_ERROR,
                            {
                                "message": "Failed to coerce edited tasks; aborting.",
                                "error": str(exc),
                            },
                        )
                        summary = f"Plan confirmation contained invalid tasks: {exc}"
                        self.final_response = summary
                        return summary
                    context = PlanContext(
                        name=context.name,
                        question=context.question,
                        tasks=edited_tasks,
                        plan_summary=context.plan_summary,
                        raw_plan_output=context.raw_plan_output,
                        plan_statistics=context.plan_statistics,
                    )

                break  # Proceed to solver

            # Proceed to solver + aggregation with per-task control
            assert context is not None
            self._solving_started = True
            result = await self.pipeline.solve_and_aggregate(context)
            summary = result.plan_summary or "Plan & Solve pipeline completed."
            self.final_response = summary
            # Cache context and results for potential post-completion restarts
            self._last_context = context
            try:
                self._last_solver_results = list(result.solver_results)
            except Exception:
                self._last_solver_results = []
            return summary
        finally:
            self.pipeline.set_progress_callback(None)
            self.state = AgentState.FINISHED

    async def step(self) -> str:
        raise NotImplementedError("PlanSolverSessionAgent executes via run().")

    async def _progress_callback(self, event: str, payload: dict[str, Any]) -> None:
        content = self._make_serializable(payload)

        if not self.broadcast_tasks and event == PlanEvents.COMPLETED:
            content = {k: v for k, v in content.items() if k != "tasks"}

        await self._emit_event(event, content)

    async def _emit_event(self, event: str, content: Any, *, metadata: dict[str, Any] | None = None, step_id: str | None = None) -> None:
        session = get_ws_session_context()
        if not session:
            return

        if self.event_namespace:
            event_type = f"{self.event_namespace}.{event}"
        else:
            event_type = event
        session_id = getattr(session, "session_id", None)
        # Ensure payloads are JSON-serializable
        serial_content = self._make_serializable(content)
        serial_metadata = self._make_serializable(metadata) if metadata is not None else None
        ws_event = create_event(event_type, session_id=session_id, content=serial_content, metadata=serial_metadata, step_id=step_id)

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

    async def _await_plan_confirmation(self, context: PlanContext) -> tuple[list[Any] | None, bool]:
        """Send a plan confirmation request and wait for user's response.

        Returns: (edited_tasks, proceed)
        - edited_tasks: if user provided a new task list, return it, otherwise None
        - proceed: True to continue to solver, False if user declined
        """
        session = get_ws_session_context()
        if not session:
            # Not running under WS, proceed without confirmation
            return None, True

        import uuid

        step_id = f"confirm_plan_{uuid.uuid4().hex[:8]}"
        self._last_plan_confirm_step_id = step_id

        # Emit a user confirmation request with full tasks as metadata
        try:
            ws_event = create_event(
                AgentEvents.USER_CONFIRM,
                session_id=getattr(session, "session_id", None),
                step_id=step_id,
                content="Confirm plan before solving",
                metadata={
                    "requires_confirmation": True,
                    "scope": "plan",
                    "plan_summary": context.plan_summary,
                    "tasks": self._make_serializable(list(context.tasks)),
                },
            )
            if hasattr(session, "_send_event"):
                await session._send_event(ws_event)  # type: ignore[attr-defined]
            else:
                await send_websocket_message(session.websocket, ws_event)  # type: ignore[attr-defined]
        except Exception:
            # Best effort: in case event emission fails, proceed
            return None, True

        # Wait for user response
        try:
            if hasattr(session, "_wait_for_user_response"):
                response = await session._wait_for_user_response(step_id, timeout=self.plan_confirmation_timeout)  # type: ignore[attr-defined]
            else:
                return None, True
        except Exception:
            return None, True

        confirmed = bool(response.get("confirmed", False)) if isinstance(response, dict) else False
        if not confirmed:
            return None, False

        edited_tasks = None
        if isinstance(response, dict) and "tasks" in response:
            maybe_tasks = response.get("tasks")
            if isinstance(maybe_tasks, list):
                edited_tasks = maybe_tasks

        return edited_tasks, True

    # ---- External control API exposed to WebSocket server ----
    async def solve_tasks(
        self,
        tasks: list[Any] | Any,
        *,
        question: str | None = None,
        plan_summary: str | None = None,
    ) -> str:
        """Run solver-only flow using client-provided tasks, bypassing planning.

        Direct-task mode emits only solver.start/solver.completed events; it does
        not emit plan.completed, aggregate.*, pipeline.completed, or final_answer.
        """
        # Normalize tasks to a list
        raw_tasks: list[Any]
        if isinstance(tasks, list):
            raw_tasks = tasks
        else:
            raw_tasks = [tasks]

        if not raw_tasks:
            raise ValueError("solve_tasks requires at least one task")

        # Allow re-use after completion
        if self.state not in (AgentState.IDLE, AgentState.FINISHED):
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        # Coerce tasks to the planner's expected type if supported
        try:
            coerced_tasks = list(self.pipeline.planner.coerce_tasks(raw_tasks))
        except Exception as exc:
            await self._emit_event(
                PlanEvents.COERCION_ERROR,
                {
                    "message": "Failed to coerce client-provided tasks; aborting.",
                    "error": str(exc),
                },
            )
            raise

        # Build a minimal context
        q = (question or "Direct task execution").strip()
        psummary = plan_summary or "Tasks provided by client"
        context = PlanContext(
            name=self.pipeline.name,
            question=q,
            tasks=coerced_tasks,
            plan_summary=psummary,
            raw_plan_output=None,
            plan_statistics=None,
        )

        # Transition to RUNNING and attach progress callback
        self.state = AgentState.RUNNING
        # Only forward solver.* events via the standard progress callback
        self.pipeline.set_progress_callback(self._progress_callback)
        self._solving_started = True

        try:
            # Run solvers only; do not aggregate or emit pipeline-level events
            results = await self.pipeline._run_solvers(coerced_tasks, context)  # type: ignore[attr-defined]

            # Cache for potential restart support
            self._last_context = context
            try:
                self._last_solver_results = list(result.solver_results)
            except Exception:
                self._last_solver_results = []

            # Cache last context and results (for potential restarts)
            self._last_context = context
            try:
                self._last_solver_results = list(results)
            except Exception:
                self._last_solver_results = []
            # Do not emit final answer; return a simple status string
            return "OK"
        finally:
            self.pipeline.set_progress_callback(None)
            self.state = AgentState.FINISHED

    async def cancel_plan(self) -> bool:
        """Cancel planning phase if in progress or awaiting confirmation."""
        # If planning task is running, cancel it
        if isinstance(self._planning_task, asyncio.Task) and not self._planning_task.done():
            self._planning_task.cancel()
            return True
        # If awaiting confirmation, auto-decline to abort this run
        session = get_ws_session_context()
        if session and self._last_plan_confirm_step_id:
            try:
                await session.handle_user_response(self._last_plan_confirm_step_id, {"confirmed": False, "reason": "cancel_plan"})  # type: ignore[attr-defined]
                return True
            except Exception:
                return False
        return False

    async def replan(self, question: str | None = None) -> bool:
        """Request re-planning. Allowed only before solving starts."""
        if self._solving_started:
            # Replan not supported once solving has started
            await self._emit_event(AgentEvents.ERROR, {"message": "Cannot replan after solving has started"})
            return False
        self._replan_requested = True
        if question:
            self._replan_question = str(question)
        # Cancel current plan or decline confirmation to trigger loop
        await self.cancel_plan()
        return True

    async def cancel_solver_task(self, task_id: int | str) -> bool:
        if not self._solving_started:
            return False
        try:
            return await self.pipeline.request_cancel_solver_task(task_id)
        except Exception:
            return False

    async def restart_solver_task(self, task_id: int | str) -> bool:
        # Case 1: during solving, delegate to pipeline's in-run restart
        if self._solving_started:
            try:
                return await self.pipeline.request_restart_solver_task(task_id)
            except Exception:
                return False

        # Case 2: after completion, rerun a single task and re-aggregate
        context = getattr(self, "_last_context", None)
        if not context:
            return False

        def _tid(x: Any) -> Any:
            try:
                if isinstance(x, dict):
                    return x.get("id")
                return getattr(x, "id", None)
            except Exception:
                return None

        target_task = None
        for t in context.tasks:
            if _tid(t) == task_id or str(_tid(t)) == str(task_id):
                target_task = t
                break
        if target_task is None:
            return False

        # Emit solver.restarted for visibility
        await self._emit_event(SolverEvents.RESTARTED, {"task": target_task})

        # Ensure progress callback active
        self.pipeline.set_progress_callback(self._progress_callback)

        # Run single-task solver
        try:
            new_results = await self.pipeline._run_solvers([target_task], context)  # type: ignore[attr-defined]
        except Exception:
            return False
        if not new_results:
            return False
        new_res = new_results[0]

        # Merge with previous results, replacing same task id
        updated_results: list[SolverRunResult] = []
        replaced = False
        for r in getattr(self, "_last_solver_results", []) or []:
            if _tid(r.task) == _tid(target_task):
                updated_results.append(new_res)
                replaced = True
            else:
                updated_results.append(r)
        if not replaced:
            updated_results.append(new_res)

        # Re-run aggregator to emit updated aggregate events
        try:
            await self.pipeline._run_aggregator(context, updated_results)  # type: ignore[attr-defined]
            self._last_solver_results = updated_results
            return True
        except Exception:
            return False


def create_plan_solver_session_agent(
    pipeline: PlanSolverPipeline,
    *,
    name: str | None = None,
    event_namespace: str | None = None,
    broadcast_tasks: bool = True,
    max_retry_attempts: int = 0,
    retry_delay_seconds: float = 0.0,
    require_plan_confirmation: bool = False,
    plan_confirmation_timeout: int = 300,
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
        require_plan_confirmation=require_plan_confirmation,
        plan_confirmation_timeout=plan_confirmation_timeout,
    )
