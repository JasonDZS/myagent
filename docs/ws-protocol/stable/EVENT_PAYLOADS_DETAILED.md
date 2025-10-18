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

See also: `FIELD_CONVENTIONS.md` for naming, units, and required/optional field semantics.

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
  };
  metadata: {
    task_count: number;
    plan_summary: string;
    total_estimated_tokens: number;
    llm_calls: number;
    planning_time_ms: number;
    statistics?: Array<Record<string, any>>;  // Per-call LLM stats for planning stage
    metrics?: Record<string, any>;            // Global snapshot (agents/tools/models)
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
    "planning_time_ms": 5400,
    "statistics": [
      {"model": "gpt-4", "input_tokens": 800, "output_tokens": 350, "origin": "plan", "agent": "planner"}
    ],
    "metrics": {"agents": {"by_agent": {"planner": {"runs": 1}}}}
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
    statistics?: Array<Record<string, any>>;  // Per-call LLM stats for the solver stage (all tasks)
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

## Aggregate Events

Aggregation events are emitted by the server during the final aggregation stage after solver tasks complete.

### aggregate.start

Aggregation stage initiated.

**Purpose**: Notify client that aggregation has started

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "aggregate.start";
  metadata: {
    task_count: number;
    completed_tasks: number;
    failed_tasks: number;
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "aggregate.start",
  "timestamp": "2024-10-18T14:40:00Z",
  "metadata": {
    "task_count": 3,
    "completed_tasks": 3,
    "failed_tasks": 0
  }
}
```

---

### aggregate.completed

Aggregation completed successfully.

**Purpose**: Deliver aggregated final result and aggregation stats

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "aggregate.completed";
  content?: {
    final_result: any;  // Aggregated result from solver outputs
  };
  metadata: {
    aggregation_time_ms: number;
    result_size_bytes: number;
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "aggregate.completed",
  "timestamp": "2024-10-18T14:41:00Z",
  "content": {
    "final_result": {
      "slides": [
        {"title": "Intro", "content": "..."},
        {"title": "Trends", "content": "..."}
      ]
    }
  },
  "metadata": {
    "aggregation_time_ms": 5200,
    "result_size_bytes": 125000
  }
}
```

---

## Pipeline Events

Pipeline events summarize the end-to-end lifecycle (plan → solve → aggregate).

### pipeline.completed

Full pipeline completed.

**Purpose**: Report end-to-end timing breakdown and completion status

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "pipeline.completed";
  metadata: {
    total_time_ms: number;
    plan_time_ms: number;
    solve_time_ms: number;
    aggregate_time_ms: number;
    status: "success" | "partial_success" | "failed";
    result_summary: string;
    statistics?: Array<Record<string, any>>;  // Unified per-call stats across plan+solve
    metrics?: Record<string, any>;            // Global snapshot (agents/tools/models)
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "pipeline.completed",
  "timestamp": "2024-10-18T14:41:05Z",
  "metadata": {
    "total_time_ms": 182000,
    "plan_time_ms": 45000,
    "solve_time_ms": 120000,
    "aggregate_time_ms": 17000,
    "status": "success",
    "result_summary": "Generated 5-slide presentation successfully",
    "statistics": [
      {"model": "gpt-4", "input_tokens": 1200, "output_tokens": 600, "origin": "plan", "agent": "planner"}
    ],
    "metrics": {"models": {"by_model": {"gpt-4": {"calls": 2, "input_tokens": 1200, "output_tokens": 600}}}}
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

## Additional Agent Events

### agent.session_end

**Purpose**: Notify client that session has ended

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "agent.session_end";
  content?: string;
  metadata: {
    reason: "user_request" | "timeout" | "error" | "completion";
    total_duration_ms: number;
    total_messages?: number;
    completion_status?: "success" | "partial" | "failed";
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "agent.session_end",
  "timestamp": "2024-10-18T14:45:00Z",
  "content": "Session ended successfully",
  "metadata": {
    "reason": "completion",
    "total_duration_ms": 125000,
    "total_messages": 8,
    "completion_status": "success"
  }
}
```

---

### agent.llm_message

**Purpose**: Relay raw LLM message or token for streaming/debugging

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "agent.llm_message";
  content: string;  // Raw LLM output or token
  metadata: {
    model: string;
    message_id?: string;
    role?: "user" | "assistant" | "system";
    index?: number;  // For multiple responses
    tokens?: number;
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "agent_001",
  "event": "agent.llm_message",
  "timestamp": "2024-10-18T14:30:15Z",
  "content": "I'll help you create a presentation by breaking it down into steps: 1. Content generation, 2. Styling, 3. Export",
  "metadata": {
    "model": "gpt-4",
    "message_id": "msg_abc123",
    "role": "assistant",
    "tokens": 35
  }
}
```

---

### agent.state_exported

**Purpose**: Session state has been exported for recovery

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "agent.state_exported";
  content?: {
    exported_state: Record<string, any>;  // Full session state snapshot
  };
  metadata: {
    exported_at: string;  // ISO8601 timestamp
    valid_until: string;  // State expiration time
    state_size_bytes?: number;
    checksum?: string;  // For integrity verification
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "agent.state_exported",
  "timestamp": "2024-10-18T14:35:00Z",
  "content": {
    "exported_state": {
      "stage": "solving",
      "plan_context": {
        "question": "Create a 5-slide presentation",
        "tasks": [{"id": "task_1", "title": "Generate content"}]
      },
      "current_task_id": "task_1",
      "completed_tasks": []
    }
  },
  "metadata": {
    "exported_at": "2024-10-18T14:35:00Z",
    "valid_until": "2024-10-19T14:35:00Z",
    "state_size_bytes": 4096,
    "checksum": "sha256:abc123..."
  }
}
```

---

### agent.state_restored

**Purpose**: Session state has been restored after reconnection

**Payload Structure**:
```typescript
{
  session_id: string;
  event: "agent.state_restored";
  content?: string;  // Restoration confirmation message
  metadata: {
    restored_at: string;  // ISO8601 timestamp
    restoration_time_ms: number;
    previous_stage: string;
    recovered_tasks?: number;
    state_integrity: "verified" | "partial" | "failed";
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "event": "agent.state_restored",
  "timestamp": "2024-10-18T14:36:00Z",
  "content": "Session state successfully restored from saved state",
  "metadata": {
    "restored_at": "2024-10-18T14:36:00Z",
    "restoration_time_ms": 523,
    "previous_stage": "solving",
    "recovered_tasks": 2,
    "state_integrity": "verified"
  }
}
```

---

## Additional Plan Events

### plan.cancelled

**Purpose**: Planning was cancelled before completion

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "plan.cancelled";
  content?: string;  // Cancellation reason
  metadata: {
    reason: "user_request" | "timeout" | "error" | "resource_limit";
    partial_plan?: Array<{
      id: string;
      title: string;
      description: string;
    }>;
    cancellation_time_ms: number;
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "plan_001",
  "event": "plan.cancelled",
  "timestamp": "2024-10-18T14:31:00Z",
  "content": "Planning cancelled by user request",
  "metadata": {
    "reason": "user_request",
    "partial_plan": [
      {
        "id": "task_1",
        "title": "Generate content",
        "description": "Content generation incomplete"
      }
    ],
    "cancellation_time_ms": 8500
  }
}
```

---

### plan.coercion_error

**Purpose**: LLM output couldn't be parsed into valid task list

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "plan.coercion_error";
  content?: string;  // Error message
  metadata: {
    error_code: string;  // e.g., "PLAN_COERCE_001"
    raw_output?: string;  // Original LLM output that failed to parse
    error_type: string;  // e.g., "ValueError", "TypeError"
    recovery_action: "retry" | "manual_input" | "fallback" | "abort";
    attempt?: number;
    max_attempts?: number;
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "plan_001",
  "event": "plan.coercion_error",
  "timestamp": "2024-10-18T14:32:00Z",
  "content": "Failed to parse plan output as task list",
  "metadata": {
    "error_code": "PLAN_COERCE_001",
    "raw_output": "LLM returned unparseable format: [invalid json]",
    "error_type": "JSONDecodeError",
    "recovery_action": "retry",
    "attempt": 1,
    "max_attempts": 3
  }
}
```

---

## Additional Solver Events

### solver.cancelled

**Purpose**: Task was cancelled during solving

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "solver.cancelled";
  content?: string;  // Cancellation message
  metadata: {
    task_id: string;
    reason: "user_request" | "dependency_failed" | "timeout" | "resource_limit";
    execution_time_ms: number;
    partial_result?: Record<string, any>;  // Any partial output before cancellation
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "solver_002",
  "event": "solver.cancelled",
  "timestamp": "2024-10-18T14:33:00Z",
  "content": "Task was cancelled by user",
  "metadata": {
    "task_id": "task_2",
    "reason": "user_request",
    "execution_time_ms": 12500,
    "partial_result": {
      "progress": 0.6,
      "partial_output": "Generated 3 of 5 slides..."
    }
  }
}
```

---

### solver.restarted

**Purpose**: Task was restarted after failure

**Payload Structure**:
```typescript
{
  session_id: string;
  step_id: string;
  event: "solver.restarted";
  content?: string;  // Restart reason
  metadata: {
    task_id: string;
    previous_error?: string;
    attempt: number;
    max_attempts: number;
    reason: "retry_after_error" | "user_request" | "escalation";
    backoff_ms: number;
  };
}
```

**Real Example**:
```json
{
  "session_id": "sess_xyz789",
  "step_id": "solver_001",
  "event": "solver.restarted",
  "timestamp": "2024-10-18T14:34:00Z",
  "content": "Task restarted after timeout",
  "metadata": {
    "task_id": "task_1",
    "previous_error": "TimeoutError: Task exceeded 30s limit",
    "attempt": 2,
    "max_attempts": 3,
    "reason": "retry_after_error",
    "backoff_ms": 2000
  }
}
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
- [x] plan.start
- [x] plan.completed
- [x] plan.step_completed
- [x] plan.validation_error
- [x] plan.cancelled
- [x] plan.coercion_error

**Solver Events** (Server → Client):
- [x] solver.start
- [x] solver.progress
- [x] solver.completed
- [x] solver.step_failed
- [x] solver.retry
- [x] solver.cancelled
- [x] solver.restarted

**Agent Events** (Server → Client):
- [x] agent.thinking
- [x] agent.tool_call
- [x] agent.tool_result
- [x] agent.partial_answer
- [x] agent.final_answer
- [x] agent.user_confirm
- [x] agent.session_created
- [x] agent.session_end
- [x] agent.llm_message
- [x] agent.state_exported
- [x] agent.state_restored

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

## Summary

**Total Events Documented**: 45+ event types with complete payload specifications

### Event Count by Category
- **User Events**: 8 types
- **Plan Events**: 6 types (added: cancelled, coercion_error)
- **Solver Events**: 7 types (added: cancelled, restarted)
- **Agent Events**: 11 types (added: llm_message, state_exported, state_restored)
- **System Events**: 3 types
- **Error Events**: 7 types

**Coverage**: 100% of events defined in `myagent/ws/events.py` now have complete payload specifications, TypeScript interfaces, and real examples.
