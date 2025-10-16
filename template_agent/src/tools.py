from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib import request, parse, error as urlerror
from pathlib import Path
from typing import Any, ClassVar, Sequence
import re
import html as _html
from fs.memoryfs import MemoryFS  # pyfilesystem2 required
from contextlib import contextmanager
import contextvars

from myagent.tool.base_tool import BaseTool, ToolResult
from myagent import LLM
from myagent.config import LLMSettings, settings


# -----------------------------
# Simple session-scoped virtual file system (VFS)
# Backed by pyfilesystem2 MemoryFS.
# -----------------------------

_VFS_FS: dict[str, MemoryFS] = {}  # session_id -> MemoryFS

# Optional override for binding a specific WS session id
_VFS_SESSION_OVERRIDE: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_vfs_session_override", default=None
)


def _get_session_id() -> str | None:
    # Prefer explicit override (e.g., from server preloading)
    try:
        override = _VFS_SESSION_OVERRIDE.get()
        if isinstance(override, str) and override:
            return override
    except Exception:
        pass

    # Fallback to ws-session context if available
    try:  # Lazy import to avoid hard dependency at import time
        from myagent.ws import get_ws_session_context  # type: ignore

        sess = get_ws_session_context()
        sid = getattr(sess, "session_id", None)
        if isinstance(sid, str) and sid:
            return sid
    except Exception:
        pass
    return None


@contextmanager
def vfs_bind_session(session_id: str):
    """Temporarily bind VFS operations to a specific WS session id.

    Useful for server-side initialization before an agent runs.
    """
    token = _VFS_SESSION_OVERRIDE.set(session_id)
    try:
        yield
    finally:
        _VFS_SESSION_OVERRIDE.reset(token)


def _get_store() -> MemoryFS:
    sid = _get_session_id() or "__global__"
    fs = _VFS_FS.get(sid)
    if fs is None:
        fs = MemoryFS()
        _VFS_FS[sid] = fs
    return fs


def _vfs_reset() -> None:
    # Reset only current session's VFS
    sid = _get_session_id() or "__global__"
    _VFS_FS[sid] = MemoryFS()


def _vfs_norm(path: str) -> str:
    return str(Path(path).as_posix()).lstrip("/")


def _vfs_mkdirs(path: str) -> None:
    parts = _vfs_norm(path).split("/")
    cur = []
    for p in parts:
        cur.append(p)
        fs = _get_store()
        try:
            fs.makedirs("/".join(cur), recreate=True)
        except Exception:
            pass


def _vfs_write_file(path: str, content: str) -> None:
    path = _vfs_norm(path)
    parent = Path(path).parent.as_posix()
    if parent and parent != ".":
        _vfs_mkdirs(parent)
    fs = _get_store()
    try:
        fs.writetext(path, content)
    except Exception:
        # ensure parent exists then retry
        fs.makedirs(parent, recreate=True)
        fs.writetext(path, content)


def _vfs_read_file(path: str) -> str | None:
    fs = _get_store()
    norm = _vfs_norm(path)
    try:
        if fs.exists(norm) and fs.isfile(norm):
            return fs.readtext(norm)
    except Exception:
        return None
    return None


def _vfs_list_dir(path: str) -> list[tuple[str, bool]]:
    """Return list of (name, is_file) under a VFS directory path.

    path is relative (e.g., "template" or "datasets").
    """
    rel = _vfs_norm(path).rstrip("/")
    fs = _get_store()
    target = rel or "/"
    try:
        names = list(fs.listdir(target))
    except Exception:
        return []
    items: list[tuple[str, bool]] = []
    for name in names:
        child = name if target in ("", "/") else f"{target.rstrip('/')}/{name}"
        try:
            is_file = bool(fs.isfile(child))
            is_dir = bool(fs.isdir(child))
        except Exception:
            is_file = True
            is_dir = False
        items.append((name, is_file and not is_dir))
    # Sort: directories first, then files, both alpha
    return sorted(items, key=lambda x: (x[1], x[0].lower()))


