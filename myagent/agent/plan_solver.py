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
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Sequence

from .base import BaseAgent

AggregateFn = Callable[["PlanContext", Sequence["SolverRunResult"]], Any]
AsyncAggregateFn = Callable[["PlanContext", Sequence["SolverRunResult"]], Awaitable[Any]]


@dataclass(frozen=True)
class PlanContext:
    """Context shared from planning to solving and aggregation stages."""

    name: str
    question: str
    tasks: Sequence[Any]
    plan_summary: str | None
    raw_plan_output: str | None


@dataclass(frozen=True)
class SolverRunResult:
    """Represents the outcome of a single solver agent run."""

    task: Any
    output: Any
    summary: str | None
    raw_output: str | None
    agent_name: str


@dataclass(frozen=True)
class PlanSolveResult:
    """Aggregate outcome of the plan → solve pipeline."""

    context: PlanContext
    solver_results: Sequence[SolverRunResult]
    aggregate_output: Any = None

    @property
    def tasks(self) -> Sequence[Any]:
        return self.context.tasks

    @property
    def plan_summary(self) -> str | None:
        return self.context.plan_summary

    @property
    def question(self) -> str:
        return self.context.question


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
    ) -> None:
        self.name = name
        self.planner = planner
        self.solver = solver
        self.aggregator = aggregator
        self.concurrency = concurrency

    async def run(self, question: str) -> PlanSolveResult:
        """Execute the plan → solve pipeline for the provided question."""
        plan_agent = self.planner.build_agent()
        plan_request = self.planner.build_request(question)
        plan_output = await plan_agent.run(plan_request)
        tasks = list(self.planner.extract_tasks(plan_agent, plan_output))

        if not tasks:
            raise RuntimeError(
                f"Planner '{self.planner.name}' produced no tasks for question: {question}"
            )

        plan_summary = self.planner.extract_summary(plan_agent, plan_output)
        context = PlanContext(
            name=self.name,
            question=question,
            tasks=tasks,
            plan_summary=plan_summary,
            raw_plan_output=plan_output,
        )

        solver_results = await self._run_solvers(tasks, context)
        aggregate_output = await self._run_aggregator(context, solver_results)

        return PlanSolveResult(
            context=context,
            solver_results=solver_results,
            aggregate_output=aggregate_output,
        )

    async def _run_solvers(
        self, tasks: Sequence[Any], context: PlanContext
    ) -> list[SolverRunResult]:
        semaphore = (
            asyncio.Semaphore(self.concurrency) if self.concurrency else None
        )

        async def _execute(task: Any) -> SolverRunResult:
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
                return SolverRunResult(
                    task=task,
                    output=output,
                    summary=summary,
                    raw_output=solver_output,
                    agent_name=getattr(agent, "name", self.solver.name),
                )

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
        aggregate = self.aggregator(context, results)
        if inspect.isawaitable(aggregate):
            return await aggregate  # type: ignore[return-value]
        return aggregate


def create_plan_solver(
    *,
    name: str = "plan_solver",
    planner: PlanAgent,
    solver: SolverAgent,
    aggregator: AggregateFn | AsyncAggregateFn | None = None,
    concurrency: int | None = None,
) -> PlanSolverPipeline:
    """Factory helper for constructing plan→solve pipelines.

    Args:
        name: Identifier for the plan/solve pipeline.
        planner: Concrete PlanAgent implementation.
        solver: Concrete SolverAgent implementation used for each task.
        aggregator: Optional function combining all solver results.
        concurrency: Max concurrent solver executions (None = unlimited).

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
    )
