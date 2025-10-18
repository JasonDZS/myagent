# WebSocket Event Protocol Specification

## Overview

MyAgent uses a structured WebSocket event protocol for real-time communication between client and server. Events are JSON objects following the `EventProtocol` model with fields for session tracking, event type, payload, and metadata.

## Core Protocol Structure

### EventProtocol Base Model

```typescript
interface EventProtocol {
  session_id?: string        // Session identifier
  connection_id?: string     // WebSocket connection identifier
  step_id?: string          // For request/response pairing
  event: string             // Event type (e.g., "user.message", "agent.thinking")
  timestamp: string         // ISO8601 datetime
  content?: string | object // Main event payload
  metadata?: object         // Structured data (separate from content)
  show_content?: string     // Human-readable display text (Chinese)
  seq?: number              // Sequence number for reliable delivery
}
```

## Event Namespacing

Events are organized by prefix for clarity and organization:

| Namespace | Purpose | Examples |
|-----------|---------|----------|
| `user.*` | Client → Server | `user.message`, `user.response`, `user.ack` |
| `plan.*` | Planning stage | `plan.start`, `plan.completed`, `plan.cancelled` |
| `solver.*` | Task solving stage | `solver.start`, `solver.completed`, `solver.restarted` |
| `aggregate.*` | Results aggregation | `aggregate.start`, `aggregate.completed` |
| `agent.*` | Agent state/results | `agent.thinking`, `agent.tool_call`, `agent.final_answer` |
| `system.*` | System-level | `system.connected`, `system.error`, `system.heartbeat` |
| `error.*` | Error handling | `error.validation`, `error.timeout`, `error.retry` |
| `pipeline.*` | End-to-end flow | `pipeline.completed` |

## Content vs Metadata Pattern

**Clear separation between user-visible and structured data:**

| Field | Purpose | Example |
|-------|---------|---------|
| `content` | Human-readable summary or raw message | `"Generating response..."` |
| `metadata` | Structured machine-readable data | `{tasks: [...], task_count: 3}` |
| `show_content` | Display text for UI (auto-generated) | `"规划完成（3 个任务）"` |

**Rule**: Use `content` for simple text messages, `metadata` for complex structured data. Never mix.

## Reliable Delivery Mechanism

### Sequence Numbers (seq/ack)

Events are numbered for reliable delivery with client acknowledgment:

```javascript
// Server sends event with seq
{
  event: "agent.thinking",
  seq: 1,
  content: "Processing query..."
}

// Client acknowledges receipt
{
  event: "user.ack",
  seq: 1  // Acknowledging event seq=1
}
```

### Buffer Management

- Server maintains event buffer (last N events)
- On reconnect, client can request replay from last_seq
- ACK tracking prevents duplicate deliveries
- Unacknowledged events are retried

## Request/Response Pairing (step_id)

For interactive flows requiring correlation:

```javascript
// Server requests confirmation
{
  event: "agent.user_confirm",
  step_id: "plan_confirm_1",
  metadata: {
    tasks: [...],
    plan_summary: "..."
  }
}

// Client responds with matching step_id
{
  event: "user.response",
  step_id: "plan_confirm_1",
  content: {
    approved: true
  }
}
```

**Key**: step_id must match for request/response correlation.

## Event Flow Architecture

### 1. Plan → Solve → Aggregate Pipeline

```
user.message
    ↓
plan.start
    ↓
plan.completed (or plan.cancelled)
    ↓ [For each task]
  solver.start
    ↓
  agent.thinking, agent.tool_call, agent.tool_result
    ↓
  solver.completed (or solver.cancelled)
    ↓
aggregate.start
    ↓
aggregate.completed
    ↓
pipeline.completed
    ↓
agent.final_answer
```

### 2. User Confirmation Flow

```
agent.user_confirm (step_id: "confirm_1")
  ↓
[User decision]
  ↓
user.response (step_id: "confirm_1")
  ↓
[Continue or cancel based on response]
```

### 3. Reconnection & State Recovery

