# MyAgent WebSocket Protocol (Stable)

Status: Stable
Version: v1.0.1
Last Updated: 2025-10-18

The stable, production-ready specification for MyAgent’s WebSocket protocol. It defines event structure, payloads, reliability, error handling, and reconnection semantics used by both clients and server.

## Quick Start

- Base model: see `EVENT_PROTOCOL.md` for the standard `EventProtocol` shape.
- Send/receive: see `EVENT_PAYLOADS.md` for concrete payloads, examples, and flows.
- Validate: see `PAYLOAD_VALIDATION_GUIDE.md` for rules and sample validators.
- Types: use `EVENT_TYPES.ts` for frontend type safety and autocompletion.

Example event:

```json
{
  "session_id": "sess_xyz789",
  "event": "plan.completed",
  "timestamp": "2024-10-18T14:31:00Z",
  "content": {"tasks": [{"id": "task_1", "title": "Generate content"}]},
  "metadata": {
    "task_count": 1,
    "plan_summary": "Generate and format slides",
    "total_estimated_tokens": 1800,
    "llm_calls": 2,
    "planning_time_ms": 5400
  }
}
```

## Document Map

- Protocol: `EVENT_PROTOCOL.md` (start here)
- Payloads (reference): `EVENT_PAYLOADS.md`
- Payloads (detailed spec): `EVENT_PAYLOADS_DETAILED.md`
- Error handling: `ERROR_HANDLING.md`
- Reconnection: `RECONNECTION.md`
- Validation: `PAYLOAD_VALIDATION_GUIDE.md`
- TypeScript types: `EVENT_TYPES.ts`
- Cross-reference coverage: `EVENT_CROSS_REFERENCE.md`
- Field conventions: `FIELD_CONVENTIONS.md`
- Versioning policy: `VERSIONING.md`
- Changelog: `CHANGELOG.md`

## Compatibility & Versioning

- This folder tracks the stable v1 protocol. Changes follow Semantic Versioning.
- Non-breaking additions (e.g., optional metadata fields) are minor or patch bumps.
- Breaking changes are avoided; if required, they trigger a major version and are documented in `CHANGELOG.md`.

## Implementation Notes

- Separate user-visible `content` from structured `metadata`.
- Use milliseconds for fields ending with `_ms`, seconds for `_seconds`.
- Use `user.ack` with `seq` for reliable delivery and reconnection.
- Prefer types in `EVENT_TYPES.ts` for frontend code and refer to `PAYLOAD_VALIDATION_GUIDE.md` on the backend.