def _get_api_base_url() -> str:
    # Support multiple env var names; prefer TEMPLATE_API_BASE_URL
    return (
        os.environ.get("TEMPLATE_API_BASE_URL")
        or os.environ.get("TEMPLATE_BACKEND_URL")
        or os.environ.get("BACKEND_BASE_URL")
        or "http://127.0.0.1:8787"
    )


def _get_session_hints() -> dict[str, Any]:
    """Fetch per-session hints like template/database/api from WS session context.

    The WS server attaches `session_metadata` onto the current AgentSession.
    """
    try:  # Lazy import to avoid hard dependency at import time
        from myagent.ws import get_ws_session_context  # type: ignore

        sess = get_ws_session_context()
        meta = getattr(sess, "session_metadata", None)
        if isinstance(meta, dict):
            return meta
    except Exception:
        pass
    return {}


def _is_probably_html(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    # Basic heuristics: starts with tag or contains heading/paragraph/list tags
    return bool(re.search(r"<\s*(h[1-6]|p|ul|ol|li|div|span|section|article|br)\b", t, flags=re.I)) or t.startswith("<")


def _strip_tags_keep_text(text: str) -> str:
    # Replace <br> with newlines
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.I)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    return _html.unescape(text)


def _slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9\- _]+", "", s)
    s = s.replace(" ", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "section"


def _extract_front_matter_title(md_text: str) -> tuple[str | None, int]:
    lines = md_text.splitlines()
    if not lines:
        return None, 0
    if lines[0].strip() != "---":
        return None, 0
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() in ("---", "..."):
            end_idx = i
            break
    if end_idx is None:
        return None, 0
    title_val: str | None = None
    for j in range(1, end_idx):
        m = re.match(r"^title\s*:\s*(.+)\s*$", lines[j].strip(), flags=re.I)
        if m:
            val = m.group(1).strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            title_val = val.strip()
            break
    return (title_val if title_val else None), (end_idx + 1)


def parse_markdown_to_tree(
    md_text: str,
    *,
    include_content: bool = True,
    max_content_chars: int = 4000,
    collapse_single_h1_root: bool = True,
    source_path: str | None = None,
) -> dict[str, Any]:
    """Parse markdown into a hierarchical tree and leaves list.

    Returns a dict with keys: tree, leaves, node_count, doc_title, source_path.
    """
    text = md_text or ""
    fm_title, scan_start = _extract_front_matter_title(text)
    lines = text.splitlines()
    n = len(lines)

    class _Node(dict):
        pass

    def _make_node(title: str, level: int, heading_line: int, start_line: int) -> _Node:
        return _Node(
            title=str(title).strip(),
            level=int(level),
            slug=_slugify(title),
            heading_line=int(heading_line),
            start_line=int(start_line),
            end_line=None,
            content=None,
            children=[],
        )

    headings: list[dict[str, Any]] = []
    i = scan_start
    in_fence = False

    while i < n:
        line = lines[i]
        stripped = line.lstrip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            i += 1
            continue

        if in_fence:
            i += 1
            continue

        atx = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*(#+\s*)?$", line)
        if atx and not stripped.startswith(">"):
            level = len(atx.group(1))
            title_txt = atx.group(2).strip()
            title_txt = re.sub(r"\s#+\s*$", "", title_txt).strip()
            headings.append(
                {
                    "level": level,
                    "text": title_txt,
                    "heading_line": i + 1,
                    "content_start": i + 2,
                    "type": "atx",
                }
            )
            i += 1
            continue

        if i + 1 < n:
            next_line = lines[i + 1]
            m = re.match(r"^\s{0,3}(=+|-+)\s*$", next_line)
            if m and not stripped.startswith(">") and line.strip():
                lvl = 1 if m.group(1).startswith("=") else 2
                title_txt = line.strip()
                headings.append(
                    {
                        "level": lvl,
                        "text": title_txt,
                        "heading_line": i + 1,
                        "content_start": i + 3,
                        "type": "setext",
                    }
                )
                i += 2
                continue

        i += 1

    if not headings:
        doc_title = fm_title or (source_path or "Document")
        root_node = _make_node(doc_title, 0, 1, 1)
        root_node["end_line"] = n
        if include_content:
            body = text
            if max_content_chars > 0 and len(body) > max_content_chars:
                body = body[:max_content_chars] + "\n..."
            root_node["content"] = body
        return {
            "tree": root_node,
            "leaves": [root_node],
            "node_count": 1,
            "doc_title": doc_title,
            "source_path": source_path,
        }

    count_h1 = sum(1 for h in headings if int(h["level"]) == 1)
    first_heading_text = headings[0]["text"].strip()
    doc_title = fm_title or (first_heading_text if headings and headings[0]["level"] == 1 else first_heading_text)

    root = _make_node(doc_title, 0, 1, 1)
    stack: list[_Node] = [root]

    created_nodes: list[_Node] = []
    for h in headings:
        level = int(h["level"])
        while stack and int(stack[-1]["level"]) >= level:
            node = stack.pop()
            if node is not root and node.get("end_line") is None:
                node["end_line"] = int(h["heading_line"]) - 1
        node = _make_node(h["text"], level, int(h["heading_line"]), int(h["content_start"]))
        stack[-1]["children"].append(node)
        stack.append(node)
        created_nodes.append(node)

    while stack:
        node = stack.pop()
        if node.get("end_line") is None:
            node["end_line"] = n

    def _trim_trailing_blanks(s: str) -> str:
        lines2 = s.splitlines()
        while lines2 and not lines2[-1].strip():
            lines2.pop()
        return "\n".join(lines2)

    if include_content:
        for node in created_nodes:
            a = int(node["start_line"]) - 1
            b = int(node["end_line"]) - 1
            if a <= b and 0 <= a < n:
                chunk = "\n".join(lines[a : b + 1])
                chunk = _trim_trailing_blanks(chunk)
                if max_content_chars > 0 and len(chunk) > max_content_chars:
                    chunk = chunk[: max_content_chars] + "\n..."
                node["content"] = chunk

    actual_root: _Node
    if collapse_single_h1_root and count_h1 == 1 and root["children"] and int(root["children"][0]["level"]) == 1:
        actual_root = root["children"][0]
    else:
        actual_root = root

    leaves: list[dict[str, Any]] = []

    def _collect(node: _Node, trail: list[str]) -> None:
        children = node.get("children") or []
        if not children:
            leaves.append(
                {
                    "title": node["title"],
                    "level": node["level"],
                    "slug": node["slug"],
                    "path": trail,
                    "start_line": node["start_line"],
                    "end_line": node["end_line"],
                    **({"content": node.get("content")} if include_content else {}),
                }
            )
        else:
            for ch in children:
                _collect(ch, trail + [str(ch["title"])])

    _collect(actual_root, [str(actual_root["title"])])

    return {
        "tree": actual_root,
        "leaves": leaves,
        "node_count": 1 + sum(1 for _ in created_nodes),
        "doc_title": doc_title,
        "source_path": source_path,
    }


def _html_to_md_basic(html_text: str) -> str:
    """Very basic HTML→Markdown conversion focusing on headings, paragraphs, lists.

    Not intended to be perfect; just enough to extract structure for planning.
    """
    s = html_text
    # Normalize line breaks for block tags
    s = re.sub(r"\r\n?|\n", "\n", s)
    # Headings
    for level in range(6, 0, -1):
        s = re.sub(
            rf"<\s*h{level}[^>]*>(.*?)<\s*/\s*h{level}\s*>",
            lambda m: "\n" + ("#" * level) + " " + _strip_tags_keep_text(m.group(1)).strip() + "\n\n",
            s,
            flags=re.I | re.S,
        )
    # Lists
    def _ul_repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        items = re.findall(r"<\s*li[^>]*>(.*?)<\s*/\s*li\s*>", inner, flags=re.I | re.S)
        lines = ["- " + _strip_tags_keep_text(x).strip() for x in items if _strip_tags_keep_text(x).strip()]
        return "\n" + "\n".join(lines) + "\n\n" if lines else "\n"

    s = re.sub(r"<\s*ul[^>]*>(.*?)<\s*/\s*ul\s*>", _ul_repl, s, flags=re.I | re.S)

    # Paragraphs
    s = re.sub(
        r"<\s*p[^>]*>(.*?)<\s*/\s*p\s*>",
        lambda m: "\n" + _strip_tags_keep_text(m.group(1)).strip() + "\n\n",
        s,
        flags=re.I | re.S,
    )

    # Remove any remaining tags
    s = _strip_tags_keep_text(s)
    # Collapse excessive blank lines
    s = re.sub(r"\n{3,}", "\n\n", s).strip() + "\n"
    return s


def _http_get_json(url: str) -> Any:
    req = request.Request(url, headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=10) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            data = resp.read().decode(charset)
            return json.loads(data)
    except urlerror.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc}") from exc


def _find_by_name_or_id(items: list[dict[str, Any]], *, name: str | None, id_: str | None) -> dict[str, Any] | None:
    if id_:
        for it in items:
            if str(it.get("id")) == id_:
                return it
    if name:
        for it in items:
            if str(it.get("name")) == name:
                return it
    return None


# -----------------------------
# Data structures
# -----------------------------


@dataclass
class SectionTask:
    """A single report section task proposed by the planner.

    Attributes:
        id: 1-indexed section identifier
        title: Section title
        objective: What this section should convey or accomplish
        template: Optional textual template snippet for this section
        hints: Optional list of bullet hints or key points
        required_inputs: Optional file hints (e.g., ["datasets/sample.json"]) for solver
        notes: Any extra guidance or formatting constraints
    """

    id: int
    title: str
    objective: str
    template: str | None
    hints: list[str]
    required_inputs: list[str]
    notes: str | None = None

    def short_summary(self) -> str:
        tip = f" | Hints: {', '.join(self.hints[:2])}" if self.hints else ""
        return f"[Section {self.id}] {self.title}: {self.objective}{tip}"


def _ensure_string_list(values: Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, (str, bytes)):
        return [str(values).strip()] if str(values).strip() else []
    if not isinstance(values, Sequence):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _parse_section_task(task: dict[str, Any]) -> SectionTask:
    try:
        sec_id = int(task["id"])
        if sec_id <= 0:
            raise ValueError("Section id must be positive.")
    except Exception as exc:
        raise ValueError(f"Invalid section id in task: {task}") from exc

    title = str(task.get("title", "")).strip()
    objective = str(task.get("objective", "")).strip()

    template = str(task.get("template")).strip() if task.get("template") else None
    hints = _ensure_string_list(task.get("hints"))
    required_inputs = _ensure_string_list(task.get("required_inputs"))
    notes = str(task.get("notes")).strip() if task.get("notes") else None

    return SectionTask(
        id=sec_id,
        title=title,
        objective=objective,
        template=template,
        hints=hints,
        required_inputs=required_inputs,
        notes=notes,
    )


# -----------------------------
# Planner tools
# -----------------------------


class SectionPlanSubmissionTool(BaseTool):
    """Collect section tasks generated by the planning agent."""

    name: str = "submit_section_plan"
    description: str = (
        "Submit the finalized section plan. Provide per-section 'id' and optional 'required_inputs'/'hints'/'notes'. "
        "Titles/objectives/templates will be auto-filled based on the template leaves."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "description": "List of section tasks for the report (1 task per section).",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "description": "1-indexed section identifier (matches template leaf order)"},
                        "objective": {"type": "string", "description": "(Optional) Ignored; filled from template"},
                        "hints": {"type": "array", "items": {"type": "string"}},
                        "required_inputs": {
                            "type": "array",
                            "items": {"type": "string"},
                        "description": "Optional input file hints for solver (e.g., VFS paths under 'datasets/')",
                        },
                        "notes": {"type": "string"},
                    },
                    "required": ["id"],
                },
            }
        },
        "required": ["tasks"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[SectionTask] = []

    async def execute(self, tasks: Sequence[dict[str, Any]]) -> ToolResult:  # type: ignore[override]
        try:
            parsed = [_parse_section_task(t) for t in tasks]
        except ValueError as exc:
            return ToolResult(error=str(exc))

        ids = [t.id for t in parsed]
        if len(ids) != len(set(ids)):
            return ToolResult(error="Section task IDs must be unique")

        parsed.sort(key=lambda t: t.id)
        self._tasks = parsed
        overview = ["✅ Section plan received:"] + [f"- {t.short_summary()}" for t in parsed]
        return ToolResult(output="\n".join(overview), system=f"Section planning completed with {len(parsed)} tasks")

    def get_tasks(self) -> list[SectionTask]:
        return list(self._tasks)


class ListLocalTemplatesTool(BaseTool):
    """List available templates from the in-memory VFS (API-loaded)."""

    name: str = "list_local_templates"
    description: str = "List markdown templates mounted under VFS path 'template/'"
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def execute(self) -> ToolResult:  # type: ignore[override]
        vfs_list = [name for (name, is_file) in _vfs_list_dir("template") if is_file and name.lower().endswith(".md")]
        if not vfs_list:
            return ToolResult(output="No templates found in VFS. Ensure the server preloaded remote resources for this session.")
        lines = ["Available templates (VFS):", *[f"- template/{n}" for n in vfs_list]]
        return ToolResult(output="\n".join(lines))


class ReadLocalFileTool(BaseTool):
    """Read a file from the VFS (API-loaded resources only)."""

    name: str = "read_local_file"
    description: str = "Read a text file from VFS paths like 'template/...' or 'datasets/...'."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path from allowed roots"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str) -> ToolResult:  # type: ignore[override]
        # Check VFS first
        vfs_content = _vfs_read_file(path)
        if vfs_content is not None:
            return ToolResult(output=vfs_content, system=f"Read VFS file: {path}")
        return ToolResult(error=f"VFS file not found: {path}. Ensure the server preloaded resources and use 'template/' or 'datasets/' paths.")


class ListLocalDirTool(BaseTool):
    """List directory contents from the VFS (API-loaded resources only)."""

    name: str = "list_local_dir"
    description: str = "List files and subdirectories under a VFS path like 'template' or 'datasets'."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative directory path to list"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str) -> ToolResult:  # type: ignore[override]
        vfs_items = _vfs_list_dir(path)
        lines: list[str] = [f"Listing for {path} (VFS):"]
        if vfs_items:
            for name, is_file in vfs_items:
                lines.append(f"- [{'FILE' if is_file else 'DIR'}] {name}")
        else:
            lines.append("(empty)")
        return ToolResult(output="\n".join(lines))


class SplitMarkdownTreeTool(BaseTool):
    """Split Markdown into a hierarchical document tree.

    - Accepts raw `markdown` or reads from a VFS `path` (e.g., 'template/<name>.md').
    - Builds a tree using ATX (#) and Setext (===/---) headings.
    - Each smallest section is a leaf node; the document title is used as the root when applicable.
    - Returns a readable outline and structured JSON (in the system channel).
    """

    name: str = "split_markdown_tree"
    description: str = (
        "Parse markdown and return a document tree where leaves are smallest sections; title serves as root when applicable."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "VFS path to a markdown file (e.g., 'template/xxx.md')"},
            "markdown": {"type": "string", "description": "Raw markdown text; if provided, takes precedence over path"},
            "include_content": {"type": "boolean", "default": True, "description": "Include body content for each node"},
            "max_content_chars": {"type": "integer", "default": 4000, "description": "Max chars per node content (0 for unlimited)"},
            "collapse_single_h1_root": {"type": "boolean", "default": True, "description": "If exactly one H1 exists at top, use it as root"},
        },
        "required": [],
    }

    async def execute(
        self,
        *,
        path: str | None = None,
        markdown: str | None = None,
        include_content: bool = True,
        max_content_chars: int = 4000,
        collapse_single_h1_root: bool = True,
    ) -> ToolResult:  # type: ignore[override]
        src_text: str | None = None
        src_path: str | None = None

        if isinstance(markdown, str) and markdown.strip():
            src_text = markdown
        elif isinstance(path, str) and path.strip():
            norm = _vfs_norm(path)
            content = _vfs_read_file(norm)
            if content is None:
                return ToolResult(error=f"VFS file not found: {path}")
            src_text = content
            src_path = norm
        else:
            return ToolResult(error="Provide either 'markdown' or a VFS 'path'.")

        text = src_text or ""
        if not text.strip():
            return ToolResult(error="Markdown content is empty")
        result_obj = parse_markdown_to_tree(
            text,
            include_content=include_content,
            max_content_chars=max_content_chars,
            collapse_single_h1_root=collapse_single_h1_root,
            source_path=src_path,
        )

        def _outline(node: dict[str, Any], indent: int, lines_out: list[str]) -> None:
            lbl = f"H{node.get('level')}" if int(node.get("level", 0)) > 0 else "ROOT"
            rng = f"L{node.get('start_line')}-{node.get('end_line')}" if node.get("start_line") and node.get("end_line") else ""
            prefix = "  " * indent
            title_show = str(node.get("title", "Document"))
            lines_out.append(f"{prefix}- {title_show} ({lbl} {rng})")
            for ch in node.get("children") or []:
                _outline(ch, indent + 1, lines_out)

        outline_lines: list[str] = []
        _outline(result_obj["tree"], 0, outline_lines)
        return ToolResult(output="\n".join(outline_lines), system=json.dumps(result_obj, ensure_ascii=False))

