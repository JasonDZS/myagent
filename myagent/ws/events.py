"""WebSocket event protocol definitions."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class EventProtocol(BaseModel):
    """WebSocket event protocol.

    All server-to-client and client-to-server communication uses this structure.
    """

    session_id: str | None = Field(None, description="Unique session identifier")
    connection_id: str | None = Field(None, description="WebSocket connection ID")
    step_id: str | None = Field(None, description="Request/response correlation ID (for pairing)")
    event: str = Field(..., description="Event type (e.g., 'plan.start', 'agent.thinking')")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO8601 timestamp when event was created"
    )
    content: str | dict[str, Any] | None = Field(
        None,
        description="Main event payload: user-visible text or primary data structure"
    )
    metadata: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Supplementary machine-readable data: statistics, context, options"
    )

    class Config:
        """Pydantic configuration"""
        json_schema_extra = {
            "examples": [
                {
                    "session_id": "sess_001",
                    "event": "agent.thinking",
                    "timestamp": "2024-10-18T12:00:00Z",
                    "content": "Processing query...",
                    "metadata": {"model": "gpt-4", "max_tokens": 2000}
                },
                {
                    "session_id": "sess_001",
                    "event": "plan.completed",
                    "step_id": "plan_1",
                    "content": {"tasks": [{"id": 1, "title": "..."}]},
                    "metadata": {"task_count": 1, "plan_summary": "..."}
                }
            ]
        }

    # Content vs Metadata Guidance:
    # - content: What the user needs to see or primary payload
    #   Examples: final_answer, plan tasks, error message
    # - metadata: Structured supplementary data for processing
    #   Examples: execution_time, tokens_used, task details


class UserEvents:
    """User (client) event types - sent from client to server.

    Usage patterns:
    - MESSAGE: content = user query text, metadata = source/client info
    - RESPONSE: content = {approved, feedback}, metadata = response context
    - ACK: metadata = {last_seq, received_count} for reliable delivery

    Reconnection Events (Three Distinct Types):
    - RECONNECT: Simple session resume (short disconnect, <60s)
      · Payload: {session_id}
      · Use: Connection briefly lost, session still valid

    - RECONNECT_WITH_STATE: Stateful recovery with client snapshot (<60s-24h)
      · Payload: {signed_state, last_seq, last_event_id}
      · Use: Extended disconnect, client has exported state
      · Creates NEW session (verifies client state integrity)

    - REQUEST_STATE: Explicit state export request (planned operation)
      · Payload: {session_id} only
      · Use: Client wants to save session before closing
      · Does NOT trigger reconnection, purely export
      · Response includes signed_state for later RECONNECT_WITH_STATE
    """

    MESSAGE = "user.message"
    # New: direct task submission to run solver without planning
    SOLVE_TASKS = "user.solve_tasks"
    RESPONSE = "user.response"
    CANCEL = "user.cancel"
    CANCEL_TASK = "user.cancel_task"
    RESTART_TASK = "user.restart_task"
    CANCEL_PLAN = "user.cancel_plan"
    REPLAN = "user.replan"
    CREATE_SESSION = "user.create_session"
    RECONNECT = "user.reconnect"
    RECONNECT_WITH_STATE = "user.reconnect_with_state"
    REQUEST_STATE = "user.request_state"
    # Client acknowledgement of received events (carry last_seq)
    ACK = "user.ack"


class PlanEvents:
    """Plan stage events (planning phase of pipeline).

    Usage patterns:
    - START: content = {question}, metadata = plan context
    - COMPLETED: content = {tasks list}, metadata = {task_count, plan_summary, stats}
    - CANCELLED: metadata = {reason}
    - STEP_COMPLETED: metadata = {step_name, step_index}
    - VALIDATION_ERROR: content = error message, metadata = {error_code, field, constraint}
    """

    START = "plan.start"
    COMPLETED = "plan.completed"
    CANCELLED = "plan.cancelled"
    COERCION_ERROR = "plan.coercion_error"
    STEP_COMPLETED = "plan.step_completed"      # 规划步骤完成
    VALIDATION_ERROR = "plan.validation_error"  # 规划验证错误


class SolverEvents:
    """Solver stage events (task solving phase of pipeline).

    Usage patterns:
    - START: metadata = {task, attempt}, content empty
    - COMPLETED: content = {task, result}, metadata = {execution_time_ms, stats}
    - CANCELLED: metadata = {reason}
    - RESTARTED: metadata = {attempt, reason}
    - PROGRESS: metadata = {progress_percent, current_step}
    - STEP_FAILED: content = error, metadata = {step_name, error_code, recovery_action}
    - RETRY: metadata = {attempt, max_attempts, backoff_ms}
    """

    START = "solver.start"
    COMPLETED = "solver.completed"
    CANCELLED = "solver.cancelled"
    RESTARTED = "solver.restarted"
    PROGRESS = "solver.progress"        # 求解中的进度更新
    STEP_FAILED = "solver.step_failed"  # 单个步骤失败
    RETRY = "solver.retry"              # 重试开始


class AggregateEvents:
    """Aggregation stage events."""

    START = "aggregate.start"
    COMPLETED = "aggregate.completed"


class PipelineEvents:
    """Pipeline-level events."""

    COMPLETED = "pipeline.completed"


class AgentEvents:
    """Agent event types (reasoning and execution).

    Usage patterns:
    - THINKING: content = status text, metadata = {model, max_tokens}
    - TOOL_CALL: content = description, metadata = {tool_name, args, call_id}
    - TOOL_RESULT: content = result summary, metadata = {result_data, execution_time_ms}
    - PARTIAL_ANSWER: content = streaming text, metadata = {completion_percent}
    - FINAL_ANSWER: content = complete answer, metadata = {type, generation_time_ms}
    - USER_CONFIRM: content = confirmation text, metadata = {tasks, options}
    - ERROR: content = error message, metadata = {error_code, error_type, context}
    - SESSION_*: metadata = session context
    """

    THINKING = "agent.thinking"
    TOOL_CALL = "agent.tool_call"
    TOOL_RESULT = "agent.tool_result"
    PARTIAL_ANSWER = "agent.partial_answer"
    FINAL_ANSWER = "agent.final_answer"
    USER_CONFIRM = "agent.user_confirm"
    ERROR = "agent.error"
    TIMEOUT = "agent.timeout"
    INTERRUPTED = "agent.interrupted"
    SESSION_CREATED = "agent.session_created"
    SESSION_END = "agent.session_end"
    LLM_MESSAGE = "agent.llm_message"
    STATE_EXPORTED = "agent.state_exported"
    STATE_RESTORED = "agent.state_restored"

    # Backward-compatible aliases for plan/solver control events
    PLAN_CANCELLED = PlanEvents.CANCELLED
    SOLVER_CANCELLED = SolverEvents.CANCELLED
    SOLVER_RESTARTED = SolverEvents.RESTARTED


class SystemEvents:
    """System event types"""

    CONNECTED = "system.connected"
    NOTICE = "system.notice"
    HEARTBEAT = "system.heartbeat"
    ERROR = "system.error"


class ErrorEvents:
    """Error and recovery events for comprehensive error handling.

    Usage patterns:
    - EXECUTION: content = error message, metadata = {error_code, error_type, context}
    - VALIDATION: content = validation error, metadata = {error_code, field, constraint}
    - TIMEOUT: content = timeout message, metadata = {timeout_seconds, stage}
    - RECOVERY_STARTED: content = recovery status, metadata = {recovery_action}
    - RECOVERY_SUCCESS: content = "Recovery successful", metadata = {recovery_time_ms}
    - RECOVERY_FAILED: content = failure reason, metadata = {error_code, retry_action}
    """

    EXECUTION = "error.execution"             # 执行错误
    VALIDATION = "error.validation"           # 验证错误
    TIMEOUT = "error.timeout"                 # 超时错误
    RECOVERY_STARTED = "error.recovery_started"      # 恢复开始
    RECOVERY_SUCCESS = "error.recovery_success"      # 恢复成功
    RECOVERY_FAILED = "error.recovery_failed"        # 恢复失败


def _truncate(text: str, limit: int = 160) -> str:
    try:
        return text if len(text) <= limit else text[: limit - 1] + "…"
    except Exception:
        return text


def _derive_show_content(event_type: str, content: Any, metadata: dict[str, Any] | None) -> str | None:
    """Produce a human‑readable summary for the event payload.

    The goal is to avoid raw JSON for end users.
    """
    try:
        md = metadata or {}
        et = event_type or ""

        # System
        if et == SystemEvents.CONNECTED:
            return "已连接到服务器"
        if et == SystemEvents.ERROR:
            return f"系统错误：{content if isinstance(content, str) else '发生错误'}"
        if et == SystemEvents.HEARTBEAT:
            return "心跳"
        if et == SystemEvents.NOTICE:
            return str(content) if isinstance(content, str) else "通知"

        # Agent
        if et == AgentEvents.SESSION_CREATED:
            return "会话创建成功"
        if et == AgentEvents.THINKING:
            return "正在思考…"
        if et == AgentEvents.PARTIAL_ANSWER:
            if isinstance(content, str):
                return _truncate(content, 200)
            return "生成中…"
        if et == AgentEvents.FINAL_ANSWER:
            if isinstance(content, str):
                return content
            return "已生成答案"
        if et == AgentEvents.USER_CONFIRM:
            scope = (md.get("scope") if isinstance(md, dict) else None) or "plan"
            tasks = md.get("tasks") if isinstance(md, dict) else None
            count = len(tasks) if isinstance(tasks, list) else None
            summary = md.get("plan_summary") if isinstance(md, dict) else None
            if scope == "plan":
                base = f"请确认规划（{count} 个任务）" if count is not None else "请确认规划"
                if isinstance(summary, str) and summary.strip():
                    base += f"：{_truncate(summary.strip(), 120)}"
                return base
            return "请确认操作"
        if et == AgentEvents.TOOL_CALL:
            return "执行工具调用…"
        if et == AgentEvents.TOOL_RESULT:
            return "工具返回结果"
        if et == AgentEvents.ERROR:
            return f"Agent 错误：{content if isinstance(content, str) else '发生错误'}"
        if et == AgentEvents.TIMEOUT:
            return "执行超时"
        if et == AgentEvents.INTERRUPTED:
            return "执行已中断"

        # Plan
        if et == PlanEvents.START:
            if isinstance(content, dict) and isinstance(content.get("question"), str):
                return f"开始规划：{_truncate(content['question'], 120)}"
            return "开始规划"
        if et == PlanEvents.COMPLETED:
            tasks = None
            if isinstance(content, dict):
                tasks = content.get("tasks")
            count = len(tasks) if isinstance(tasks, list) else None
            base = f"规划完成（{count} 个任务）" if count is not None else "规划完成"
            if isinstance(content, dict) and isinstance(content.get("plan_summary"), str):
                base += f"：{_truncate(content['plan_summary'], 120)}"
            return base
        if et == PlanEvents.CANCELLED:
            return "规划已取消"
        if et == PlanEvents.STEP_COMPLETED:
            step_name = md.get("step_name") if isinstance(md, dict) else None
            return f"规划步骤完成：{step_name}" if step_name else "规划步骤完成"
        if et == PlanEvents.VALIDATION_ERROR:
            return f"规划验证错误：{content if isinstance(content, str) else '验证失败'}"

        # Solver
        if et == SolverEvents.START:
            task = content.get("task") if isinstance(content, dict) else None
            title = None
            if isinstance(task, dict):
                title = task.get("title") or task.get("name")
            elif hasattr(task, "title"):
                title = getattr(task, "title")
            return f"开始求解：{title}" if title else "开始求解"
        if et == SolverEvents.COMPLETED:
            task = content.get("task") if isinstance(content, dict) else None
            title = None
            if isinstance(task, dict):
                title = task.get("title") or task.get("name")
            elif hasattr(task, "title"):
                title = getattr(task, "title")
            return f"求解完成：{title}" if title else "求解完成"
        if et == SolverEvents.CANCELLED:
            return "求解已取消"
        if et == SolverEvents.RESTARTED:
            return "任务已重启"
        if et == SolverEvents.PROGRESS:
            progress = md.get("progress_percent") if isinstance(md, dict) else None
            if progress is not None:
                return f"求解进度：{progress}%"
            return "求解中…"
        if et == SolverEvents.STEP_FAILED:
            step_name = md.get("step_name") if isinstance(md, dict) else None
            return f"求解步骤失败：{step_name}" if step_name else "求解步骤失败"
        if et == SolverEvents.RETRY:
            attempt = md.get("attempt", 1) if isinstance(md, dict) else 1
            max_attempts = md.get("max_attempts", 3) if isinstance(md, dict) else 3
            return f"重试中…（{attempt}/{max_attempts}）"

        # Aggregate
        if et == AggregateEvents.START:
            return "开始聚合"
        if et == AggregateEvents.COMPLETED:
            return "聚合完成"

        # Pipeline
        if et == PipelineEvents.COMPLETED:
            return "流水线完成"

        # Error events
        if et == ErrorEvents.EXECUTION:
            return f"执行错误：{content if isinstance(content, str) else '执行失败'}"
        if et == ErrorEvents.VALIDATION:
            return f"验证错误：{content if isinstance(content, str) else '数据验证失败'}"
        if et == ErrorEvents.TIMEOUT:
            timeout_sec = md.get("timeout_seconds") if isinstance(md, dict) else None
            if timeout_sec:
                return f"超时错误：操作超过 {timeout_sec} 秒"
            return "超时错误"
        if et == ErrorEvents.RECOVERY_STARTED:
            return "开始恢复…"
        if et == ErrorEvents.RECOVERY_SUCCESS:
            return "恢复成功"
        if et == ErrorEvents.RECOVERY_FAILED:
            return f"恢复失败：{content if isinstance(content, str) else '无法恢复'}"

        return None
    except Exception:
        return None


def create_event(
    event_type: str,
    session_id: str | None = None,
    content: str | dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Create standard event"""
    event = {"event": event_type, "timestamp": datetime.now().isoformat()}

    if session_id:
        event["session_id"] = session_id
    if content is not None:
        event["content"] = content
    if metadata:
        event["metadata"] = metadata

    # Attach readable summary unless explicitly provided in kwargs
    if "show_content" in kwargs:
        pass
    else:
        sc = _derive_show_content(event_type, content, metadata)
        if sc is not None:
            event["show_content"] = sc

    event.update(kwargs)
    return event
