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
    SummarizeFilenamesTool,
    SplitMarkdownTreeTool,
    parse_markdown_to_tree,
    _vfs_list_dir,
    _vfs_read_file,
    _vfs_write_file,
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
            tools=[
                ListLocalTemplatesTool(),
                ListLocalDirTool(),
                SummarizeFilenamesTool(),
                SplitMarkdownTreeTool(),
                self._plan_tool,
            ],
            system_prompt=(
                "You are a planning agent that analyzes a preloaded template (Markdown or HTML) and input files, "
                "then decomposes the report into structured sections.\n\n"
                "Instructions:\n"
                "- The server preloads template and knowledge base files into a session-scoped virtual file system (VFS).\n"
                "- The VFS provides (no local files are used):\n"
                "  * template/<name>.md (normalized from HTML when necessary; prefer .md files)\n"
                "  * template/<name>.html (original HTML, when available)\n"
                "  * datasets/<file>.json (knowledge base files)\n"
                "- Use list_local_templates to see templates in VFS; use list_local_dir to explore VFS folders (e.g., datasets).\n"
                "- Optionally call summarize_filenames to quickly get 1-sentence descriptions of dataset files based on filenames.\n"
                "- To inspect the template structure, you MAY call split_markdown_tree on the markdown template to preview leaves (smallest sections).\n"
                "- IMPORTANT: Titles and template snippets for each section are auto-filled by the system based on the template leaves.\n"
                "  You only need to propose per-section reference files (required_inputs) and optional hints/notes.\n"
                "- When ready, call submit_section_plan exactly once with tasks array including 'id' and any 'required_inputs'/'hints'/'notes'.\n"
                "  Fields 'title', 'template', and 'objective' will be ignored/overwritten by the system."
            ),
            next_step_prompt=(
                "Planning guide:\n"
                "1) Inspect template under template/ (prefer .md). Explore datasets/ via list_local_dir.\n"
                "2) Optionally call summarize_filenames to quickly profile dataset files.\n"
                "3) Optionally call split_markdown_tree to preview the leaves; adopt a simple 1..N id order.\n"
                "4) For each leaf id, provide only 'required_inputs' (datasets/...) and optional 'hints'/'notes'.\n"
                "5) Call submit_section_plan once to finish, then terminate. Titles/objectives/templates are auto-filled."
            ),
            max_steps=18,
            max_observe=1200,
        )

    def _pick_template_md_path(self) -> str:
        items = _vfs_list_dir("template")
        mds = sorted([name for (name, is_file) in items if is_file and name.lower().endswith(".md")])
        if not mds:
            raise RuntimeError("No template markdown found in VFS under 'template/'.")
        return f"template/{mds[0]}"

    def _load_text(self, path: str) -> str:
        content = _vfs_read_file(path)
        if content is None:
            raise RuntimeError(f"VFS file not found: {path}")
        return content

    def extract_tasks(self, agent, plan_output: str) -> Sequence[SectionTask]:  # noqa: ANN001
        submitted = self._plan_tool.get_tasks()

        # Build leaves from template markdown
        tpl_path = self._pick_template_md_path()
        tpl_text = self._load_text(tpl_path)
        parsed = parse_markdown_to_tree(
            tpl_text,
            include_content=True,
            max_content_chars=0,
            collapse_single_h1_root=True,
            source_path=tpl_path,
        )
        leaves = parsed.get("leaves") or []
        if not leaves:
            raise RuntimeError("No sections (leaves) extracted from template.")

        # Map submitted references by id
        ref_by_id = {int(t.id): t for t in submitted} if submitted else {}

        tasks: list[SectionTask] = []
        for idx, leaf in enumerate(leaves, start=1):
            title = str(leaf.get("title") or f"Section {idx}")
            template_snippet = str(leaf.get("content") or "").strip()
            # Default objective; titles/templates will be injected by code (here).
            objective = f"阅读候选输入文件（datasets/...），依据模板片段撰写《{title}》章节，严格遵循模板结构与风格。"
            ref = ref_by_id.get(idx)
            hints = list(ref.hints) if ref else []
            required_inputs = list(ref.required_inputs) if ref else []
            notes = ref.notes if ref else None

            tasks.append(
                SectionTask(
                    id=idx,
                    title=title,
                    objective=objective,
                    template=template_snippet or None,
                    hints=hints,
                    required_inputs=required_inputs,
                    notes=notes,
                )
            )

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
                        template=(str(t.get("template")).strip() if t.get("template") else None),
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
            tools=[ListLocalTemplatesTool(), ListLocalDirTool(), ReadLocalFileTool(), draft_tool],
            system_prompt=(
                "You are a report section writer. You MUST strictly follow the provided template file to structure and style the content.\n"
                "- The template is available in the VFS under 'template/'. Prefer the normalized Markdown file (*.md).\n"
                "- Mirror headings, list/bullet style, tone, and formatting conventions from the template.\n"
                "- Produce content ONLY for this section; do not include the section heading itself (the aggregator will add it).\n"
                "- Keep the writing concise, factual, and consistent with the template voice."
            ),
            next_step_prompt=(
                "Execution guide:\n"
                "1) Inspect the template: call list_local_templates; if needed, list_local_dir path='template'.\n"
                "2) Read the template markdown via read_local_file (e.g., path='template/<name>.md') to capture structure/style.\n"
                "3) Explore datasets via list_local_dir path='datasets' and read_local_file as needed for facts.\n"
                "4) Write the section content (WITHOUT the section heading) following the template's style (bullets vs paragraphs; include tables if appropriate).\n"
                "5) Call submit_section_draft once ready, then terminate."
            ),
            max_steps=24,
            max_observe=1800,
        )

    def build_request(self, task: SectionTask, *, context: PlanContext) -> str:
        lines: list[str] = [
            f"Section #{task.id}: {task.title}",
            f"Objective: {task.objective}",
        ]
        if getattr(task, "template", None):
            lines.append("Section template (STRICTLY FOLLOW THIS STRUCTURE):\n" + str(task.template).strip())
            lines.append(
                "Constraints: replicate the section template exactly (structure, subheadings if any, list styles, ordering)."
            )
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
    """Combine solver outputs and restore the original document structure.

    - Reparse the template markdown from VFS to get the document tree.
    - Insert each section's generated content at the corresponding leaf (by 1..N order).
    - Rebuild a complete Markdown with document title and hierarchical headings in original order.
    - Save to VFS under 'reports/generated_report.md'.
    """

    # Collect solver outputs by 1-based id
    solved: list[dict[str, Any]] = []
    for r in results:
        sec = r.output
        if not isinstance(sec, dict) or "id" not in sec:
            raise RuntimeError(f"Invalid solver output for section: {sec!r}")
        solved.append({"id": int(sec.get("id", 0)), "content": str(sec.get("content", "")), "title": str(sec.get("title", ""))})
    solved.sort(key=lambda s: s.get("id", 0))
    solved_map = {int(s["id"]): s for s in solved}

    # Pick template markdown and parse its structure
    items = _vfs_list_dir("template")
    mds = sorted([name for (name, is_file) in items if is_file and name.lower().endswith(".md")])
    if not mds:
        raise RuntimeError("No template markdown found in VFS under 'template/'.")
    tpl_path = f"template/{mds[0]}"
    tpl_text = _vfs_read_file(tpl_path)
    if tpl_text is None:
        raise RuntimeError(f"VFS file not found: {tpl_path}")

    parsed = parse_markdown_to_tree(
        tpl_text,
        include_content=False,
        max_content_chars=0,
        collapse_single_h1_root=True,
        source_path=tpl_path,
    )

    doc_title = parsed.get("doc_title") or context.plan_summary or "Generated Report"
    tree = parsed.get("tree") or {}
    leaves = parsed.get("leaves") or []

    # Traverse tree and rebuild markdown; insert solver content at leaves following 1..N order
    lines: list[str] = []
    lines.append(f"# {doc_title}\n")

    # Determine whether to print heading for root node
    root_level = int(tree.get("level", 0)) if isinstance(tree, dict) else 0

    # Depth-first traversal
    leaf_counter = 0

    def _emit_node(node: dict[str, Any], *, skip_self: bool = False) -> None:
        nonlocal leaf_counter
        level = int(node.get("level", 0))
        title = str(node.get("title", "")).strip()
        children = node.get("children") or []

        if not skip_self and level > 0:
            lines.append("#" * level + f" {title}")
            lines.append("")

        if not children:
            # Leaf node: insert corresponding solver output by order (1-based id)
            leaf_counter += 1
            sec = solved_map.get(leaf_counter)
            content = (sec or {}).get("content") or ""
            content = str(content).strip()
            if content:
                lines.append(content)
                lines.append("")
            return

        for ch in children:
            _emit_node(ch, skip_self=False)

    _emit_node(tree, skip_self=(root_level == 1 or root_level == 0))

    markdown = "\n".join(lines).strip() + "\n"

    # Persist to VFS
    output_path = "reports/generated_report.md"
    _vfs_write_file(output_path, markdown)

    return {"sections": solved, "report": {"content": markdown, "vfs_path": output_path, "path": output_path}}
