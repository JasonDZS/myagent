# Error Handling Strategy

## Error Classification

### Error Types

Errors are classified by recovery possibility and scope:

| Category | Recoverable | Examples | Action |
|----------|-------------|----------|--------|
| **Validation** | ✅ Yes | Invalid input, constraint violation | Inform user, retry with corrected input |
| **Transient** | ✅ Yes | Timeout, rate limit, temporary service outage | Auto-retry with backoff |
| **Resource** | ⚠️ Partial | Out of memory, disk full, quota exceeded | Cleanup + retry or escalate |
| **Permanent** | ❌ No | Invalid credentials, unsupported operation, corrupt data | Terminate with error |
| **Connection** | ⚠️ Depends | Socket closed, network unavailable | Reconnect and resume |

## Error Events

### New Error Event Types

```python
class ErrorEvents:
    """Error-specific event types"""

    VALIDATION = "error.validation"        # Input validation failed
    TIMEOUT = "error.timeout"              # Operation timed out
    RATE_LIMITED = "error.rate_limited"    # Rate limit exceeded
    RECOVERY_FAILED = "error.recovery_failed"  # Unrecoverable error
    CONNECTION_LOST = "error.connection_lost"  # Connection dropped
    RETRY_ATTEMPT = "error.retry_attempt"  # Retry in progress
```

### Error Event Payload Structure

```javascript
{
  event: "error.{type}",
  content: "Human-readable error message",
  metadata: {
    // Common fields
    error_code: "ERR_001",
    error_type: "TimeoutError",
    timestamp: "2024-10-18T12:00:00Z",

    // Classification
    recoverable: true,
    recovery_strategy: "retry" | "fallback" | "escalate" | "terminate",

    // Context
    stage: "planning" | "solving" | "aggregation",
    task_id?: "task_123",
    operation: "generate_plan",

    // Retry info
    attempt?: 1,
    max_attempts?: 3,
    retry_after_ms?: 5000,

    // Additional context
    context: {
      // Error-specific context
    }
  },
  show_content: "Chinese display text"
}
```

## Error Handling Flows

### 1. Validation Error Flow

```
user.message
  ↓
[Validation fails]
  ↓
error.validation
  ├─ metadata.recoverable = true
  ├─ metadata.recovery_strategy = "escalate_to_user"
  └─ content = "Invalid input: ..."
  ↓
[User corrects and resubmits]
  ↓
user.message (retry)
  ↓
[Continue normal flow]
```

**Example**:
```javascript
{
  event: "error.validation",
  content: "Task count must be > 0",
  metadata: {
    error_code: "ERR_VAL_001",
    error_type: "ConstraintViolation",
    recoverable: true,
    recovery_strategy: "escalate_to_user",
    constraint: "task_count > 0",
    provided_value: 0
  },
  show_content: "输入验证失败：任务数量必须大于 0"
}
```

### 2. Transient Error with Auto-Retry

```
agent.tool_call
  ↓
[Network timeout]
  ↓
error.timeout (attempt=1)
  ├─ metadata.recoverable = true
  ├─ metadata.retry_after_ms = 2000
  └─ metadata.recovery_strategy = "retry"
  ↓
[Wait 2000ms]
  ↓
error.retry_attempt (attempt=1)
  ↓
agent.tool_call (retry)
  ├─ Success? → Continue
  └─ Fail? → error.timeout (attempt=2)
```

**Example**:
```javascript
{
  event: "error.timeout",
  content: "API request timed out after 30 seconds",
  metadata: {
    error_code: "ERR_TIMEOUT_001",
    error_type: "TimeoutError",
    recoverable: true,
    recovery_strategy: "retry",
    stage: "solving",
    task_id: "task_1",
    operation: "tool_call",
    attempt: 1,
    max_attempts: 3,
    retry_after_ms: 2000,
    timeout_seconds: 30,
    elapsed_seconds: 30.2,
    context: {
      tool_name: "web_search",
      query: "..."
    }
  },
  show_content: "执行超时（尝试 1/3，将在 2 秒后重试）"
}
```