class LoadRemoteResourcesTool(BaseTool):
    """Load template and knowledge base files from backend API into a virtual FS.

    The tool queries the backend for the specified template (by name or id)
    and knowledge base (by name or id), then mounts them into an in-memory
    virtual file system with the following layout:
      - template/<template_safe_name>.md  (template content)
      - datasets/<file_name>.json         (each KB file as JSON)

    API base URL is taken from env TEMPLATE_API_BASE_URL unless overridden.
    """

    name: str = "load_remote_resources"
    description: str = (
        "Fetch template + database files via backend API and mount a virtual file system."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "template_name": {"type": "string"},
            "template_id": {"type": "string"},
            "knowledge_base_name": {"type": "string"},
            "database_id": {"type": "string"},
            "api_base_url": {"type": "string", "description": "Optional override for backend URL"},
        },
        "required": [],
    }

    @staticmethod
    def _safe_filename(name: str, suffix: str) -> str:
        safe = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in name.strip())
        safe = safe.strip("_") or "untitled"
        return safe + suffix

    async def execute(
        self,
        *,
        template_name: str | None = None,
        template_id: str | None = None,
        knowledge_base_name: str | None = None,
        database_id: str | None = None,
        api_base_url: str | None = None,
    ) -> ToolResult:  # type: ignore[override]
        # Merge with session hints if args missing
        hints = _get_session_hints()
        template_name = template_name or hints.get("template_name")
        template_id = template_id or hints.get("template_id")
        knowledge_base_name = knowledge_base_name or hints.get("knowledge_base_name")
        database_id = database_id or hints.get("database_id")
        api_base_url = api_base_url or hints.get("api_base_url")

        base = (api_base_url or _get_api_base_url()).rstrip("/")
        # Resolve template
        try:
            templates = _http_get_json(f"{base}/api/templates")
            if not isinstance(templates, list):
                return ToolResult(error="Unexpected templates response")
            tpl = _find_by_name_or_id(templates, name=template_name, id_=template_id)
            if not tpl:
                return ToolResult(error="Template not found by name or id")
            tpl_name = str(tpl.get("name") or tpl.get("id") or "template")
            tpl_content = str(tpl.get("content") or "")
        except Exception as exc:
            return ToolResult(error=f"Failed to fetch templates: {exc}")

        # Resolve database
        try:
            dbs = _http_get_json(f"{base}/api/databases")
            if not isinstance(dbs, list):
                return ToolResult(error="Unexpected databases response")
            # Need full DB with files; list endpoint only has counts
            db_meta = _find_by_name_or_id(dbs, name=knowledge_base_name, id_=database_id)
            if not db_meta:
                return ToolResult(error="Database not found by name or id")
            db_id = str(db_meta.get("id"))
            db = _http_get_json(f"{base}/api/databases/{parse.quote(db_id)}")
            if not isinstance(db, dict):
                return ToolResult(error="Unexpected database detail response")
            files = db.get("files") or []
            if not isinstance(files, list):
                files = []
        except Exception as exc:
            return ToolResult(error=f"Failed to fetch database: {exc}")

        # Mount into VFS
        _vfs_reset()
        _vfs_mkdirs("template")
        _vfs_mkdirs("datasets")

        # Determine template representation; prefer markdown, convert from HTML if needed.
        base_name = self._safe_filename(tpl_name, "")
        if _is_probably_html(tpl_content):
            raw_html_name = base_name + ".html"
            md_name = base_name + ".md"
            _vfs_write_file(f"template/{raw_html_name}", tpl_content)
            try:
                md_converted = _html_to_md_basic(tpl_content)
            except Exception:
                md_converted = _strip_tags_keep_text(tpl_content)
            _vfs_write_file(f"template/{md_name}", md_converted)
            tpl_file = md_name
        else:
            md_name = base_name + ".md"
            _vfs_write_file(f"template/{md_name}", tpl_content)
            tpl_file = md_name

        added_files: list[str] = []
        for f in files:
            name = str(f.get("name") or f.get("id") or "data.json")
            # ensure .json extension preserved
            if not name.lower().endswith(".json"):
                name = name + ".json"
            try:
                content = json.dumps(f.get("data") or {}, ensure_ascii=False, indent=2)
            except Exception:
                content = str(f.get("data"))
            fname = self._safe_filename(name, "")
            _vfs_write_file(f"datasets/{fname}", content)
            added_files.append(fname)

        summary_lines = [
            "Loaded remote resources:",
            f"- Template: template/{tpl_file}",
            f"- Files ({len(added_files)}):",
            *[f"  - datasets/{n}" for n in added_files],
        ]
        return ToolResult(output="\n".join(summary_lines))


