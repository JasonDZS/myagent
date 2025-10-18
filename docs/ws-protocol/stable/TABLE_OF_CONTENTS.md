# WebSocket Protocol Documentation - Table of Contents

## Overview

Complete WebSocket event protocol documentation for MyAgent. This folder contains the stable, production-ready protocol specifications.

**Generated**: October 18, 2024
**Status**: ✅ Phase 1 Complete

---

## 📚 Core Documentation

### 1. [EVENT_PROTOCOL.md](./EVENT_PROTOCOL.md)
**Core protocol specification** - Start here for understanding the foundation.

- ✅ Event structure (EventProtocol model)
- ✅ Namespacing system (user.*, plan.*, solver.*, agent.*, system.*, error.*)
- ✅ Content vs Metadata pattern
- ✅ Sequence numbers and ACK mechanism
- ✅ Request/response pairing (step_id)
- ✅ Event flow architecture (Plan → Solve → Aggregate pipeline)
- ✅ Session management lifecycle
- ✅ All event types summary table

**Read this if**: You want to understand the basic protocol structure

---

### 2. [EVENT_PAYLOADS.md](./EVENT_PAYLOADS.md)
**Complete payload reference** - Reference for all event types with full examples.

- ✅ User Events (11 types): message, solve_tasks, response, cancel, ack, create_session, reconnect, etc.
- ✅ Plan Events (4 types): start, completed, cancelled, coercion_error
- ✅ Solver Events (4 types): start, completed, cancelled, restarted
- ✅ Agent Events (13 types): thinking, tool_call, tool_result, partial_answer, final_answer, user_confirm, error, session_created, etc.
- ✅ System Events (4 types): connected, heartbeat, notice, error
- ✅ Error Events (6 types): validation, timeout, rate_limited, recovery_failed, connection_lost, retry_attempt
- ✅ Aggregate Events (2 types): start, completed
- ✅ Pipeline Events (1 type): completed

**Format**: For each event: purpose, payload structure, metadata fields, examples

**Read this if**: You need the exact structure for sending/receiving events

---

### 3. [ERROR_HANDLING.md](./ERROR_HANDLING.md)
**Error handling strategy** - How to classify, handle, and recover from errors.

- ✅ Error classification (Validation, Transient, Resource, Permanent, Connection)
- ✅ Error event structure and fields
- ✅ 5 error flow diagrams (Validation → Timeout → Rate Limit → Unrecoverable → Connection Loss)
- ✅ Retry strategy with exponential backoff algorithm
- ✅ Retry configuration (max_attempts, backoff_multiplier, etc.)
- ✅ Implementation pattern for execute_with_retry()
- ✅ Error code system and best practices
- ✅ Monitoring and logging strategies

**Read this if**: You need to handle errors gracefully and implement retry logic

---

### 4. [RECONNECTION.md](./RECONNECTION.md)
**Reconnection & state recovery** - How to handle connection loss and resume operations.

- ✅ Connection state machine (DISCONNECTED → CONNECTING → CONNECTED → CONNECTION_LOST → RECONNECTING)
- ✅ Session identification and persistence
- ✅ Connection loss detection (heartbeat, socket close, timeout)
- ✅ Heartbeat protocol (30s interval, 60s timeout)
- ✅ 3 reconnection flows:
  - Quick reconnect (< 60s): Event replay from buffer
  - Extended disconnect (60s-24h): Partial state export + event replay
  - Session expired (> 24h): Create new session
- ✅ Event buffering (circular buffer, seq numbers, ACKs)
- ✅ State recovery strategies
- ✅ Implementation checklist (server & client)
- ✅ Testing scenarios and configuration

**Read this if**: You need to handle disconnections and maintain session state

---

## 🔗 Quick Navigation

### By Task

| Task | Read | Key Sections |
|------|------|--------------|
| Understand the protocol | EVENT_PROTOCOL.md | Overview, Event Namespacing, Core Protocol Structure |
| Send an event | EVENT_PAYLOADS.md | [Relevant event type section] |
| Handle errors | ERROR_HANDLING.md | Error Classification, Error Event Flows, Retry Strategy |
| Reconnect on network loss | RECONNECTION.md | Connection Loss Detection, Reconnection Flows |
| Debug an event | EVENT_PAYLOADS.md | Event payload structure + metadata fields |

### By Role

| Role | Start With | Then Read |
|------|-----------|-----------|
| **Backend Developer** | EVENT_PROTOCOL.md | → ERROR_HANDLING.md → RECONNECTION.md |
| **Frontend Developer** | EVENT_PROTOCOL.md | → EVENT_PAYLOADS.md → RECONNECTION.md |
| **DevOps/Monitoring** | ERROR_HANDLING.md | → RECONNECTION.md |
| **Product Manager** | EVENT_PROTOCOL.md (Overview section) | → EVENT_PAYLOADS.md (summary only) |

### By Event Type

- **User Events**: EVENT_PAYLOADS.md → User Events section
- **Plan/Solver/Agent Events**: EVENT_PAYLOADS.md → respective sections
- **Error Events**: ERROR_HANDLING.md → Error Events section + EVENT_PAYLOADS.md → Error Events section
- **System Events**: EVENT_PAYLOADS.md → System Events section