```
// Client disconnects and reconnects
user.reconnect_with_state
  ↓
// Server sends buffered events from last_seq
system.notice (event list)
  ↓
user.ack (acknowledging receipt)
  ↓
// Resume operation
```

## Session Management

### Session Lifecycle

1. **Create**: `user.create_session` → `agent.session_created`
2. **Active**: Bidirectional event flow
3. **Reconnect**: `user.reconnect_with_state` → Event replay
4. **End**: `agent.session_end`

### Connection Lifecycle

- New connection receives `system.connected`
- Heartbeat: `system.heartbeat` every 30s (configurable)
- Disconnect: Client detects and handles reconnection

## All Event Types

### User Events

| Event | Direction | Purpose |
|-------|-----------|---------|
| `user.message` | Client → Server | Submit query/task |
| `user.solve_tasks` | Client → Server | Direct solver execution |
| `user.response` | Client → Server | Answer confirmation requests |
| `user.cancel` | Client → Server | Cancel current operation |
| `user.cancel_task` | Client → Server | Cancel specific task |
| `user.restart_task` | Client → Server | Restart failed task |
| `user.ack` | Client → Server | Acknowledge received event |
| `user.create_session` | Client → Server | Initialize session |
| `user.reconnect` | Client → Server | Reconnect without state |
| `user.reconnect_with_state` | Client → Server | Reconnect and resume |
| `user.request_state` | Client → Server | Request session state |

### Plan Events

| Event | Payload | Metadata |
|-------|---------|----------|
| `plan.start` | `{question: "..."}` | Task context |
| `plan.completed` | `{tasks: [...]}` | `{task_count, plan_summary}` |
| `plan.cancelled` | `null` | Cancellation reason |
| `plan.coercion_error` | Error message | Error details |

### Solver Events

| Event | Payload | Metadata |
|-------|---------|----------|
| `solver.start` | `{task: {...}}` | Task details |
| `solver.completed` | `{task, result}` | Execution time, stats |
| `solver.cancelled` | `{task}` | Cancellation reason |
| `solver.restarted` | `{task}` | Retry count, reason |

### Agent Events

| Event | Purpose | Metadata |
|-------|---------|----------|
| `agent.thinking` | Agent is reasoning | Model name |
| `agent.tool_call` | Executing tool | Tool name, params |
| `agent.tool_result` | Tool execution result | Result summary |
| `agent.partial_answer` | Streaming response | Progress indicator |
| `agent.final_answer` | Complete response | N/A |
| `agent.user_confirm` | Needs confirmation | Tasks, options |
| `agent.error` | Agent error | Error type, context |
| `agent.timeout` | Execution timeout | Duration, stage |
| `agent.interrupted` | Execution interrupted | Reason |
| `agent.session_created` | Session initialized | Session ID, config |
| `agent.session_end` | Session closed | Duration, stats |
| `agent.state_exported` | State snapshot | Serialized state |
| `agent.state_restored` | State recovered | Restored state info |

### System Events

| Event | Payload | Purpose |
|-------|---------|---------|
| `system.connected` | `{server_version, capabilities}` | Connection established |
| `system.notice` | `{message: "..."}` | Informational message |
| `system.heartbeat` | `{timestamp}` | Keep-alive signal |
| `system.error` | `{error: "..."}` | System-level error |

### Error Events (Implemented)

Comprehensive error handling and recovery events. See `ERROR_RECOVERY_GUIDE.md` for detailed recovery strategies.

| Event | When | Metadata | Status |
|-------|------|----------|--------|
| `error.validation` | Input validation fails | Validation errors, field constraints | ✅ Production |
| `error.timeout` | Operation exceeds timeout | Timeout value, stage, retry details | ✅ Production |
| `error.execution` | Execution fails | Error type, context, recoverable flag | ✅ Production |
| `error.retry` | Automatic retry triggered | Attempt count, delay, original error | ✅ Production |
| `error.recovery_started` | Recovery attempt initiated | Recovery action, estimated duration | ✅ Production |
| `error.recovery_success` | Recovery succeeded | Recovery time, attempt count | ✅ Production |
| `error.recovery_failed` | Recovery failed | Error code, original/recovery errors | ✅ Production |

