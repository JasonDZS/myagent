# Event Payloads - Detailed Format Specification

Complete payload format reference for all MyAgent WebSocket event types with TypeScript definitions, validation rules, and real-world examples.

## Table of Contents

1. [Protocol Overview](#protocol-overview)
2. [User Events](#user-events)
3. [Plan Events](#plan-events)
4. [Solver Events](#solver-events)
5. [Agent Events](#agent-events)
6. [System Events](#system-events)
7. [Error Events](#error-events)
8. [Payload Validation](#payload-validation)
9. [Code Generation](#code-generation)

---

## Protocol Overview

### EventProtocol Base Structure

All events follow this base structure:

```typescript
interface EventProtocol {
  session_id?: string;           // Unique session identifier
  connection_id?: string;        // WebSocket connection ID
  step_id?: string;              // Request/response correlation ID
  event: string;                 // Event type (e.g., "plan.start")
  timestamp: string;             // ISO8601 timestamp
  content: string | object | null;  // Primary payload (user-visible)
  metadata?: Record<string, any>;    // Supplementary data (machine-readable)
}
```

### Content vs Metadata Rules

- **content**: User-visible summary or primary payload
  - Type: `string` or `object` (dict in Python)
  - Use for: Information users need to see
  - Examples: final answers, plan descriptions, error messages

- **metadata**: Structured supplementary data
  - Type: Always `object` (dict in Python)
  - Use for: Statistics, context, processing instructions
  - Examples: execution times, token counts, error codes

---

## User Events

User events are sent **from client to server**.

### user.create_session

Create new WebSocket session.

**Purpose**: Initialize new agent session with optional configuration

**Payload Structure**:
```typescript
{
  event: "user.create_session",
  content?: {
    // Optional: initial context or configuration
    project_name?: string;
    session_name?: string;
    config?: Record<string, any>;
  },
  metadata?: {
    client_version?: string;
    client_id?: string;
  }
}
```

**Real Example**:
```json
{
  "event": "user.create_session",
  "content": {
    "project_name": "PowerPoint Generator",
    "session_name": "generate_slides_oct18"
  },
  "metadata": {
    "client_version": "1.0.0",
    "client_id": "client_abc123"
  }
}
```

**Response**: `agent.session_created` event

---

### user.message

Send user query or instruction to agent.

**Purpose**: Primary user input for agent processing

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "user.message",
  content: string;  // User query/instruction
  metadata?: {
    message_type?: "query" | "instruction" | "feedback";
    priority?: "low" | "normal" | "high";
    source?: string;  // UI section, API endpoint, etc.
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "user.message",
  "timestamp": "2024-10-18T14:30:00Z",
  "content": "Create a 5-slide presentation about AI trends",
  "metadata": {
    "message_type": "query",
    "priority": "normal",
    "source": "web_ui"
  }
}
```

**Response Chain**: `plan.start` → `plan.completed` → `solver.start` → ... → `agent.final_answer`

---

### user.response

Send response to agent confirmation or validation request.

**Purpose**: Provide user input for confirmation flows (user.confirm events)

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;           // Correlates with agent.user_confirm step_id
  event: "user.response",
  content: {
    approved: boolean;       // User approved or rejected
    feedback?: string;       // Optional user feedback
    data?: Record<string, any>;  // Corrected data if applicable
  },
  metadata?: {
    response_time_ms?: number;
    user_action?: "approve" | "reject" | "modify";
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "confirm_001",
  "event": "user.response",
  "content": {
    "approved": true,
    "feedback": "Looks good, but change slide 2 color to blue"
  },
  "metadata": {
    "response_time_ms": 3500,
    "user_action": "approve"
  }
}
```

**Response**: Solver continues with approved plan

---

### user.ack

Acknowledge receipt of events (for reliable delivery).

**Purpose**: Confirm event reception and enable buffer pruning

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "user.ack",
  content?: {
    last_seq: number;        // Last sequence number received
  },
  metadata?: {
    received_count?: number;
    buffer_size?: number;
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "user.ack",
  "content": {
    "last_seq": 42
  },
  "metadata": {
    "received_count": 10,
    "buffer_size": 1024
  }
}
```

---

### user.cancel

Cancel current operation.

**Purpose**: Stop agent execution

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "user.cancel",
  content?: {
    reason?: string;  // Why user cancelled
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "user.cancel",
  "content": {
    "reason": "User changed mind"
  }
}
```

---

### user.reconnect

Resume session after brief connection loss.

**Purpose**: Reconnect to existing session (<60s disconnect)

**Payload Structure**:
```typescript
{
  event: "user.reconnect",
  content: {
    session_id: string;      // Previous session ID
    last_seq?: number;       // Last event sequence received
  }
}
```

**Real Example**:
```json
{
  "event": "user.reconnect",
  "content": {
    "session_id": "sess_xyz789",
    "last_seq": 42
  }
}
```

---

### user.reconnect_with_state

Recover session with client-provided state snapshot.

**Purpose**: Recover extended disconnect (60s-24h) with state export

**Payload Structure**:
```typescript
{
  event: "user.reconnect_with_state",
  content: {
    signed_state: string;    // State snapshot (signed/encrypted)
    last_seq: number;
    last_event_id?: string;
  },
  metadata?: {
    offline_duration_ms: number;
    state_version: string;
  }
}
```

---

### user.request_state

Request state export (not reconnection).

**Purpose**: Export current session state for later recovery

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "user.request_state",
  metadata?: {
    include_history?: boolean;  // Include full event history
    compression?: "gzip" | "none";
  }
}
```

---

## Plan Events

Plan events are emitted **by the server** during planning phase.

### plan.start

Planning phase initiated.

**Purpose**: Notify client that planning has started

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "plan.start",
  step_id: string;
  content: {
    question: string;        // User's question/request
    context?: string;        // Additional context
  },
  metadata: {
    plan_id: string;
    timeout_seconds: number;
    model: string;           // LLM model used
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "plan_001",
  "event": "plan.start",
  "timestamp": "2024-10-18T14:30:05Z",
  "content": {
    "question": "Create a 5-slide presentation about AI trends",
    "context": "Professional business presentation"
  },
  "metadata": {
    "plan_id": "plan_abc123",
    "timeout_seconds": 120,
    "model": "gpt-4"
  }
}
```

---

### plan.completed

Planning phase finished successfully.

**Purpose**: Deliver final plan to solver

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "plan.completed",
  content: {
    tasks: Array<{
      id: string;
      title: string;
      description: string;
      estimated_duration_sec?: number;
    }>;
  },
  metadata: {
    task_count: number;
    plan_summary: string;
    total_estimated_tokens: number;
    llm_calls: number;
    planning_time_ms: number;
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "plan_001",
  "event": "plan.completed",
  "content": {
    "tasks": [
      {
        "id": "task_1",
        "title": "Generate content for slide 1",
        "description": "Create title slide with introduction"
      },
      {
        "id": "task_2",
        "title": "Generate content for slide 2",
        "description": "Cover current AI trends"
      }
    ]
  },
  "metadata": {
    "task_count": 2,
    "plan_summary": "5-slide presentation with content generation and formatting",
    "total_estimated_tokens": 3200,
    "llm_calls": 2,
    "planning_time_ms": 5400
  }
}
```

---

### plan.step_completed

Individual planning step completed.

**Purpose**: Report progress on multi-step planning

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "plan.step_completed",
  content: {
    step_name: string;
    step_result: any;
  },
  metadata: {
    step_index: number;
    step_duration_ms: number;
    tokens_used: number;
  }
}
```

---

### plan.validation_error

Plan validation failed.

**Purpose**: Notify of invalid plan structure

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "plan.validation_error",
  content: {
    error_message: string;
    field?: string;
    constraint?: string;
  },
  metadata: {
    error_code: string;     // e.g., "ERR_VALIDATION_400"
    validation_errors: Array<string>;
  }
}
```

---

## Solver Events

Solver events are emitted **by the server** during task solving phase.

### solver.start

Task solving phase initiated.

**Purpose**: Notify client that solver is starting tasks

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "solver.start",
  metadata: {
    task_count: number;
    total_tasks: number;
    estimated_duration_sec: number;
  }
}
```

---

### solver.progress

Report progress during solving.

**Purpose**: Provide real-time progress updates

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "solver.progress",
  content?: {
    current_task: string;
    status: string;
  },
  metadata: {
    progress_percent: number;  // 0-100
    current_step: number;
    completed_steps: number;
    total_steps: number;
    elapsed_time_ms: number;
    estimated_remaining_ms?: number;
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "solver_001",
  "event": "solver.progress",
  "content": {
    "current_task": "Generating slide 2 content",
    "status": "processing"
  },
  "metadata": {
    "progress_percent": 40,
    "current_step": 2,
    "completed_steps": 1,
    "total_steps": 5,
    "elapsed_time_ms": 8500,
    "estimated_remaining_ms": 12750
  }
}
```

---

### solver.completed

All tasks completed successfully.

**Purpose**: Deliver solver results

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "solver.completed",
  content: {
    task_results: Array<{
      task_id: string;
      result: any;
      status: "success" | "failed" | "partial";
    }>;
  },
  metadata: {
    total_tasks: number;
    successful_tasks: number;
    failed_tasks: number;
    total_execution_time_ms: number;
    total_tokens_used: number;
  }
}
```

---

### solver.step_failed

Individual solving step failed.

**Purpose**: Report step-level failure

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "solver.step_failed",
  content: {
    error_message: string;
    step_name: string;
  },
  metadata: {
    step_index: number;
    error_code: string;
    error_type: string;      // e.g., "TimeoutError", "ExecutionError"
    recovery_possible: boolean;
  }
}
```

---

### solver.retry

Retry attempt in progress.

**Purpose**: Notify of automatic retry

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "solver.retry",
  content?: {
    step_name: string;
  },
  metadata: {
    attempt: number;
    max_attempts: number;
    backoff_ms: number;
  }
}
```

---

## Agent Events

Agent events are emitted **by the server** during agent reasoning and action.

### agent.thinking

Agent is reasoning about the problem.

**Purpose**: Provide thinking/reasoning feedback

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "agent.thinking",
  content: string;  // Thinking process description
  metadata: {
    model: string;
    max_tokens: number;
    temperature: number;
    thinking_type: "analysis" | "planning" | "reasoning";
  }
}
```

---

### agent.tool_call

Agent is calling a tool.

**Purpose**: Notify client of tool invocation

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "agent.tool_call",
  content: {
    tool_name: string;
    tool_description: string;
    arguments: Record<string, any>;
  },
  metadata: {
    call_id: string;
    tool_type: string;
    estimated_duration_ms?: number;
  }
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "action_001",
  "event": "agent.tool_call",
  "content": {
    "tool_name": "generate_text",
    "tool_description": "Generate text content using LLM",
    "arguments": {
      "prompt": "Write an introduction for AI trends slide",
      "max_length": 500
    }
  },
  "metadata": {
    "call_id": "call_xyz123",
    "tool_type": "llm",
    "estimated_duration_ms": 3000
  }
}
```

---

### agent.tool_result

Tool execution completed.

**Purpose**: Deliver tool result to agent

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "agent.tool_result",
  content: {
    result: any;  // Tool output
    status: "success" | "failed";
  },
  metadata: {
    call_id: string;
    execution_time_ms: number;
    tokens_used?: number;
  }
}
```

---

### agent.partial_answer

Streaming partial answer.

**Purpose**: Stream text output for streaming responses

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "agent.partial_answer",
  content: string;  // Partial text chunk
  metadata: {
    chunk_index: number;
    completion_percent?: number;
  }
}
```

---

### agent.final_answer

Agent's final answer.

**Purpose**: Deliver complete answer

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "agent.final_answer",
  content: {
    answer: string;
    answer_type: "text" | "json" | "code" | "structured";
  },
  metadata: {
    generation_time_ms: number;
    total_tokens_used: number;
    model: string;
  }
}
```

---

### agent.user_confirm

Request user confirmation.

**Purpose**: Ask user for approval before proceeding

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "agent.user_confirm",
  content: {
    message: string;
    confirmation_type: "approve" | "select" | "input";
    options?: Array<{
      id: string;
      label: string;
      description?: string;
    }>;
  },
  metadata: {
    timeout_seconds?: number;
    critical: boolean;  // Important confirmation
  }
}
```

---

## System Events

System events are **bidirectional** (server ↔ client).

### system.connected

Connection established.

**Purpose**: Confirm WebSocket connection

**Payload Structure**:
```typescript
{
  connection_id: string;
  event: "system.connected",
  content: {
    server_version: string;
    server_time: string;  // ISO8601
  },
  metadata: {
    server_uptime_seconds: number;
    active_sessions: number;
  }
}
```

---

### system.heartbeat

Connection keepalive.

**Purpose**: Maintain connection and detect disconnects

**Payload Structure**:
```typescript
{
  session_id?: string;
  event: "system.heartbeat",
  content?: {
    server_time: string;
  },
  metadata: {
    seq: number;
    server_uptime_seconds: number;
  }
}
```

---

### system.error

Generic system error.

**Purpose**: Report system-level errors

**Payload Structure**:
```typescript
{
  session_id?: string;
  event: "system.error",
  content: string;  // Error message
  metadata: {
    error_code: string;
    severity: "info" | "warning" | "error";
  }
}
```

---

## Error Events

Error events are emitted **by the server** for error handling.

### error.validation

Validation error occurred.

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "error.validation",
  content: string;
  metadata: {
    error_code: "ERR_VALIDATION_400";
    field?: string;
    constraint?: string;
    recoverable: boolean;
  }
}
```

---

### error.timeout

Timeout error occurred.

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "error.timeout",
  content: string;
  metadata: {
    error_code: "ERR_TIMEOUT_500";
    timeout_seconds: number;
    elapsed_seconds: number;
    stage: string;
    attempt: number;
    max_attempts: number;
    retry_after_ms: number;
    recovery_strategy: string;
  }
}
```

---

### error.execution

Execution error occurred.

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "error.execution",
  content: string;
  metadata: {
    error_code: "ERR_EXECUTION_600";
    error_type: string;
    context: Record<string, any>;
    recoverable: boolean;
  }
}
```

---

### error.retry

Retry attempt starting.

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "error.retry",
  content?: string;
  metadata: {
    attempt: number;
    max_attempts: number;
    delay_ms: number;
    error: string;
  }
}
```

---

### error.recovery_started

Recovery attempt initiated.

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "error.recovery_started",
  content: string;
  metadata: {
    recovery_action: string;
    estimated_duration_ms?: number;
  }
}
```

---

### error.recovery_success

Recovery succeeded.

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "error.recovery_success",
  content?: string;
  metadata: {
    recovery_time_ms: number;
    attempts: number;
  }
}
```

