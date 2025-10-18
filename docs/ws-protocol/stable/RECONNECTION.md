# Reconnection & State Recovery Strategy

## Overview

When a WebSocket connection is lost, the client must be able to reconnect and resume operations without data loss. MyAgent implements a stateful reconnection protocol with event replay from buffers.

## Connection States

```
DISCONNECTED
    ↓
[user.create_session or user.reconnect]
    ↓
CONNECTING
    ↓
[system.connected]
    ↓
CONNECTED
    ↓ [Network issue]
    ↓
CONNECTION_LOST
    ↓
[user.reconnect_with_state]
    ↓
RECONNECTING
    ↓
[Event replay complete]
    ↓
CONNECTED (resumed)
```

## Session Identification

### Session ID

Unique identifier created when client initiates session:

```javascript
// Client initiates
{
  event: "user.create_session",
  content: {
    client_id: "browser_abc123",
    app_version: "1.0.0"
  }
}

// Server responds
{
  event: "agent.session_created",
  session_id: "sess_xyz789",
  content: {
    session_id: "sess_xyz789",
    created_at: "2024-10-18T12:00:00Z"
  },
  metadata: {
    server_version: "1.0.0",
    capabilities: ["planning", "solving", "aggregation"]
  }
}
```

### Persistence

- Client must persist `session_id` locally (localStorage, preferences)
- Session valid for duration (configurable, default 24 hours)
- Allow resuming previous sessions on application restart

## Connection Loss Detection

### Detection Methods

| Method | Reliability | Detection Time |
|--------|------------|-----------------|
| **Heartbeat** | High | 30-60s (configurable) |
| **Socket close event** | Instant | < 1ms |
| **Inactivity timeout** | High | 5-10m |
| **Failed send** | Medium | Operation time |

### Heartbeat Protocol

```
[Connected state]
    ↓ [Every 30s]
    ↓
system.heartbeat (server → client)
    ↓
[Client receives]
    ↓
user.ack (client → server)
    ↓ [No heartbeat for 2 × period (60s)]
    ↓
[Client assumes disconnected]
    ↓
[Initiate reconnection]
```

**Server Configuration**:
```python
HEARTBEAT_INTERVAL_SECONDS = 30
HEARTBEAT_TIMEOUT_SECONDS = 60  # 2x interval
MAX_HEARTBEAT_MISSES = 2
```

**Heartbeat Event**:
```javascript
{
  event: "system.heartbeat",
  session_id: "sess_xyz789",
  content: {
    server_time: "2024-10-18T12:00:30Z"
  },
  metadata: {
    seq: 10,
    server_uptime_seconds: 3600
  }
}
```

## Reconnection Flows

### Flow 1: Quick Reconnect (< 60 seconds offline)

```
[Connection lost]
    ↓
user.reconnect_with_state (last_seq=42)
  session_id: "sess_xyz789"
  content: { last_seq: 42 }
    ↓
[Server checks buffer]
    ↓
[Events 43-50 in buffer? YES]
    ↓
system.notice (buffered events)
  content: {
    events: [
      {event: "agent.thinking", seq: 43},
      {event: "agent.tool_call", seq: 44},
      ...
      {event: "solver.completed", seq: 50}
    ]
  }
    ↓
user.ack (last_seq=50)
    ↓
[Resume from seq=51]
    ↓
[Continue operation]
```

**Server-side logic**:
```python
async def handle_reconnect_with_state(session_id: str, last_seq: int):
    """Handle client reconnection with state"""

    session = get_session(session_id)
    if not session:
        # Session expired
        return create_event(
            "error.recovery_failed",
            content="Session expired, please create new session"
        )

    # Get buffered events since last_seq
    buffered_events = session.get_events_since(last_seq)

    if not buffered_events:
        # Buffer cleared or gap too large
        return create_event(
            "system.notice",
            content="No buffered events available, continuing from current state"
        )

    # Send all buffered events
    for event in buffered_events:
        await send_event(session_id, event)

    # Update session state
    session.last_ack_seq = buffered_events[-1].seq
    return create_event(
        "system.notice",
        content=f"Replayed {len(buffered_events)} buffered events"
    )
```