**Status**: All error events are production-ready. Full implementations in `myagent/ws/events.py` (ErrorEvents class) and `ERROR_RECOVERY_GUIDE.md`.

## Payload Examples

### Plan Confirmation Request

```javascript
{
  event: "agent.user_confirm",
  step_id: "plan_confirm_1",
  content: "请确认规划（3 个任务）：生成PPT、优化样式、导出文件",
  metadata: {
    scope: "plan",
    tasks: [
      {id: 1, title: "Generate PPT", description: "..."},
      {id: 2, title: "Optimize styling", description: "..."},
      {id: 3, title: "Export file", description: "..."}
    ],
    task_count: 3,
    plan_summary: "Generate a presentation with 5 slides..."
  },
  show_content: "请确认规划（3 个任务）：生成PPT、优化样式、导出文件"
}
```

### Solver Completion

```javascript
{
  event: "solver.completed",
  content: {
    task: {id: 1, title: "Generate PPT"},
    result: {slides: 5, status: "success"}
  },
  metadata: {
    execution_time_ms: 2500,
    llm_calls: 3,
    tokens_used: {input: 1200, output: 800}
  },
  show_content: "求解完成：Generate PPT"
}
```

### Error Event

```javascript
{
  event: "error.timeout",
  content: "Task execution exceeded 30 second timeout",
  metadata: {
    task_id: "task_1",
    timeout_seconds: 30,
    elapsed_seconds: 31.5,
    recovery_action: "retry"
  },
  show_content: "执行超时"
}
```

## Best Practices

### 1. Event Creation

```python
from myagent.ws.events import create_event, AgentEvents

# Simple event
event = create_event(
    AgentEvents.THINKING,
    session_id="sess_123",
    content="Processing..."
)

# Complex event with metadata
event = create_event(
    PlanEvents.COMPLETED,
    session_id="sess_123",
    content={"tasks": task_list},
    metadata={"task_count": len(task_list), "plan_summary": "..."},
    step_id="plan_1"
)
```

### 2. Sending Events

```python
from myagent.ws import send_websocket_message

await send_websocket_message(
    session_id="sess_123",
    event=create_event(...)
)
```

### 3. Handling Confirmations

```python
# In plan_solver.py pattern
event = create_event(
    AgentEvents.USER_CONFIRM,
    step_id=f"plan_confirm_{timestamp}",
    metadata={"tasks": tasks, "plan_summary": summary}
)
await send_websocket_message(session_id, event)

# Server waits for matching user.response
response = await wait_for_response(
    session_id=session_id,
    step_id=event["step_id"],
    timeout=60
)
```

### 4. Error Recovery

```python
# Send error event
event = create_event(
    "error.timeout",
    content="Operation timed out",
    metadata={
        "timeout_seconds": 30,
        "recovery_action": "retry"
    }
)
await send_websocket_message(session_id, event)

# Implement retry logic
retry_count = 0
while retry_count < max_retries:
    try:
        result = await execute_with_timeout(...)
        break
    except TimeoutError:
        retry_count += 1
        await send_websocket_message(session_id, create_event(
            "error.retry",
            metadata={"attempt": retry_count, "max_retries": max_retries}
        ))
```

## Migration Guide

### From Existing Code

Current implementations in `plan_solver.py` already follow most conventions:

1. Events sent via `send_websocket_message()`
2. Metadata separated from content
3. `show_content` auto-generated by `_derive_show_content()`
4. `step_id` used for confirmation correlation

### Required Changes

1. **Add seq/ack numbering** to server buffer
2. **Define error events** for consistent error handling
3. **Add reconnection state recovery** logic
4. **Document all custom payloads** in EVENT_PAYLOADS.md

## See Also

- `EVENT_DESIGN_GUIDE.md` - Detailed usage guide with examples
- `EVENT_PAYLOADS.md` - Complete payload reference (to be written)
- `ERROR_HANDLING.md` - Error event strategies (to be written)
- `RECONNECTION.md` - Reconnection and state recovery (to be written)