### 3. Rate Limit Error with Backoff

```
agent.tool_call (attempt=1)
  ↓
[Rate limit hit]
  ↓
error.rate_limited (attempt=1)
  ├─ metadata.retry_after_ms = 60000 (from header)
  ├─ metadata.backoff_multiplier = 2.0
  └─ metadata.recovery_strategy = "exponential_backoff"
  ↓
[Wait 60s with exponential backoff]
  ↓
agent.tool_call (attempt=2)
  ├─ Success? → Continue
  └─ Fail? → error.rate_limited (attempt=2, retry_after_ms=120000)
```

**Example**:
```javascript
{
  event: "error.rate_limited",
  content: "Rate limit exceeded: 100 requests per minute",
  metadata: {
    error_code: "ERR_RATE_001",
    error_type: "RateLimitError",
    recoverable: true,
    recovery_strategy: "exponential_backoff",
    attempt: 1,
    max_attempts: 3,
    retry_after_ms: 60000,
    backoff_multiplier: 2.0,
    rate_limit_reset: "2024-10-18T12:01:00Z",
    limit_per_minute: 100,
    requests_made: 105,
    context: {
      service: "openai_api",
      endpoint: "/chat/completions"
    }
  },
  show_content: "请求过于频繁，将在 60 秒后重试"
}
```

### 4. Unrecoverable Error

```
agent.thinking
  ↓
[Invalid API key]
  ↓
error.recovery_failed
  ├─ metadata.recoverable = false
  ├─ metadata.recovery_strategy = "terminate"
  └─ metadata.severity = "critical"
  ↓
agent.error (detailed error)
  ↓
agent.session_end (error status)
```

**Example**:
```javascript
{
  event: "error.recovery_failed",
  content: "Invalid API key: Authentication failed",
  metadata: {
    error_code: "ERR_AUTH_001",
    error_type: "AuthenticationError",
    recoverable: false,
    recovery_strategy: "terminate",
    severity: "critical",
    stage: "planning",
    cause: "invalid_credentials",
    context: {
      service: "openai",
      required_config: ["OPENAI_API_KEY"]
    }
  },
  show_content: "认证失败：API 密钥无效，无法继续"
}
```

### 5. Connection Loss with Reconnection

```
[Normal operation]
  ↓
[WebSocket closes unexpectedly]
  ↓
error.connection_lost
  ├─ metadata.last_event_seq = 42
  ├─ metadata.recovery_strategy = "reconnect_with_state"
  └─ metadata.recoverable = true
  ↓
[Client attempts reconnect]
  ↓
user.reconnect_with_state (last_seq=42)
  ↓
[Server replays buffered events from seq=43]
  ↓
system.notice (buffered events)
  ↓
[Resume where left off]
```

**Example**:
```javascript
{
  event: "error.connection_lost",
  content: "WebSocket connection closed",
  metadata: {
    error_code: "ERR_CONN_001",
    error_type: "ConnectionError",
    recoverable: true,
    recovery_strategy: "reconnect_with_state",
    close_code: 1006,
    close_reason: "abnormal_closure",
    last_event_seq: 42,
    uptime_seconds: 123.45,
    context: {
      last_operation: "agent.thinking",
      state: "planning_stage"
    }
  },
  show_content: "连接已断开，正在重新连接..."
}
```

## Retry Strategy

### Exponential Backoff Algorithm

```python
def calculate_retry_delay(attempt: int, base_delay_ms: int = 1000,
                          max_delay_ms: int = 60000,
                          backoff_multiplier: float = 2.0) -> int:
    """Calculate delay for nth retry with exponential backoff"""
    delay = base_delay_ms * (backoff_multiplier ** (attempt - 1))
    # Add jitter: ±10% to prevent thundering herd
    jitter = delay * 0.1 * random.uniform(-1, 1)
    delay_with_jitter = max(base_delay_ms, min(max_delay_ms, delay + jitter))
    return int(delay_with_jitter)

# Example
attempt 1: 1000ms
attempt 2: 2000ms ± 10%
attempt 3: 4000ms ± 10%
attempt 4: 8000ms ± 10%
attempt 5: 16000ms ± 10%
attempt 6: 32000ms ± 10% (capped at 60000ms)
```