---

### error.recovery_failed

Recovery failed.

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "error.recovery_failed",
  content: string;
  metadata: {
    error_code: string;
    attempts: number;
    original_error: string;
    recovery_error: string;
  }
}
```

---

## Payload Validation

### Validation Rules by Event Type

| Event | Required Fields | Content Type | Metadata Type |
|-------|-----------------|--------------|---------------|
| user.message | session_id, content | string | object |
| user.response | session_id, step_id, content | object | object |
| plan.completed | content, metadata | object | object |
| agent.tool_call | content | object | object |
| agent.final_answer | content | object | object |
| error.timeout | step_id, content | string | object |

### Python Validation Functions

```python
from typing import Any, Dict

def validate_content(event_type: str, content: Any) -> bool:
    """Validate content field matches event type."""
    # User events
    if event_type == "user.message":
        return isinstance(content, str)
    if event_type == "user.response":
        return isinstance(content, dict) and "approved" in content

    # Plan events
    if event_type in ("plan.completed", "plan.validation_error"):
        return isinstance(content, (str, dict))

    # Agent events
    if event_type == "agent.tool_call":
        return isinstance(content, dict) and "tool_name" in content
    if event_type == "agent.final_answer":
        return isinstance(content, dict) and "answer" in content

    return True

def validate_metadata(event_type: str, metadata: Dict[str, Any]) -> bool:
    """Validate metadata field matches event type."""
    if not isinstance(metadata, dict):
        return False

    # Solver progress requires progress_percent
    if event_type == "solver.progress":
        return "progress_percent" in metadata

    # Error events require error_code
    if event_type.startswith("error."):
        return "error_code" in metadata

    return True
