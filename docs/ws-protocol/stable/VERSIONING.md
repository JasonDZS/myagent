# Versioning Policy

Status: Stable
Version: v1.0.1
Last Updated: 2025-10-18

This document describes how the WebSocket protocol evolves over time and how changes are communicated.

## Semantic Versioning

The stable protocol follows SemVer: `MAJOR.MINOR.PATCH`.

- MAJOR: Breaking changes to event types or field semantics.
- MINOR: Backward-compatible additions (e.g., new optional metadata fields or new event types).
- PATCH: Backward-compatible clarifications and documentation fixes.

## Compatibility Guarantees

- Existing event types and field names are not changed in backward-incompatible ways within a major version.
- New fields are added as optional and won’t break existing consumers.
- Units and suffixes remain consistent (`_ms` and `_seconds`).

## Deprecation Policy

- Deprecated fields or events are marked in documentation and changelog.
- A deprecation window is communicated before removal in a new MAJOR version.

## Version Identification

- Documentation version is tracked in this folder via `CHANGELOG.md`.
- Server and client implementations are recommended to pin to a protocol major version.

## Process

1. Propose change via PR with updates to: relevant docs, `EVENT_TYPES.ts`, and `CHANGELOG.md`.
2. Validate with examples and, when possible, tests linked from `PAYLOAD_VALIDATION_GUIDE.md`.
3. Ship as MINOR or PATCH if backward-compatible; otherwise, schedule for the next MAJOR.
