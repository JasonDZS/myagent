# Content vs Metadata Usage Guide

## Overview

Clear separation between `content` and `metadata` fields is critical for consistency and maintainability. This guide defines the canonical pattern for every event type.

---

## Core Principle

```
content:  User-visible summary or primary payload
metadata: Structured machine-readable data
```

**Rule of Thumb**: If it's meant to be displayed to the user, use `content`. If it's structured data for processing, use `metadata`.

---

## Detailed Guidelines

### Content Field

**Purpose**: Human-readable information meant for display or primary payload

**Use Cases**:
- Final answers (agent.final_answer)
- User confirmations (agent.user_confirm)
- Error messages (error.timeout, error.validation)
- Short status messages (plan.start question)
- Streaming responses (agent.partial_answer)

**Format**:
- String preferred
- Short and descriptive (< 500 chars)
- Plain text or markdown
- May include interpolated values

**Example**:
```python
create_event(
    AgentEvents.FINAL_ANSWER,
    content="Here is the generated presentation with 5 slides..."
)
```

### Metadata Field

**Purpose**: Structured, machine-readable supplementary data

**Use Cases**:
- Task objects (solver.start)
- Statistics (execution_time, tokens_used)
- Context (task_id, step_id, attempt number)
- Complex nested objects
- Configuration parameters

**Format**:
- Dictionary with well-defined schema
- Supports nested structures
- Type-safe when possible
- Can be empty if no supplementary data

**Example**:
```python
create_event(
    SolverEvents.COMPLETED,
    content={"task": {"title": "..."}},
    metadata={
        "execution_time_ms": 2500,
        "llm_calls": 3,
        "tokens_used": {"input": 1200, "output": 800}
    }
)
```

---

## Event-Specific Patterns

### User Events

#### user.message
```python
content: User input message (string)
metadata: {
    source: "web" | "api" | "mobile",
    client_id: "...",
    user_id?: "..."
}
```

#### user.response
```python
content: {
    approved: true/false,
    feedback?: "User feedback"
}
metadata: {
    response_time_ms: 5000,
    decision_confidence?: 0.95
}
```

### Plan Events

#### plan.start
```python
content: {
    question: "User query here"
}
metadata: {
    plan_id: "plan_001",
    model: "gpt-4"
}
```

**Note**: `question` in content is the primary payload - it's key to understanding what's being planned.

#### plan.completed
```python
content: {
    tasks: [{id, title, description}, ...]
}
metadata: {
    task_count: 3,
    plan_summary: "Complete plan description",
    total_estimated_time_seconds: 300
}
```

**Note**: Tasks in content because they're primary. Summary in metadata because it's supplementary.

#### plan.step_completed
```python
content: "Brief step summary"
metadata: {
    step_name: "Input parsing",
    step_index: 1,
    total_steps: 5
}
```

#### plan.validation_error
```python
content: "Validation error message"
metadata: {
    error_code: "VAL_001",
    field: "task_count",
    constraint: "> 0"
}
```

### Solver Events

#### solver.start
```python
content: null or ""
metadata: {
    task: {id, title, description},
    task_id: "task_1",
    attempt: 1
}
```

**Note**: Task details belong in metadata - this is the trigger event for starting work.

#### solver.progress
```python
content: null or "求解中..."
metadata: {
    progress_percent: 45,
    current_step: "Generating content",
    estimated_completion_seconds: 30
}
```

#### solver.completed
```python
content: {
    task: {title},
    result: "Final task result"
}
metadata: {
    execution_time_ms: 45000,
    llm_calls: 5,
    tokens_used: {input, output}
}
```

#### solver.step_failed
```python
content: "Error message"
metadata: {
    step_name: "Content generation",
    error_code: "EXEC_001",
    recovery_action: "retry"
}
```

#### solver.retry
```python
content: null or "Retrying..."
metadata: {
    attempt: 2,
    max_attempts: 3,
    previous_error: "Timeout",
    backoff_ms: 2000
}
```

### Agent Events

#### agent.thinking
```python
content: null or "Brief thinking status"
metadata: {
    model: "gpt-4",
    max_tokens: 2000
}
```

#### agent.tool_call
```python
content: "Tool call description"
metadata: {
    tool_name: "web_search",
    tool_args: {query, max_results},
    call_id: "call_123"
}
```

