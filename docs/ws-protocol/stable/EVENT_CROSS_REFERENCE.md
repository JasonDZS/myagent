# WebSocket Event System - Cross-Reference Guide

**Status**: Complete mapping of all 45+ event types across code and documentation

This document provides a comprehensive mapping of all WebSocket events across the codebase and documentation files.

---

## Quick Navigation

- [File Reference Map](#file-reference-map)
- [Event Coverage Matrix](#event-coverage-matrix)
- [Event-by-Event Reference](#event-by-event-reference)
- [Documentation Gaps & Status](#documentation-gaps--status)

---

## File Reference Map

| Aspect | Code Location | Primary Docs | Payload Specs | Types | Validation |
|--------|---------------|--------------|---------------|-------|-----------|
| **Definitions** | `myagent/ws/events.py` | `EVENT_PROTOCOL.md` | `EVENT_PAYLOADS_DETAILED.md` | `EVENT_TYPES.ts` | `PAYLOAD_VALIDATION_GUIDE.md` |
| **Usage** | `myagent/ws/events.py` (docstrings) | `EVENT_PAYLOADS.md` | `EVENT_PAYLOADS_DETAILED.md` | `EVENT_TYPES.ts` | - |
| **Recovery** | `myagent/ws/retry_config.py` | `ERROR_RECOVERY_GUIDE.md` | `ERROR_RECOVERY_STRATEGIES.md` | - | - |
| **Display** | `myagent/ws/events.py` (`_derive_show_content`) | - | - | - | - |

---

## Event Coverage Matrix

### User Events (8 types) - Client → Server

| Event | Python Constant | In events.py | In EVENT_PAYLOADS_DETAILED | In EVENT_TYPES.ts | In PAYLOAD_VALIDATION | Documentation Status |
|-------|-----------------|--------------|----------------------------|-------------------|----------------------|----------------------|
| user.create_session | ✅ Line 95 | ✅ Docstring | ✅ Lines 55-91 | ✅ Lines 26-37 | ✅ | 🟢 Complete |
| user.message | ✅ Line 86 | ✅ Docstring | ✅ Lines 97-130 | ✅ Lines 39-48 | ✅ | 🟢 Complete |
| user.response | ✅ Line 89 | ✅ Docstring | ✅ Lines 136-175 | ✅ Lines 50-63 | ✅ | 🟢 Complete |
| user.ack | ✅ Line 100 | ✅ Docstring | ✅ Lines 181-214 | ✅ Lines 65-75 | ✅ | 🟢 Complete |
| user.cancel | ✅ Line 90 | ✅ Docstring | ✅ Lines 219-245 | ✅ Lines 77-83 | ✅ | 🟢 Complete |
| user.reconnect | ✅ Line 96 | ✅ Docstring | ✅ Lines 249-274 | ✅ Lines 85-91 | ✅ | 🟢 Complete |
| user.reconnect_with_state | ✅ Line 97 | ✅ Docstring | ✅ Lines 279-299 | ✅ Lines 93-104 | ✅ | 🟢 Complete |
| user.request_state | ✅ Line 98 | ✅ Docstring | ✅ Lines 303-319 | ✅ Lines 106-113 | ✅ | 🟢 Complete |

**Coverage**: 100%

---

### Plan Events (6 types) - Server → Client

| Event | Python Constant | In events.py | In EVENT_PAYLOADS_DETAILED | In EVENT_TYPES.ts | In PAYLOAD_VALIDATION | Documentation Status |
|-------|-----------------|--------------|----------------------------|-------------------|----------------------|----------------------|
| plan.start | ✅ Line 114 | ✅ Docstring | ✅ Lines 327-368 | ✅ Lines 129-142 | ✅ | 🟢 Complete |
| plan.completed | ✅ Line 115 | ✅ Docstring | ✅ Lines 372-429 | ✅ Lines 144-163 | ✅ | 🟢 Complete |
| plan.cancelled | ✅ Line 116 | ✅ Docstring | ✅ Lines 1323-1365 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |
| plan.coercion_error | ✅ Line 117 | ✅ Docstring | ✅ Lines 1370-1408 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |
| plan.step_completed | ✅ Line 118 | ✅ Docstring | ✅ Lines 434-456 | ✅ Lines 165-178 | ✅ | 🟢 Complete |
| plan.validation_error | ✅ Line 119 | ✅ Docstring | ✅ Lines 460-482 | ✅ Lines 180-193 | ✅ | 🟢 Complete |

**Coverage**: 100% (documentation), 67% (TS types)

---

### Solver Events (7 types) - Server → Client

| Event | Python Constant | In events.py | In EVENT_PAYLOADS_DETAILED | In EVENT_TYPES.ts | In PAYLOAD_VALIDATION | Documentation Status |
|-------|-----------------|--------------|----------------------------|-------------------|----------------------|----------------------|
| solver.start | ✅ Line 135 | ✅ Docstring | ✅ Lines 490-507 | ✅ Lines 205-214 | ✅ | 🟢 Complete |
| solver.progress | ✅ Line 139 | ✅ Docstring | ✅ Lines 512-558 | ✅ Lines 216-232 | ✅ | 🟢 Complete |
| solver.completed | ✅ Line 136 | ✅ Docstring | ✅ Lines 562-589 | ✅ Lines 234-252 | ✅ | 🟢 Complete |
| solver.step_failed | ✅ Line 140 | ✅ Docstring | ✅ Lines 593-616 | ✅ Lines 254-268 | ✅ | 🟢 Complete |
| solver.retry | ✅ Line 141 | ✅ Docstring | ✅ Lines 620-641 | ✅ Lines 270-282 | ✅ | 🟢 Complete |
| solver.cancelled | ✅ Line 137 | ✅ Docstring | ✅ Lines 1415-1452 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |
| solver.restarted | ✅ Line 138 | ✅ Docstring | ✅ Lines 1457-1495 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |

**Coverage**: 100% (documentation), 71% (TS types)

---

### Agent Events (11 types) - Server → Client

| Event | Python Constant | In events.py | In EVENT_PAYLOADS_DETAILED | In EVENT_TYPES.ts | In PAYLOAD_VALIDATION | Documentation Status |
|-------|-----------------|--------------|----------------------------|-------------------|----------------------|----------------------|
| agent.thinking | ✅ Line 171 | ✅ Docstring | ✅ Lines 649-669 | ✅ Lines 295-306 | ✅ | 🟢 Complete |
| agent.tool_call | ✅ Line 172 | ✅ Docstring | ✅ Lines 673-718 | ✅ Lines 308-322 | ✅ | 🟢 Complete |
| agent.tool_result | ✅ Line 173 | ✅ Docstring | ✅ Lines 722-744 | ✅ Lines 324-337 | ✅ | 🟢 Complete |
| agent.partial_answer | ✅ Line 174 | ✅ Docstring | ✅ Lines 748-766 | ✅ Lines 339-348 | ✅ | 🟢 Complete |
| agent.final_answer | ✅ Line 175 | ✅ Docstring | ✅ Lines 770-792 | ✅ Lines 350-363 | ✅ | 🟢 Complete |
| agent.user_confirm | ✅ Line 176 | ✅ Docstring | ✅ Lines 796-822 | ✅ Lines 365-382 | ✅ | 🟢 Complete |
| agent.session_created | ✅ Line 180 | ✅ Docstring | ✅ (in EVENT_PAYLOADS.md) | ✅ Lines 384-392 | ✅ | 🟡 Missing detailed spec |
| agent.session_ended | ✅ Line 181 | ✅ Docstring | ✅ Lines 1156-1189 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |
| agent.llm_message | ✅ Line 182 | ✅ Docstring | ✅ Lines 1193-1229 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |
| agent.state_exported | ✅ Line 183 | ✅ Docstring | ✅ Lines 1233-1278 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |
| agent.state_restored | ✅ Line 184 | ✅ Docstring | ✅ Lines 1282-1317 | ⚠️ Not in ts | ✅ | 🟡 TS Type Missing |

**Coverage**: 100% (documentation), 64% (TS types)

---

### System Events (3 types) - Bidirectional

| Event | Python Constant | In events.py | In EVENT_PAYLOADS_DETAILED | In EVENT_TYPES.ts | In PAYLOAD_VALIDATION | Documentation Status |
|-------|-----------------|--------------|----------------------------|-------------------|----------------------|----------------------|
| system.connected | ✅ Line 195 | ✅ Docstring | ✅ Lines 830-850 | ✅ Lines 418-429 | ✅ | 🟢 Complete |
| system.heartbeat | ✅ Line 197 | ✅ Docstring | ✅ Lines 854-873 | ✅ Lines 431-440 | ✅ | 🟢 Complete |
| system.error | ✅ Line 198 | ✅ Docstring | ✅ Lines 877-894 | ✅ Lines 442-449 | ✅ | 🟢 Complete |

**Coverage**: 100%

---

### Error Events (7 types) - Server → Client

| Event | Python Constant | In events.py | In EVENT_PAYLOADS_DETAILED | In EVENT_TYPES.ts | In PAYLOAD_VALIDATION | Error Recovery Guide |
|-------|-----------------|--------------|----------------------------|-------------------|----------------------|----------------------|
| error.validation | ✅ Line 214 | ✅ Docstring | ✅ Lines 902-920 | ✅ Lines 460-471 | ✅ | ✅ Detailed |
| error.timeout | ✅ Line 215 | ✅ Docstring | ✅ Lines 924-946 | ✅ Lines 473-488 | ✅ | ✅ Detailed |
| error.execution | ✅ Line 213 | ✅ Docstring | ✅ Lines 950-968 | ✅ Lines 490-501 | ✅ | ✅ Detailed |
| error.retry | ✅ (line 216 in code: `error.retry_attempt`) | ✅ Docstring | ✅ Lines 972-990 | ✅ Lines 503-514 | ✅ | ✅ Detailed |
| error.recovery_started | ✅ Line 216 | ✅ Docstring | ✅ Lines 994-1010 | ✅ Lines 516-525 | ✅ | ✅ Detailed |
| error.recovery_success | ✅ Line 217 | ✅ Docstring | ✅ Lines 1014-1030 | ✅ Lines 527-536 | ✅ | ✅ Detailed |
| error.recovery_failed | ✅ Line 218 | ✅ Docstring | ✅ Lines 1034-1052 | ✅ Lines 538-549 | ✅ | ✅ Detailed |

**Coverage**: 100%

---

## Event-by-Event Reference

### Quick Lookup by Event Name

#### user.* events
- **user.create_session** - Initialize session
  - Code: `events.py:95` | Docs: `EVENT_PAYLOADS_DETAILED.md:55` | Types: `EVENT_TYPES.ts:26`
- **user.message** - Send query
  - Code: `events.py:86` | Docs: `EVENT_PAYLOADS_DETAILED.md:97` | Types: `EVENT_TYPES.ts:39`
- **user.response** - Confirm/reject
  - Code: `events.py:89` | Docs: `EVENT_PAYLOADS_DETAILED.md:136` | Types: `EVENT_TYPES.ts:50`
- **user.ack** - Acknowledge receipt
  - Code: `events.py:100` | Docs: `EVENT_PAYLOADS_DETAILED.md:181` | Types: `EVENT_TYPES.ts:65`
- **user.cancel** - Cancel operation
  - Code: `events.py:90` | Docs: `EVENT_PAYLOADS_DETAILED.md:219` | Types: `EVENT_TYPES.ts:77`
- **user.reconnect** - Resume session
  - Code: `events.py:96` | Docs: `EVENT_PAYLOADS_DETAILED.md:249` | Types: `EVENT_TYPES.ts:85`
- **user.reconnect_with_state** - Recover with state
  - Code: `events.py:97` | Docs: `EVENT_PAYLOADS_DETAILED.md:279` | Types: `EVENT_TYPES.ts:93`
- **user.request_state** - Export state
  - Code: `events.py:98` | Docs: `EVENT_PAYLOADS_DETAILED.md:303` | Types: `EVENT_TYPES.ts:106`

#### plan.* events
- **plan.start** - Planning begins
  - Code: `events.py:114` | Docs: `EVENT_PAYLOADS_DETAILED.md:327` | Types: `EVENT_TYPES.ts:129`
- **plan.completed** - Plan ready
  - Code: `events.py:115` | Docs: `EVENT_PAYLOADS_DETAILED.md:372` | Types: `EVENT_TYPES.ts:144` | Recovery: `ERROR_RECOVERY_GUIDE.md`
- **plan.cancelled** - Planning cancelled
  - Code: `events.py:116` | Docs: `EVENT_PAYLOADS_DETAILED.md:1323` | Types: ⚠️ Missing
- **plan.coercion_error** - Parse error
  - Code: `events.py:117` | Docs: `EVENT_PAYLOADS_DETAILED.md:1370` | Types: ⚠️ Missing
- **plan.step_completed** - Step done
  - Code: `events.py:118` | Docs: `EVENT_PAYLOADS_DETAILED.md:434` | Types: `EVENT_TYPES.ts:165`
- **plan.validation_error** - Validation failed
  - Code: `events.py:119` | Docs: `EVENT_PAYLOADS_DETAILED.md:460` | Types: `EVENT_TYPES.ts:180`

#### solver.* events
- **solver.start** - Solving begins
  - Code: `events.py:135` | Docs: `EVENT_PAYLOADS_DETAILED.md:490` | Types: `EVENT_TYPES.ts:205`
- **solver.progress** - Progress update
  - Code: `events.py:139` | Docs: `EVENT_PAYLOADS_DETAILED.md:512` | Types: `EVENT_TYPES.ts:216`
- **solver.completed** - Task done
  - Code: `events.py:136` | Docs: `EVENT_PAYLOADS_DETAILED.md:562` | Types: `EVENT_TYPES.ts:234`
- **solver.step_failed** - Step error
  - Code: `events.py:140` | Docs: `EVENT_PAYLOADS_DETAILED.md:593` | Types: `EVENT_TYPES.ts:254`
- **solver.retry** - Retry attempt
  - Code: `events.py:141` | Docs: `EVENT_PAYLOADS_DETAILED.md:620` | Types: `EVENT_TYPES.ts:270`
- **solver.cancelled** - Task cancelled
  - Code: `events.py:137` | Docs: `EVENT_PAYLOADS_DETAILED.md:1415` | Types: ⚠️ Missing
- **solver.restarted** - Task restarted
  - Code: `events.py:138` | Docs: `EVENT_PAYLOADS_DETAILED.md:1457` | Types: ⚠️ Missing

#### agent.* events
- **agent.thinking** - Agent reasoning
  - Code: `events.py:171` | Docs: `EVENT_PAYLOADS_DETAILED.md:649` | Types: `EVENT_TYPES.ts:295`
- **agent.tool_call** - Tool invocation
  - Code: `events.py:172` | Docs: `EVENT_PAYLOADS_DETAILED.md:673` | Types: `EVENT_TYPES.ts:308`
- **agent.tool_result** - Tool result
  - Code: `events.py:173` | Docs: `EVENT_PAYLOADS_DETAILED.md:722` | Types: `EVENT_TYPES.ts:324`
- **agent.partial_answer** - Streaming response
  - Code: `events.py:174` | Docs: `EVENT_PAYLOADS_DETAILED.md:748` | Types: `EVENT_TYPES.ts:339`
- **agent.final_answer** - Complete answer
  - Code: `events.py:175` | Docs: `EVENT_PAYLOADS_DETAILED.md:770` | Types: `EVENT_TYPES.ts:350`
- **agent.user_confirm** - Confirmation request
  - Code: `events.py:176` | Docs: `EVENT_PAYLOADS_DETAILED.md:796` | Types: `EVENT_TYPES.ts:365`
- **agent.session_created** - Session started
  - Code: `events.py:180` | Docs: `EVENT_PAYLOADS.md` | Types: `EVENT_TYPES.ts:384`
- **agent.session_ended** - Session closed
  - Code: `events.py:181` | Docs: `EVENT_PAYLOADS_DETAILED.md:1156` | Types: ⚠️ Missing
- **agent.llm_message** - Raw LLM output
  - Code: `events.py:182` | Docs: `EVENT_PAYLOADS_DETAILED.md:1193` | Types: ⚠️ Missing
- **agent.state_exported** - State exported
  - Code: `events.py:183` | Docs: `EVENT_PAYLOADS_DETAILED.md:1233` | Types: ⚠️ Missing
- **agent.state_restored** - State restored
  - Code: `events.py:184` | Docs: `EVENT_PAYLOADS_DETAILED.md:1282` | Types: ⚠️ Missing

#### system.* events
- **system.connected** - Connection established
  - Code: `events.py:195` | Docs: `EVENT_PAYLOADS_DETAILED.md:830` | Types: `EVENT_TYPES.ts:418`
- **system.heartbeat** - Keep-alive signal
  - Code: `events.py:197` | Docs: `EVENT_PAYLOADS_DETAILED.md:854` | Types: `EVENT_TYPES.ts:431`
- **system.error** - System error
  - Code: `events.py:198` | Docs: `EVENT_PAYLOADS_DETAILED.md:877` | Types: `EVENT_TYPES.ts:442`

#### error.* events
- **error.validation** - Validation failed
  - Code: `events.py:214` | Docs: `EVENT_PAYLOADS_DETAILED.md:902` | Types: `EVENT_TYPES.ts:460` | Recovery: `ERROR_RECOVERY_GUIDE.md:State Machine 1`
- **error.timeout** - Timeout occurred
  - Code: `events.py:215` | Docs: `EVENT_PAYLOADS_DETAILED.md:924` | Types: `EVENT_TYPES.ts:473` | Recovery: `ERROR_RECOVERY_GUIDE.md:State Machine 2`
- **error.execution** - Execution failed
  - Code: `events.py:213` | Docs: `EVENT_PAYLOADS_DETAILED.md:950` | Types: `EVENT_TYPES.ts:490` | Recovery: `ERROR_RECOVERY_GUIDE.md:State Machine 3`
- **error.retry** - Retry attempt
  - Code: `events.py` (see line 216) | Docs: `EVENT_PAYLOADS_DETAILED.md:972` | Types: `EVENT_TYPES.ts:503` | Recovery: `ERROR_RECOVERY_GUIDE.md`
- **error.recovery_started** - Recovery begun
  - Code: `events.py:216` | Docs: `EVENT_PAYLOADS_DETAILED.md:994` | Types: `EVENT_TYPES.ts:516` | Recovery: `ERROR_RECOVERY_GUIDE.md`
- **error.recovery_success** - Recovery succeeded
  - Code: `events.py:217` | Docs: `EVENT_PAYLOADS_DETAILED.md:1014` | Types: `EVENT_TYPES.ts:527` | Recovery: `ERROR_RECOVERY_GUIDE.md`
- **error.recovery_failed** - Recovery failed
  - Code: `events.py:218` | Docs: `EVENT_PAYLOADS_DETAILED.md:1034` | Types: `EVENT_TYPES.ts:538` | Recovery: `ERROR_RECOVERY_GUIDE.md`

---

## Documentation Gaps & Status

### Gaps Identified

#### 1. Missing TypeScript Type Definitions (4 types)
These events have Python definitions and payload documentation but lack TypeScript interfaces in EVENT_TYPES.ts:

| Event | Location in Docs | Fix Required |
|-------|------------------|--------------|
| plan.cancelled | EVENT_PAYLOADS_DETAILED.md:1323 | Add `PlanCancelled` interface to EVENT_TYPES.ts |
| plan.coercion_error | EVENT_PAYLOADS_DETAILED.md:1370 | Add `PlanCoercionError` interface to EVENT_TYPES.ts |
| solver.cancelled | EVENT_PAYLOADS_DETAILED.md:1415 | Add `SolverCancelled` interface to EVENT_TYPES.ts |
| solver.restarted | EVENT_PAYLOADS_DETAILED.md:1457 | Add `SolverRestarted` interface to EVENT_TYPES.ts |
| agent.session_ended | EVENT_PAYLOADS_DETAILED.md:1156 | Add `AgentSessionEnded` interface to EVENT_TYPES.ts |
| agent.llm_message | EVENT_PAYLOADS_DETAILED.md:1193 | Add `AgentLLMMessage` interface to EVENT_TYPES.ts |
| agent.state_exported | EVENT_PAYLOADS_DETAILED.md:1233 | Add `AgentStateExported` interface to EVENT_TYPES.ts |
| agent.state_restored | EVENT_PAYLOADS_DETAILED.md:1282 | Add `AgentStateRestored` interface to EVENT_TYPES.ts |

**Total TypeScript Gap**: 8 events

#### 2. Show Content Display Text
- **Status**: ✅ Complete in `events.py` (_derive_show_content function, lines 228-367)
- **Coverage**: All 31 main events have Chinese display text
- **Missing**: Chinese text for newly added events (plan.cancelled, plan.coercion_error, solver.cancelled, solver.restarted, agent.session_ended, agent.llm_message, agent.state_exported, agent.state_restored)

#### 3. Aggregate & Pipeline Events
- **Status**: ⚠️ Partially documented
- **Location**: Defined in `events.py` (lines 144-154)
- **Documentation**: In EVENT_PAYLOADS.md but not in EVENT_PAYLOADS_DETAILED.md

---

## Summary Statistics

### Overall Coverage

| Category | Total | Documented | TypeScript | Validated | Status |
|----------|-------|-----------|-----------|-----------|--------|
| **User Events** | 8 | 8 (100%) | 8 (100%) | 8 (100%) | ✅ Complete |
| **Plan Events** | 6 | 6 (100%) | 4 (67%) | 6 (100%) | 🟡 TS Gap |
| **Solver Events** | 7 | 7 (100%) | 5 (71%) | 7 (100%) | 🟡 TS Gap |
| **Agent Events** | 11 | 11 (100%) | 8 (73%) | 11 (100%) | 🟡 TS Gap |
| **System Events** | 3 | 3 (100%) | 3 (100%) | 3 (100%) | ✅ Complete |
| **Error Events** | 7 | 7 (100%) | 7 (100%) | 7 (100%) | ✅ Complete |
| **Aggregate Events** | 2 | 1 (50%) | 0 (0%) | 0 (0%) | 🔴 Incomplete |
| **Pipeline Events** | 1 | 1 (100%) | 0 (0%) | 0 (0%) | 🔴 Incomplete |
| **TOTAL** | **45** | **44 (98%)** | **35 (78%)** | **42 (93%)** | 🟡 Active Fixes |

### Key Metrics

- **Total Events Defined**: 45 event types
- **Documentation Coverage**: 98% (44/45 documented)
- **TypeScript Type Coverage**: 78% (35/45)
- **Validation Coverage**: 93% (42/45)
- **Show Content Coverage**: 80% (implemented for 31/39 main events)

---

## How to Use This Document

### For Frontend Developers
1. Check EVENT_TYPES.ts for TypeScript types
2. See **TypeScript Type Coverage** section for known gaps
3. If type is missing, reference EVENT_PAYLOADS_DETAILED.md for structure
4. Report gaps to maintain sync with backend

### For Backend Developers
1. Check events.py for event constants and display text
2. Reference EVENT_PAYLOADS.md for usage patterns
3. Use PAYLOAD_VALIDATION_GUIDE.md for validation logic
4. See ERROR_RECOVERY_GUIDE.md for error handling patterns

### For Documentation Maintainers
1. Use **Event Coverage Matrix** to track completeness
2. Keep EVENT_TYPES.ts in sync with events.py
3. Update _derive_show_content when new events added
4. Add entries to PAYLOAD_VALIDATION_GUIDE.md

---

## Related Documents

- `EVENT_PROTOCOL.md` - Architectural overview and patterns
- `EVENT_PAYLOADS.md` - Quick reference with practical examples
- `EVENT_PAYLOADS_DETAILED.md` - Comprehensive specifications
- `EVENT_TYPES.ts` - TypeScript type definitions
- `PAYLOAD_VALIDATION_GUIDE.md` - Validation framework
- `ERROR_RECOVERY_GUIDE.md` - Error recovery strategies
- `ERROR_RECOVERY_STRATEGIES.md` - Implementation patterns
- `myagent/ws/events.py` - Source of truth

---

**Last Updated**: 2024-10-18
**Coverage Status**: 98% documented, 78% TypeScript, 93% validated