---

## 📊 Protocol Statistics

| Metric | Count |
|--------|-------|
| Event namespaces | 8 |
| Total event types | 45+ |
| User events | 11 |
| Plan events | 4 |
| Solver events | 4 |
| Agent events | 13 |
| Error events | 6 |
| System events | 4 |
| Aggregate events | 2 |
| Pipeline events | 1 |
| Documentation lines | 2,352 |
| Code examples | 50+ |

---

## ✨ Key Features

### Event Structure
```javascript
{
  session_id: "sess_xyz789",
  connection_id: "conn_123",
  step_id: "plan_confirm_1",
  event: "agent.user_confirm",
  timestamp: "2024-10-18T12:00:00Z",
  content: {...},
  metadata: {...},
  show_content: "Chinese display text",
  seq: 42
}
```

### Reliability Mechanisms
- ✅ Sequence numbering (seq)
- ✅ Acknowledgment (user.ack)
- ✅ Event buffering with replay
- ✅ Heartbeat for keep-alive
- ✅ Exponential backoff retry

### Flow Support
- ✅ Plan → Solve → Aggregate pipeline
- ✅ User confirmations with step_id correlation
- ✅ Error recovery with retry
- ✅ Connection reconnection with state
- ✅ Session management and TTL

---

## 🚀 Implementation Priority

### Phase 1: Documentation (✅ Complete)
- [x] EVENT_PROTOCOL.md - Core specification
- [x] EVENT_PAYLOADS.md - Event payload reference
- [x] ERROR_HANDLING.md - Error handling strategies
- [x] RECONNECTION.md - Connection recovery
- [x] TABLE_OF_CONTENTS.md - This file

**Status**: All 5 core protocol documentation files created

---

## 📝 Document Cross-References

### EVENT_PROTOCOL.md references:
- ERROR_HANDLING.md for error classification
- RECONNECTION.md for session/connection lifecycle
- EVENT_PAYLOADS.md for specific payload structures

### EVENT_PAYLOADS.md references:
- EVENT_PROTOCOL.md for field definitions
- ERROR_HANDLING.md for error event structures
- RECONNECTION.md for reconnection event details

### ERROR_HANDLING.md references:
- EVENT_PROTOCOL.md for base event structure
- EVENT_PAYLOADS.md for error event payloads
- RECONNECTION.md for recovery strategies

### RECONNECTION.md references:
- EVENT_PROTOCOL.md for seq/ack mechanism
- EVENT_PAYLOADS.md for reconnection event payloads
- ERROR_HANDLING.md for error during reconnection

---

## 🔧 Usage Examples

### Example 1: Send a Plan Confirmation
See: EVENT_PAYLOADS.md → agent.user_confirm section

### Example 2: Handle Timeout Error
See: ERROR_HANDLING.md → Transient Error with Auto-Retry flow

### Example 3: Reconnect After Network Loss
See: RECONNECTION.md → Flow 1: Quick Reconnect

### Example 4: Export Session State
See: RECONNECTION.md → Flow 2: Extended Disconnect

---

## 💡 Best Practices Summary

1. **Always separate content from metadata**
   - content: user-visible text
   - metadata: structured machine data

2. **Use step_id for request/response correlation**
   - Set in confirmation request
   - Return in user response

3. **Include error codes for debugging**
   - Standard error codes per service
   - Always include context

4. **Implement exponential backoff for retries**
   - Start: 1000ms
   - Max: 60000ms
   - Multiplier: 2.0
   - Add jitter: ±10%

5. **Handle reconnection gracefully**
   - Persist session_id
   - Send ACKs after receiving events
   - Replay from buffer on reconnect

6. **Monitor and log errors**
   - Track by error_code
   - Log attempt count
   - Monitor recovery success rate

---

## 🎯 What's Included

✅ **Complete specification** of WebSocket event protocol
✅ **50+ code examples** showing real payload structures
✅ **10+ flow diagrams** documenting complex interactions
✅ **5 error handling flows** with recovery strategies
✅ **3 reconnection flows** for different scenarios
✅ **Implementation checklists** for server and client
✅ **Best practices** and configuration guidelines
✅ **Monitoring strategies** for production support

---

## 🔮 Future Phases

**Phase 2**: Add 7 new event types for production robustness
**Phase 3**: Standardize metadata/content usage across codebase
**Phase 4**: Clarify reconnection event differentiation
**Phase 5**: Implement error recovery flow
**Phase 6**: Full payload documentation (nested structures)

See: IMPLEMENTATION_PLAN.md in root directory

---

## ℹ️ Document Metadata

- **Version**: 1.0.0
- **Last Updated**: October 18, 2024
- **Status**: ✅ Stable (Phase 1 Complete)
- **Maintainer**: Claude Code
- **License**: Project License

---

## 📞 Questions?

Refer to the **Quick Navigation** section above to find the right document for your question.

For implementation details, see individual section "Best Practices" subsections.

For examples, search for code blocks with `javascript` or `python` markers.