#### agent.tool_result
```python
content: "Result summary"
metadata: {
    tool_name: "web_search",
    call_id: "call_123",
    result_summary: "Found 5 articles",
    execution_time_ms: 1200
}
```

#### agent.partial_answer
```python
content: "Streaming response text here..."
metadata: {
    completion_percent: 33,
    tokens_so_far: 500
}
```

#### agent.final_answer
```python
content: "Complete response or result"
metadata: {
    type: "text" | "structured" | "file",
    total_tokens: 2500,
    generation_time_ms: 45000
}
```

#### agent.user_confirm
```python
content: "Please confirm: Planning with 3 tasks"
metadata: {
    scope: "plan" | "task",
    tasks: [{id, title, description}, ...],
    task_count: 3,
    plan_summary: "Full description",
    options: [{value, label}, ...]
}
```

#### agent.error
```python
content: "Error message for display"
metadata: {
    error_code: "ERR_001",
    error_type: "ValueError",
    stage: "planning",
    context: {...}
}
```

#### agent.session_created
```python
content: {
    session_id: "sess_xyz789"
}
metadata: {
    server_version: "1.0.0",
    capabilities: ["planning", "solving"],
    session_ttl_hours: 24
}
```

### System Events

#### system.connected
```python
content: {
    server_name: "MyAgent"
}
metadata: {
    server_version: "1.0.0",
    capabilities: [...]
}
```

#### system.heartbeat
```python
content: {
    server_time: "2024-10-18T12:00:30Z"
}
metadata: {
    seq: 10,
    server_uptime_seconds: 3600
}
```

#### system.notice
```python
content: {
    message: "Maintenance in 1 hour"
}
metadata: {
    type: "info" | "warning" | "maintenance",
    severity: "low" | "medium" | "high"
}
```

### Error Events

#### error.validation
```python
content: "Validation error message"
metadata: {
    error_code: "ERR_VAL_001",
    field: "task_count",
    constraint: "> 0",
    provided_value: 0
}
```

#### error.timeout
```python
content: "Operation timed out"
metadata: {
    timeout_seconds: 30,
    elapsed_seconds: 31.5,
    stage: "planning"
}
```

#### error.execution
```python
content: "Execution failed"
metadata: {
    error_code: "ERR_EXEC_001",
    error_type: "RuntimeError",
    context: {...}
}
```

---

## Decision Tree

Use this to decide where to put data:

```
Is it meant to be displayed to the user?
├─ YES → Use content
└─ NO ┐
      Is it a complex object or structured data?
      ├─ YES → Use metadata
      └─ NO ┐
            Is it a supplementary field?
            ├─ YES → Use metadata
            └─ NO → Put in content as-is
```

---

## Anti-Patterns to Avoid

### ❌ Don't

```python
# Serialized JSON in content
create_event(
    EventType,
    content='{"task": {...}, "status": "..."}'  # Bad!
)

# Complex object in content without structure
create_event(
    EventType,
    content=task_object  # Bad if task_object is dict
)

# Metadata that should be in content
create_event(
    AgentEvents.FINAL_ANSWER,
    metadata={"answer": "..."}  # Bad! Put answer in content
)

# Duplicate data in both fields
create_event(
    EventType,
    content={"task": task},
    metadata={"task": task}  # Bad! Duplication
)
```

### ✅ Do

```python
# Properly separated fields
create_event(
    SolverEvents.COMPLETED,
    content={"task": {"title": "..."}, "result": "..."},
    metadata={
        "execution_time_ms": 2500,
        "tokens_used": {"input": 1200, "output": 800}
    }
)

# Clear separation
create_event(
    AgentEvents.FINAL_ANSWER,
    content="The complete answer here...",
    metadata={
        "generation_time_ms": 5000,
        "tokens": 2500
    }
)

# Metadata for complex objects
create_event(
    SolverEvents.START,
    metadata={
        "task": {...},
        "attempt": 1,
        "max_attempts": 3
    }
)
```

---

## Implementation Checklist

When creating an event, verify:

- [ ] **Content field**: Contains what the user needs to see OR primary payload
- [ ] **Metadata field**: Contains structured supplementary data
- [ ] **No duplication**: Data isn't repeated in both fields
- [ ] **Type consistency**: Data types match the pattern
- [ ] **Nested structures**: Complex objects in metadata, not content
- [ ] **Display-ready**: Content is ready to show without processing
- [ ] **Machine-readable**: Metadata is JSON-serializable