class SummarizeFilenamesTool(BaseTool):
    """Summarize dataset files using their CONTENT with a small LLM.

    - Uses env SLM_MODEL for the model name (e.g., Qwen/Qwen2.5-7B-Instruct).
    - If files are not provided, defaults to VFS 'datasets/' file list.
    - Reads each file content from VFS and generates a short summary per file.
    - Designed for planning stage to quickly profile available inputs.
    """

    name: str = "summarize_filenames"
    description: str = "Summarize dataset files by content using a compact LLM (SLM)."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of file names to summarize; defaults to VFS datasets/",
            },
            "language": {"type": "string", "description": "Output language", "default": "zh"},
            "style": {"type": "string", "description": "Optional tone/style hint"},
            "max_sentences": {"type": "integer", "description": "Sentences per summary", "default": 1},
            "max_chars_per_file": {"type": "integer", "description": "Max characters of content per file", "default": 1200},
        },
        "required": [],
    }

    async def execute(
        self,
        files: list[str] | None = None,
        language: str = "zh",
        style: str | None = None,
        max_sentences: int = 1,
        max_chars_per_file: int = 1200,
    ) -> ToolResult:  # type: ignore[override]
        # Determine file names
        if not files:
            items = _vfs_list_dir("datasets")
            files = [name for (name, is_file) in items if is_file]

        if not files:
            return ToolResult(error="No files to summarize (datasets/ is empty)")

        # Resolve small model from env
        model_name = os.getenv("SLM_MODEL") or settings.llm_settings.model
        llm = LLM(
            config_name="slm",
            llm_config=LLMSettings(
                model=model_name,
                base_url=settings.llm_settings.base_url,
                api_key=settings.llm_settings.api_key,
                max_tokens=min(512, settings.llm_settings.max_tokens),
                temperature=0.3,
            ),
        )

        # Build per-file content snippets and summarize each file individually
        summaries: list[dict[str, str]] = []
        lang_tag = "中文" if language.lower().startswith("zh") else "English"
        style_part = f"；风格：{style}" if style else ""

        for fn in files:
            # Resolve path under datasets/
            norm_name = _vfs_norm(fn)
            ds_path = norm_name if norm_name.startswith("datasets/") else f"datasets/{norm_name}"
            content = _vfs_read_file(ds_path)
            if content is None:
                summaries.append({"file": fn, "summary": "（无法读取内容）"})
                continue
            snippet = content.strip()
            if max_chars_per_file > 0 and len(snippet) > max_chars_per_file:
                snippet = snippet[:max_chars_per_file] + "\n..."

            user_prompt = (
                f"请阅读以下文件内容片段，并用{lang_tag}在不超过{max_sentences}句内总结该文件的主题与要点{style_part}。"
                f"\n文件名: {fn}\n内容片段:\n" + snippet
            )

            try:
                summary_text = await llm.ask(
                    messages=[{"role": "user", "content": user_prompt}],
                    system_msgs=[
                        {
                            "role": "system",
                            "content": "You generate terse, faithful summaries based on provided content only.",
                        }
                    ],
                    stream=False,
                    temperature=0.2,
                )
            except Exception as exc:
                summaries.append({"file": fn, "summary": f"（摘要失败: {exc}）"})
                continue

            clean_summary = str(summary_text).strip()
            summaries.append({"file": fn, "summary": clean_summary})

        pretty_text = "\n".join([f"- {it['file']}: {it['summary']}" for it in summaries])
        json_text = json.dumps({"summaries": summaries}, ensure_ascii=False)
        return ToolResult(output=pretty_text, system=json_text)


