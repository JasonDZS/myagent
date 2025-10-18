# Changelog

All notable changes to the stable WebSocket protocol documentation will be listed here.

## v1.0.1 (2025-10-18)

- Align event name to server implementation: use `agent.session_end` (was inconsistently referenced as `agent.session_ended` in some docs).
- Add missing TypeScript interfaces in `EVENT_TYPES.ts`:
  - `PlanCancelled`, `PlanCoercionError`, `SolverCancelled`, `SolverRestarted`
  - `AgentLLMMessage`, `AgentStateExported`, `AgentStateRestored`, `AgentSessionEnd`
  - `SystemNotice` and corresponding constants
- Add `FIELD_CONVENTIONS.md` and `VERSIONING.md` for production-readiness.
- Add `README.md` as the landing page for the stable protocol.
- Add `planning_time_ms` to `plan.completed` in `EVENT_PAYLOADS.md` to match the detailed spec.
- Move statistics/metrics into `metadata` for the following events and update UI/types/docs accordingly:
  - `plan.completed`: `metadata.statistics`, `metadata.metrics`
  - `solver.completed`: `metadata.statistics`
  - `pipeline.completed`: `metadata.statistics`, `metadata.metrics`

## v1.0.0 (2024-10-18)

- Initial stable protocol spec:
  - `EVENT_PROTOCOL.md`, `EVENT_PAYLOADS.md`, `EVENT_PAYLOADS_DETAILED.md`
  - `ERROR_HANDLING.md`, `RECONNECTION.md`, `PAYLOAD_VALIDATION_GUIDE.md`
  - `EVENT_TYPES.ts`, `EVENT_CROSS_REFERENCE.md`, `TABLE_OF_CONTENTS.md`