### Flow 2: Extended Disconnect (60s - 24h offline)

```
[Connection lost > 60s]
    ↓
user.reconnect_with_state (last_seq=42)
    ↓
[Server buffer truncated, events lost]
    ↓
user.request_state (session_id)
    ↓
agent.state_exported
  metadata: {
    session_state: {...},
    current_operation: "planning",
    timestamp: "2024-10-18T12:05:00Z"
  }
    ↓
[Client receives full state]
    ↓
[Resume from exported state]
    ↓
[Continue operation]
```

**When to use**:
- Buffer overflow or truncation detected
- `last_seq` predates all buffered events
- Manual state recovery requested

**State structure**:
```javascript
{
  event: "agent.state_exported",
  metadata: {
    session_id: "sess_xyz789",
    session_state: {
      stage: "planning",
      plan_context: {
        question: "Generate presentation",
        tasks: [...],
        status: "in_progress"
      },
      current_task: null,
      completed_tasks: [],
      agent_state: {...}
    },
    exported_at: "2024-10-18T12:05:00Z",
    valid_until: "2024-10-19T12:05:00Z"
  }
}
```

### Flow 3: Session Expired (> 24h offline)

```
[Connection lost > 24h]
    ↓
user.reconnect_with_state (last_seq=42, session_id=old)
    ↓
[Server checks: session expired]
    ↓
error.recovery_failed
  content: "Session expired"
  metadata: {
    recovery_strategy: "create_new_session"
  }
    ↓
user.create_session
    ↓
agent.session_created (new session_id)
    ↓
[Start new session]
```

## Event Buffering

### Buffer Design

```python
class EventBuffer:
    """Circular buffer for reliable event delivery"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = collections.deque(maxlen=max_size)
        self.seq_counter = 0
        self.acks = {}  # {client_id: last_ack_seq}

    def add_event(self, event: dict) -> int:
        """Add event to buffer, return seq number"""
        self.seq_counter += 1
        event['seq'] = self.seq_counter
        self.buffer.append(event)
        return self.seq_counter

    def get_events_since(self, last_seq: int) -> list[dict]:
        """Get all events since last_seq"""
        return [e for e in self.buffer if e['seq'] > last_seq]

    def acknowledge(self, client_id: str, seq: int) -> None:
        """Record ACK from client"""
        self.acks[client_id] = max(self.acks.get(client_id, 0), seq)

    def cleanup_acked(self) -> None:
        """Remove events acknowledged by all clients"""
        if not self.acks:
            return

        min_ack = min(self.acks.values())
        # Keep events newer than min_ack
        # Oldest events auto-purge when buffer full
```

### Buffer Retention

| Scenario | Buffer Size | Retention |
|----------|------------|-----------|
| Active client | 100-500 events | Last ACK to current |
| Inactive (1h) | 50-200 events | Last hour |
| Timeout (> 24h) | None | Expired |

## Sequence Numbers & ACKs

### Seq Assignment

Each event gets a sequence number for ordering and duplicate detection:

```
seq=1: plan.start
seq=2: agent.thinking
seq=3: agent.tool_call
...
seq=42: solver.completed
[connection lost]
[reconnect, last_seq=42]
seq=43: [replay resumes from here]
```

### ACK Protocol

Client acknowledges receipt of events:

```javascript
// Client sends ACK after receiving events
{
  event: "user.ack",
  session_id: "sess_xyz789",
  metadata: {
    last_seq: 50,
    received_count: 8,
    gap_detected: false
  }
}
```

**Duplicate Detection**:
```python
def is_duplicate(event: dict, last_seen: dict[str, int]) -> bool:
    """Check if event is duplicate based on seq + session"""
    key = (event['session_id'], event['seq'])
    if key in last_seen:
        return True
    last_seen[key] = time.time()
    return False
```