```

---

## Code Generation

### TypeScript Type Generation

Generate TypeScript interfaces for type safety:

```bash
# From Python Pydantic models
python -m myagent.tools.generate_types --output types.ts

# Manual TypeScript generation
npx json-schema-to-typescript EVENT_PAYLOADS_DETAILED.md --output event_types.ts
```

### Python Dataclass Generation

Generate Python dataclasses for validation:

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class UserMessage:
    session_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    event: str = "user.message"
    timestamp: str = None

@dataclass
class PlanCompleted:
    session_id: str
    step_id: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    event: str = "plan.completed"
    timestamp: str = None
```

---

## Appendix: Complete Event Reference

### Event Type Checklist

**User Events** (Client → Server):
- [ ] user.create_session
- [ ] user.message
- [ ] user.response
- [ ] user.ack
- [ ] user.cancel
- [ ] user.reconnect
- [ ] user.reconnect_with_state
- [ ] user.request_state

**Plan Events** (Server → Client):
- [ ] plan.start
- [ ] plan.completed
- [ ] plan.step_completed
- [ ] plan.validation_error

**Solver Events** (Server → Client):
- [ ] solver.start
- [ ] solver.progress
- [ ] solver.completed
- [ ] solver.step_failed
- [ ] solver.retry

**Agent Events** (Server → Client):
- [ ] agent.thinking
- [ ] agent.tool_call
- [ ] agent.tool_result
- [ ] agent.partial_answer
- [ ] agent.final_answer
- [ ] agent.user_confirm
- [ ] agent.session_created
- [ ] agent.session_ended

**System Events** (Bidirectional):
- [ ] system.connected
- [ ] system.heartbeat
- [ ] system.error

**Error Events** (Server → Client):
- [ ] error.validation
- [ ] error.timeout
- [ ] error.execution
- [ ] error.retry
- [ ] error.recovery_started
- [ ] error.recovery_success
- [ ] error.recovery_failed

---

**Total Events Documented**: 40+ event types with complete payload specifications

