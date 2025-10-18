# Field Conventions

Status: Stable
Version: v1.0.1
Last Updated: 2025-10-18

Consistent field naming, units, and semantics across all WebSocket events.

## Top-Level Fields

- `event` (string): Namespaced event type, e.g., `user.message`, `plan.completed`.
- `timestamp` (string): ISO8601 datetime, UTC preferred.
- `session_id` (string, optional): Unique session identifier. Opaque string, max 128 chars.
- `connection_id` (string, optional): Current WebSocket connection identifier.
- `step_id` (string, optional): Correlates request/response pairs (e.g., `agent.user_confirm` ↔ `user.response`).
- `content` (string | object | null): User-visible primary payload. Strings are preferred when possible.
- `metadata` (object, optional): Structured, machine-readable supplemental fields.
- `show_content` (string, optional): Human-readable display text for UI.
- `seq` (number, optional): Monotonic sequence number for reliable delivery (server → client).

Rules:
- Keep `content` human-oriented; put computed stats and options in `metadata`.
- Avoid duplicating the same field in both `content` and `metadata`.

## Units and Suffixes

- Milliseconds: use `_ms` (e.g., `planning_time_ms`, `execution_time_ms`, `restoration_time_ms`).
- Seconds: use `_seconds` (e.g., `timeout_seconds`, `duration_seconds`, `server_uptime_seconds`).
- Counts: use singular nouns with context (e.g., `llm_calls`, `task_count`).

All time fields are non-negative integers.

### Example: Planning Duration

- `planning_time_ms` (number): End-to-end planning phase duration in milliseconds.
  - Includes all LLM calls and internal orchestration for the plan stage.
  - Present on `plan.completed` in `metadata`.
  - Range: `>= 0`.

## IDs and Formats

- IDs are opaque strings (letters, digits, `_` and `-` allowed); avoid assuming UUIDs.
- Keep IDs stable for the life of the object (e.g., a task) within a session.
- `timestamp` must be ISO8601. Prefer `Z` or explicit offset.

## Event Naming

- Namespaced with a single dot: `<namespace>.<name>`.
- Namespaces: `user`, `plan`, `solver`, `agent`, `system`, `error`, `aggregate`, `pipeline`.
- Names are lower_snake_case.

Examples:
- `user.message`, `plan.start`, `solver.completed`, `agent.session_end`, `system.notice`, `error.recovery_failed`.

## Required vs Optional Fields

- Required fields are documented per event in `EVENT_PAYLOADS_DETAILED.md`.
- Optional fields must not be assumed present; clients should handle absence gracefully.
- When present, optional fields must conform to the documented type and units.

## Validation Summary

- Validate required top-level fields: `event`, `timestamp` and event-specific required fields.
- Type-check `content` and `metadata` based on event type.
- Ensure `_ms` and `_seconds` suffix fields are integers with correct units.
- See `PAYLOAD_VALIDATION_GUIDE.md` for end-to-end examples and validators.

## Example Snippet

```json
{
  "event": "plan.completed",
  "timestamp": "2024-10-18T14:31:00Z",
  "session_id": "sess_xyz789",
  "content": {
    "tasks": [{"id": "task_1", "title": "Generate content"}]
  },
  "metadata": {
    "task_count": 1,
    "plan_summary": "Generate and format slides",
    "total_estimated_tokens": 1800,
    "llm_calls": 2,
    "planning_time_ms": 5400
  }
}
```