## State Recovery Strategies

### Strategy 1: Event Replay Only

Use when: Connection loss < 60 seconds, full event history in buffer

```
Buffered events replay:
  → Client state rebuilds automatically
  → Resume from last operation
```

**Pros**: Simple, automatic
**Cons**: Only works for short disconnects

### Strategy 2: Partial State Export

Use when: Connection loss 60s-24h, buffer partially available

```
Combine:
  1. Buffered events (new events since last_seq)
  2. State snapshot (plan_context, current_task)

Result:
  → Client rebuilds from snapshot
  → Applies new events on top
  → Resume operation
```

**Pros**: Recovers most scenarios
**Cons**: Requires state serialization

### Strategy 3: Full State Restore

Use when: Connection loss > 24h or buffer completely lost

```
User must:
  1. Create new session, OR
  2. Re-upload original prompt/data
  3. System regenerates context

Result:
  → Clean slate with preserved results
  → No automatic resume
```

**Pros**: Always works
**Cons**: Manual intervention

## Implementation Checklist

### Server-side

- [ ] Implement EventBuffer with seq numbering
- [ ] Track session creation time (TTL: 24h)
- [ ] Implement heartbeat timer (30s interval)
- [ ] Handle `user.reconnect_with_state` event
- [ ] Implement event replay from buffer
- [ ] Handle buffer overflow gracefully
- [ ] Implement `user.request_state` for full state export
- [ ] Clear buffers on explicit session end
- [ ] Log reconnection attempts for debugging

### Client-side

- [ ] Store session_id persistently
- [ ] Detect connection loss (socket close, timeout)
- [ ] Implement reconnection backoff (1s, 2s, 4s, 8s, max 60s)
- [ ] Send `user.reconnect_with_state` with last_seq
- [ ] Handle buffered event replay
- [ ] Handle `error.recovery_failed` (session expired)
- [ ] Deduplicate events by seq number
- [ ] Send ACKs after event reception
- [ ] Display reconnection status to user

## Testing

### Test Scenarios

1. **Happy path**: Brief disconnect → quick reconnect
   - Verify event replay
   - Verify seq continuity
   - Verify no duplicates

2. **Buffer overflow**: Long disconnect → state export
   - Verify state restoration
   - Verify operation resume

3. **Session expiration**: Very long disconnect → new session
   - Verify error response
   - Verify graceful new session creation

4. **Partial message loss**: Connection drops mid-event
   - Verify no data corruption
   - Verify safe resume point

## Configuration

```python
# Reconnection settings
RECONNECTION_CONFIG = {
    "heartbeat_interval_seconds": 30,
    "heartbeat_timeout_seconds": 60,
    "max_heartbeat_misses": 2,
    "session_ttl_hours": 24,
    "buffer_size": 1000,
    "buffer_retention_hours": 1,
    "reconnect_backoff": [1, 2, 4, 8, 16, 30, 60],  # seconds
    "max_reconnect_attempts": 5,
}
```

## Monitoring

### Metrics to Track

- Reconnection success rate
- Average time to reconnect
- Events lost per reconnection
- Buffer overflow incidents
- Session expiration rate
- Duplicate event detection count

### Health Checks

```python
async def check_buffer_health(session: AgentSession) -> dict:
    """Monitor buffer health"""
    return {
        "buffer_size": len(session.buffer),
        "buffer_usage_percent": len(session.buffer) / MAX_BUFFER_SIZE * 100,
        "oldest_event_seq": session.buffer[0]['seq'] if session.buffer else None,
        "newest_event_seq": session.buffer[-1]['seq'] if session.buffer else None,
        "unacked_events": len(session.buffer) - session.last_ack_seq,
        "session_age_seconds": (now - session.created_at).total_seconds(),
    }
```

## See Also

- `EVENT_PROTOCOL.md` - Core protocol specification
- `ERROR_HANDLING.md` - Error recovery strategies
- `EVENT_PAYLOADS.md` - Complete payload reference