### Retry Configuration

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    backoff_multiplier: float = 2.0
    retry_on: tuple[type] = (TimeoutError, ConnectionError)
    skip_on: tuple[type] = (ValueError, AuthenticationError)
```

### Implementation Pattern

```python
async def execute_with_retry(
    operation: Callable,
    config: RetryConfig,
    session_id: str,
    on_error: Callable = None
) -> Any:
    """Execute operation with automatic retry"""

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await operation()
            return result
        except Exception as e:
            # Check if should retry
            if type(e) not in config.retry_on:
                raise
            if type(e) in config.skip_on:
                raise

            if attempt >= config.max_attempts:
                # Final attempt failed
                await send_websocket_message(session_id, create_event(
                    "error.recovery_failed",
                    content=f"Operation failed after {attempt} attempts",
                    metadata={
                        "error_type": type(e).__name__,
                        "attempt": attempt,
                        "max_attempts": config.max_attempts
                    }
                ))
                raise

            # Calculate backoff
            delay_ms = calculate_retry_delay(attempt, config)

            # Send retry event
            await send_websocket_message(session_id, create_event(
                "error.retry_attempt",
                metadata={
                    "attempt": attempt,
                    "max_attempts": config.max_attempts,
                    "retry_after_ms": delay_ms,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            ))

            # Wait before retry
            await asyncio.sleep(delay_ms / 1000)
```

## Error Event Best Practices

### 1. Always Include Metadata

```python
# ✅ Good
create_event(
    "error.timeout",
    content="Operation timed out",
    metadata={
        "error_code": "ERR_001",
        "attempt": 1,
        "max_attempts": 3,
        "context": {"task_id": "123"}
    }
)

# ❌ Bad - insufficient context
create_event(
    "error.timeout",
    content="Operation timed out"
)
```

### 2. Use Standard Error Codes

Define error codes per service/module:

```python
ERROR_CODES = {
    "ERR_VAL_001": "Validation constraint violated",
    "ERR_TIMEOUT_001": "Operation timeout",
    "ERR_RATE_001": "Rate limit exceeded",
    "ERR_AUTH_001": "Authentication failed",
    "ERR_CONN_001": "Connection lost",
}
```

### 3. Classify Errors Correctly

```python
# Always set recoverable flag based on error type
def is_recoverable(error: Exception) -> bool:
    recoverable_types = (TimeoutError, ConnectionError, IOError)
    permanent_types = (ValueError, KeyError, AuthenticationError)

    if isinstance(error, permanent_types):
        return False
    if isinstance(error, recoverable_types):
        return True
    return False  # Default to non-recoverable
```

### 4. Provide Clear Recovery Hints

```python
# ✅ Clear recovery path
metadata = {
    "recoverable": True,
    "recovery_strategy": "retry_with_exponential_backoff",
    "retry_after_ms": 2000,
    "max_attempts": 3,
    "current_attempt": 1
}

# ❌ Unclear
metadata = {
    "error": "failed"
}
```

## Monitoring & Logging

### Error Event Logging

```python
async def log_error_event(event: dict) -> None:
    """Log error event for monitoring"""
    metadata = event.get("metadata", {})

    logger.error(
        f"Error: {metadata.get('error_code')}",
        extra={
            "event_type": event["event"],
            "recoverable": metadata.get("recoverable"),
            "attempt": metadata.get("attempt"),
            "stage": metadata.get("stage"),
            "operation": metadata.get("operation")
        }
    )

    # Send to monitoring system
    if not metadata.get("recoverable"):
        alert_critical(event)
```

### Metrics to Track

- Error rate by type
- Retry success rate
- Time to recovery
- Unrecoverable errors per session
- Most common error paths

## See Also

- `EVENT_PROTOCOL.md` - Core protocol specification
- `RECONNECTION.md` - Connection recovery strategies
- `EVENT_PAYLOADS.md` - Complete payload reference
