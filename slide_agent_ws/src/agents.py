from __future__ import annotations

from typing import Any, Sequence

from myagent import create_react_agent
from myagent.agent import PlanAgent, SolverAgent, PlanContext, SolverRunResult

# Reuse database tools from the examples module to avoid duplication
from .data2ppt import (
    DatabaseQueryTool,
    DatabaseSchemaTool,
    GeneratePPTTool,
)

from .tools import SlidePlanSubmissionTool, SlideDraftTool, _normalize_slide_payload
from .slide_types import SlideTask


class Data2PPTPlanAgent(PlanAgent):
    """Planner that proposes a set of SlideTask items for a given question.

    The planner returns tasks via the SlidePlanSubmissionTool. These tasks are
    used downstream by the solver stage to generate slide drafts in parallel.
    """

    def __init__(self) -> None:
        super().__init__(name="ppt_plan")
        self._plan_tool = SlidePlanSubmissionTool()

    def build_agent(self):  # -> BaseAgent
        schema_tool = DatabaseSchemaTool()
        query_tool = DatabaseQueryTool()

        return create_react_agent(
            name="ppt_planner",
            tools=[schema_tool, query_tool, self._plan_tool],
            system_prompt=(
                "You are a senior analytics planner. Decompose the user's question into a concrete PPT plan: "
                "a sequence of slides that communicate insights clearly and visually. "
                "Leverage db_schema and db_query to understand data availability and shape the plan.\n\n"
                "Instructions:\n"
                "- Determine a logical slide flow (cover → metrics → breakdowns → conclusion).\n"
                "- Each slide must have an id (1..N), a title, and an objective.\n"
                "- Suggest 0..3 insights and optional SQL ideas for the solver to try.\n"
                "- When ready, call submit_slide_plan exactly once with the final tasks array.\n"
                "- Do not execute data-heavy queries here; defer to slide solvers."
            ),
            next_step_prompt=(
                "Plan guideline:\n"
                "1) Explore schema as needed.\n"
                "2) Draft slides with concise objectives.\n"
                "3) Provide query_suggestions when useful.\n"
                "4) Call submit_slide_plan once to finish planning.\n"
                "5) Use terminate to end."
            ),
            max_steps=18,
            max_observe=1200,
        )

    def extract_tasks(self, agent, plan_output: str) -> Sequence[SlideTask]:  # noqa: ANN001
        tasks = self._plan_tool.get_tasks()
        if not tasks:
            raise RuntimeError("Planner did not submit a slide plan.")
        return tasks

    def extract_summary(self, agent, plan_output: str) -> str | None:  # noqa: ANN001
        if getattr(agent, "final_response", None):
            return agent.final_response  # type: ignore[attr-defined]
        return "Slide plan prepared."

    def coerce_tasks(self, tasks: Sequence[Any]) -> Sequence[SlideTask]:
        # Accept either SlideTask or dict payloads
        coerced: list[SlideTask] = []
        for t in tasks:
            if isinstance(t, SlideTask):
                coerced.append(t)
            elif isinstance(t, dict):
                # Minimal validation
                try:
                    coerced.append(
                        SlideTask(
                            id=int(t["id"]),
                            title=str(t["title"]).strip(),
                            objective=str(t["objective"]).strip(),
                            insights=[str(x).strip() for x in (t.get("insights") or []) if str(x).strip()],
                            query_suggestions=[str(x).strip() for x in (t.get("query_suggestions") or []) if str(x).strip()],
                            chart_hint=str(t.get("chart_hint")).strip() if t.get("chart_hint") else None,
                            notes=str(t.get("notes")).strip() if t.get("notes") else None,
                        )
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    raise ValueError(f"Invalid task payload: {t}") from exc
            else:
                raise ValueError(f"Unsupported task type: {type(t)}")
        return coerced


class Data2PPTSlideSolver(SolverAgent):
    """Per-slide solver that analyzes data and produces a slide draft."""

    def __init__(self) -> None:
        super().__init__(name="ppt_slide_solver")
        self._draft_tools: dict[int, SlideDraftTool] = {}

    def build_agent(self, task: SlideTask, *, context: PlanContext):  # noqa: ANN001
        draft_tool = SlideDraftTool(expected_id=task.id)
        self._draft_tools[task.id] = draft_tool

        schema_tool = DatabaseSchemaTool()
        query_tool = DatabaseQueryTool()

        return create_react_agent(
            name=f"ppt_slide_solver_{task.id}",
            tools=[schema_tool, query_tool, draft_tool],
            system_prompt=(
                "You are a data analyst tasked with building one PPT slide.\n"
                "Use db_schema and db_query to gather evidence supporting this slide's objective.\n"
                "Synthesize concise insights and present them as a single, clear sentence (<=100 chars).\n"
                "Limit slides to at most two charts and include chart-ready data if valuable.\n"
                "Submit the final slide via submit_slide_draft exactly once. Do NOT call generate_ppt."
            ),
            next_step_prompt=(
                "Execution guide:\n"
                "1) Review brief and explore data with db_schema/db_query.\n"
                "2) Draft <=100 char single-paragraph text (inline Markdown ok; no lists/line breaks).\n"
                "3) Add up to two charts when relevant.\n"
                "4) Call submit_slide_draft once ready, then terminate."
            ),
            max_steps=25,
            max_observe=1500,
        )

    def build_request(self, task: SlideTask, *, context: PlanContext) -> str:
        parts: list[str] = [
            f"Slide #{task.id}: {task.title}",
            f"Objective: {task.objective}",
        ]
        if task.insights:
            parts.append("Suggested insights:\n- " + "\n- ".join(task.insights))
        if task.query_suggestions:
            parts.append("SQL ideas:\n- " + "\n- ".join(task.query_suggestions))
        if task.chart_hint:
            parts.append(f"Chart hint: {task.chart_hint}")
        if task.notes:
            parts.append(f"Additional notes: {task.notes}")
        return "\n\n".join(parts)

    def extract_result(self, agent, solver_output: str, task: SlideTask, *, context: PlanContext) -> dict[str, Any]:  # noqa: ANN001
        draft_tool = self._draft_tools.pop(task.id, None)
        slide = draft_tool.get_slide() if draft_tool else None
        if not slide:
            raise RuntimeError(f"Solver for slide {task.id} did not submit a slide draft.")
        return slide

    def extract_summary(self, agent, solver_output: str, task: SlideTask, *, context: PlanContext) -> str | None:  # noqa: ANN001
        if getattr(agent, "final_response", None):
            return agent.final_response  # type: ignore[attr-defined]
        return f"Slide {task.id}: {task.title} draft ready."


async def compile_presentation(context: PlanContext, results: Sequence[SolverRunResult]) -> dict[str, Any]:
    """Combine solver outputs and produce PPT JSON via GeneratePPTTool.

    Returns a dict that includes normalized slides and the tool result under
    'ppt_result'.
    """
    slides: list[dict[str, Any]] = []
    for item in results:
        slide = item.output
        if not isinstance(slide, dict):
            raise RuntimeError(f"Solver output is not a slide dict: {slide!r}")
        if "id" not in slide:
            raise RuntimeError(f"Slide dict missing 'id': {slide!r}")
        slides.append(_normalize_slide_payload(slide))

    slides.sort(key=lambda s: s.get("id", 0))
    ppt_tool = GeneratePPTTool()
    ppt_result = await ppt_tool.execute(slides=slides)  # type: ignore[arg-type]
    return {"slides": slides, "ppt_result": ppt_result}