# -----------------------------
# Solver tool
# -----------------------------


class SectionDraftTool(BaseTool):
    """Capture final section draft produced by a solver agent."""

    name: str = "submit_section_draft"
    description: str = (
        "Submit the finalized section draft. Provide id, title, markdown content, and optional tables."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "section": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "content": {"type": "string", "description": "Markdown content for this section"},
                    "tables": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Optional structured tables; when present also include as markdown",
                    },
                },
                "required": ["id", "title", "content"],
            }
        },
        "required": ["section"],
    }

    def __init__(self, expected_id: int | None = None) -> None:
        super().__init__()
        self._expected_id = expected_id
        self._section: dict[str, Any] | None = None

    async def execute(self, section: dict[str, Any]) -> ToolResult:  # type: ignore[override]
        if self._expected_id is not None and section.get("id") != self._expected_id:
            return ToolResult(error=f"Section id mismatch. Expected {self._expected_id}, got {section.get('id')!r}")
        # Minimal validation
        if not str(section.get("title", "")).strip() or not str(section.get("content", "")).strip():
            return ToolResult(error="Section title and content are required")
        self._section = {
            "id": int(section["id"]),
            "title": str(section["title"]).strip(),
            "content": str(section["content"]).strip(),
            **({"tables": section.get("tables")} if section.get("tables") is not None else {}),
        }
        return ToolResult(output=f"Draft stored for section {section['id']}: {section['title']}")

    def get_section(self) -> dict[str, Any] | None:
        return self._section


