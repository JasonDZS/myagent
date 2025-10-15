from __future__ import annotations

from typing import Any, Sequence

from myagent import create_react_agent
from myagent.agent import PlanAgent, SolverAgent, PlanContext, SolverRunResult

from .tools import (
    SectionPlanSubmissionTool,
    SectionDraftTool,
    SectionTask,
    ListLocalTemplatesTool,
    ListLocalDirTool,
    ReadLocalFileTool,
    RenderMarkdownReportTool,
)


class TemplatePlanAgent(PlanAgent):
    """Planner that proposes a set of report section tasks based on a template.

    The agent explores available templates and any user-provided files, then
    produces a sequenced plan of sections to drive the solver stage.
    """

    def __init__(self) -> None:
        super().__init__(name="template_plan")
        self._plan_tool = SectionPlanSubmissionTool()

    def build_agent(self):  # -> BaseAgent
        return create_react_agent(
            name="template_planner",
            tools=[ListLocalTemplatesTool(), ListLocalDirTool(), ReadLocalFileTool(), self._plan_tool],
            system_prompt=(
                "You are a planning agent that analyzes a markdown template and input files, "
                "then decomposes the report into structured sections.\n\n"
                "Instructions:\n"
                "- Use list_local_templates to discover templates; use list_local_dir to explore folders; "
                "read_local_file only reads files.\n"
                "- Identify the report title and section headings from the template.\n"
                "- Build a clear, ordered list of sections with objective and hints.\n"
                "- When ready, call submit_section_plan exactly once with tasks array.\n"
                "- Keep it concise; defer heavy lifting to solvers."
            ),
            next_step_prompt=(
                "Planning guide:\n"
                "1) Inspect template structure and style cues (list_local_templates / list_local_dir / read_local_file).\n"
                "2) Draft sections (id, title, objective).\n"
                "3) Add hints and required_inputs if specific files are needed.\n"
                "4) Call submit_section_plan once to finish.\n"
                "5) Use terminate to end."
            ),
            max_steps=18,
            max_observe=1200,
        )

    def extract_tasks(self, agent, plan_output: str) -> Sequence[SectionTask]:  # noqa: ANN001
        tasks = self._plan_tool.get_tasks()
        if not tasks:
            raise RuntimeError("Planner did not submit a section plan.")
        return tasks

    def extract_summary(self, agent, plan_output: str) -> str | None:  # noqa: ANN001
        if getattr(agent, "final_response", None):
            return agent.final_response  # type: ignore[attr-defined]
        return "Section plan prepared."

    def coerce_tasks(self, tasks: Sequence[Any]) -> Sequence[SectionTask]:
        coerced: list[SectionTask] = []
        for t in tasks:
            if isinstance(t, SectionTask):
                coerced.append(t)
            elif isinstance(t, dict):
                coerced.append(
                    SectionTask(
                        id=int(t["id"]),
                        title=str(t["title"]).strip(),
                        objective=str(t["objective"]).strip(),
                        hints=[str(x).strip() for x in (t.get("hints") or []) if str(x).strip()],
                        required_inputs=[str(x).strip() for x in (t.get("required_inputs") or []) if str(x).strip()],
                        notes=str(t.get("notes")).strip() if t.get("notes") else None,
                    )
                )
            else:
                raise ValueError(f"Unsupported task type: {type(t)}")
        return coerced


class TemplateSectionSolver(SolverAgent):
    """Per-section solver that synthesizes markdown content from inputs."""

    def __init__(self) -> None:
        super().__init__(name="template_section_solver")
        self._draft_tools: dict[int, SectionDraftTool] = {}

    def build_agent(self, task: SectionTask, *, context: PlanContext):  # noqa: ANN001
        draft_tool = SectionDraftTool(expected_id=task.id)
        self._draft_tools[task.id] = draft_tool

        return create_react_agent(
            name=f"section_solver_{task.id}",
            tools=[ListLocalDirTool(), ReadLocalFileTool(), draft_tool],
            system_prompt=(
                "You are a report section writer. Read relevant files and produce polished markdown for this section.\n"
                "Keep voice consistent with the template's style. Prefer concise bullets or short paragraphs as appropriate."
            ),
            next_step_prompt=(
                "Execution guide:\n"
                "1) Review task objective and hints.\n"
                "2) Explore directories with list_local_dir; read files with read_local_file (files only).\n"
                "3) Draft the section as markdown; include tables when fit.\n"
                "4) Call submit_section_draft once ready, then terminate."
            ),
            max_steps=20,
            max_observe=1500,
        )

    def build_request(self, task: SectionTask, *, context: PlanContext) -> str:
        lines: list[str] = [
            f"Section #{task.id}: {task.title}",
            f"Objective: {task.objective}",
        ]
        if task.hints:
            lines.append("Hints:\n- " + "\n- ".join(task.hints))
        if task.required_inputs:
            lines.append("Potential input files:\n- " + "\n- ".join(task.required_inputs))
        if task.notes:
            lines.append(f"Notes: {task.notes}")
        return "\n\n".join(lines)

    def extract_result(self, agent, solver_output: str, task: SectionTask, *, context: PlanContext) -> dict[str, Any]:  # noqa: ANN001
        draft_tool = self._draft_tools.pop(task.id, None)
        section = draft_tool.get_section() if draft_tool else None  # type: ignore[union-attr]
        if not section:
            raise RuntimeError(f"Solver for section {task.id} did not submit a draft.")
        return section

    def extract_summary(self, agent, solver_output: str, task: SectionTask, *, context: PlanContext) -> str | None:  # noqa: ANN001
        if getattr(agent, "final_response", None):
            return agent.final_response  # type: ignore[attr-defined]
        return f"Section {task.id}: {task.title} draft ready."


async def compile_report(context: PlanContext, results: Sequence[SolverRunResult]) -> dict[str, Any]:
    """Combine solver outputs and produce a Markdown report via RenderMarkdownReportTool."""
    sections: list[dict[str, Any]] = []
    for r in results:
        sec = r.output
        if not isinstance(sec, dict) or "id" not in sec:
            raise RuntimeError(f"Invalid solver output for section: {sec!r}")
        sections.append(sec)
    sections.sort(key=lambda s: s.get("id", 0))

    title = context.plan_summary or "Generated Report"
    renderer = RenderMarkdownReportTool()
    tool_result = await renderer.execute(title=title, sections=sections, output_path="reports/generated_report.md")
    extra = tool_result.extra or {}
    return {"sections": sections, "report": extra}