---

## Migration Guide

For existing code, apply this priority:

1. **High Priority** (Do first):
   - `plan.completed`: tasks → content
   - `solver.completed`: task + result → content
   - `agent.final_answer`: answer → content

2. **Medium Priority** (Next):
   - `solver.start`: task → metadata
   - `agent.tool_call`: tool_name + args → metadata
   - `agent.user_confirm`: tasks + summary → metadata

3. **Low Priority** (Later):
   - `agent.thinking`: model config → metadata
   - `system.*`: version info → metadata

---

## Examples by Event

### Complete Example 1: Plan Completion

```python
# Create plan completion event
tasks_list = [
    {"id": 1, "title": "Generate content", "description": "..."},
    {"id": 2, "title": "Format slides", "description": "..."},
]

event = create_event(
    PlanEvents.COMPLETED,
    session_id="sess_001",
    content={
        "tasks": tasks_list  # Primary payload
    },
    metadata={
        "task_count": len(tasks_list),  # Supplementary
        "plan_summary": "5-slide AI presentation",
        "planning_time_ms": 3000,
        "llm_calls": 2
    }
)

# Frontend displays:
# - show_content: "规划完成（2 个任务）"
# - Renders tasks from content
# - Logs execution time from metadata
```

### Complete Example 2: Error with Recovery

```python
event = create_event(
    ErrorEvents.TIMEOUT,
    session_id="sess_001",
    content="API request timed out after 30 seconds",  # User message
    metadata={
        "error_code": "ERR_TIMEOUT_001",
        "timeout_seconds": 30,
        "elapsed_seconds": 31.5,
        "stage": "solving",
        "operation": "tool_call",
        "recovery_action": "retry",
        "attempt": 1,
        "max_attempts": 3,
        "retry_after_ms": 2000
    }
)

# Frontend:
# - Shows show_content to user
# - Uses metadata for retry logic
# - Logs error_code for monitoring
```

### Complete Example 3: Tool Execution

```python
event = create_event(
    AgentEvents.TOOL_RESULT,
    session_id="sess_001",
    content="Successfully fetched 5 web search results",  # User-facing summary
    metadata={
        "tool_name": "web_search",
        "call_id": "call_123",
        "result_count": 5,
        "execution_time_ms": 1200,
        "tokens_used": {"input": 100, "output": 250},
        "cache_hit": False
    }
)

# Frontend:
# - Displays show_content (auto-generated from content)
# - Processes result_count for UI updates
# - Sends metrics to monitoring (execution_time_ms, tokens_used)
```

---

## Validation Rules

### Content Field Validation

```python
def validate_content(event_type: str, content: Any) -> bool:
    """Ensure content follows pattern"""

    # String content: OK (for simple messages)
    if isinstance(content, str):
        return len(content) > 0 and len(content) < 10000

    # Dict content: Must have clear primary payload
    if isinstance(content, dict):
        if not content:  # Empty dict is suspicious
            return event_type in {"solver.start", "system.heartbeat"}
        return True

    # None content: Only for events with no primary data
    if content is None:
        return event_type in {"error.recovery_started", "system.heartbeat"}

    return False
```

### Metadata Field Validation

```python
def validate_metadata(metadata: dict[str, Any]) -> bool:
    """Ensure metadata is well-formed"""

    if not isinstance(metadata, dict):
        return False

    # Check JSON serializable (important for WebSocket)
    try:
        import json
        json.dumps(metadata)
        return True
    except (TypeError, ValueError):
        return False
```

---

## FAQ

**Q: Can metadata be empty?**
A: Yes, if there's no supplementary data. Include only needed fields.

**Q: Can content be None?**
A: Only for events where there's no primary payload (e.g., `error.recovery_started`).

**Q: Should I use show_content or content?**
A: Use `content` for data. `show_content` is auto-generated from content + metadata for display.

**Q: How deep can metadata nesting go?**
A: Typically 2-3 levels. If more, consider if you need a different event structure.

**Q: Is it OK to put arrays in content?**
A: Yes, if they're the primary payload (e.g., tasks in plan.completed).

**Q: Should I include timing data in content?**
A: No, timing belongs in metadata unless it's critical to the user message.

---

## References

- EVENT_PROTOCOL.md: Core protocol definition
- EVENT_PAYLOADS.md: Complete payload examples
- events.py: Actual implementation with _derive_show_content()