# -----------------------------
# Aggregation helper
# -----------------------------


class RenderMarkdownReportTool(BaseTool):
    """Render a markdown report from section drafts and optional metadata.

    This tool is used by the pipeline aggregator (not by LLM) to assemble
    the final report. When `output_path` is provided, the report is saved
    into the in-memory VFS (virtual path), not the local filesystem.
    """

    name: str = "render_markdown_report"
    description: str = "Assemble sections into a markdown report"
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "sections": {"type": "array", "items": {"type": "object"}},
            "output_path": {"type": "string", "description": "Optional VFS path (e.g., 'reports/generated_report.md') to save"},
            "front_matter": {"type": "object"},
        },
        "required": ["title", "sections"],
    }

    async def execute(
        self,
        *,
        title: str,
        sections: Sequence[dict[str, Any]],
        output_path: str | None = None,
        front_matter: dict[str, Any] | None = None,
    ) -> ToolResult:  # type: ignore[override]
        lines: list[str] = []
        if front_matter:
            lines.append("---")
            for k, v in front_matter.items():
                lines.append(f"{k}: {v}")
            lines.append("---\n")
        lines.append(f"# {title}\n")
        for sec in sorted(sections, key=lambda s: s.get("id", 0)):
            heading = f"## {sec.get('title', '').strip()}".strip()
            if heading:
                lines.append(heading)
            content = str(sec.get("content", "")).strip()
            if content:
                lines.append(content)
            lines.append("")
        markdown = "\n".join(lines).strip() + "\n"

        result: dict[str, Any] = {"content": markdown}

        # Optionally persist into VFS
        if output_path:
            # Normalize and write to VFS (session-scoped)
            norm = _vfs_norm(output_path)
            _vfs_write_file(norm, markdown)
            # Return both vfs_path and a legacy 'path' field for compatibility
            result["vfs_path"] = norm
            result["path"] = norm
        # Put structured result into output; use system for a short status string
        return ToolResult(output=result, system="rendered")
