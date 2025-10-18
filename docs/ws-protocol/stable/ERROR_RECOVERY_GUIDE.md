# Error Recovery Guide

Complete guide for implementing comprehensive error handling and recovery flows in MyAgent WebSocket protocol.

## Table of Contents

1. [Error Classification System](#error-classification-system)
2. [Error Detection and Emission](#error-detection-and-emission)
3. [Recovery State Machines](#recovery-state-machines)
4. [Exponential Backoff and Retry Logic](#exponential-backoff-and-retry-logic)
5. [Implementation Patterns](#implementation-patterns)
6. [Configuration](#configuration)
7. [Testing and Validation](#testing-and-validation)

## Error Classification System

### Error Types and Characteristics

```
┌─────────────────────────────────────────────────────────────┐
│            ERROR CLASSIFICATION HIERARCHY                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ❌ ValidationError                                         │
│     └─ Characteristics: Immediate, deterministic           │
│     └─ Cause: Invalid input data, constraint violation     │
│     └─ Recovery: Inform user, request corrected input      │
│     └─ Retry: Usually not helpful (same input fails)       │
│     └─ User action: Manual correction required             │
│                                                             │
│  ⏱️  TimeoutError                                           │
│     └─ Characteristics: Time-dependent, transient          │
│     └─ Cause: Long execution, slow network, overload       │
│     └─ Recovery: Wait and retry with backoff               │
│     └─ Retry: Yes, with exponential backoff                │
│     └─ User action: Can auto-retry or prompt               │
│                                                             │
│  🚫 ExecutionError                                          │
│     └─ Characteristics: Immediate, might be transient      │
│     └─ Cause: Tool execution failure, API error            │
│     └─ Recovery: Depends on error code                     │
│     └─ Retry: Maybe - check error details                  │
│     └─ User action: May need intervention                  │
│                                                             │
│  🔗 RateLimitError                                          │
│     └─ Characteristics: Transient, requires delay          │
│     └─ Cause: API rate limit exceeded                      │
│     └─ Recovery: Exponential backoff with server hint      │
│     └─ Retry: Yes, after server-specified delay            │
│     └─ User action: Automatic retry                        │
│                                                             │
│  💾 ResourceError                                           │
│     └─ Characteristics: Immediate, often permanent         │
│     └─ Cause: Memory, disk, database limit reached         │
│     └─ Recovery: Cleanup and retry or fail gracefully      │
│     └─ Retry: Maybe, after cleanup                         │
│     └─ User action: May require admin intervention         │
│                                                             │
│  🔌 ConnectionError                                         │
│     └─ Characteristics: Network-level, transient           │
│     └─ Cause: Network loss, DNS failure, firewall          │
│     └─ Recovery: Connection recovery protocol              │
│     └─ Retry: Yes, with session recovery                   │
│     └─ User action: Automatic reconnection                 │
│                                                             └─────────────────────────────────────────────────────────────┘
```

### Error Codes and Meanings

```python
# Validation Errors (4xx range)
ERR_VALIDATION_400    = "Invalid input data"
ERR_VALIDATION_401    = "Missing required field"
ERR_VALIDATION_402    = "Constraint violated"
ERR_VALIDATION_403    = "Type mismatch"

# Timeout Errors (5xx range - client timeout)
ERR_TIMEOUT_500       = "Request timeout"
ERR_TIMEOUT_501       = "Execution timeout"
ERR_TIMEOUT_502       = "Response timeout"

# Execution Errors (6xx range)
ERR_EXECUTION_600     = "Tool execution failed"
ERR_EXECUTION_601     = "API call failed"
ERR_EXECUTION_602     = "Database error"
ERR_EXECUTION_603     = "Resource exhausted"

# Rate Limiting (7xx range)
ERR_RATELIMIT_700     = "Rate limit exceeded"
ERR_RATELIMIT_701     = "Quota exceeded"
ERR_RATELIMIT_702     = "Concurrency limit"

# Connection Errors (9xx range)
ERR_CONNECTION_900    = "Connection lost"
ERR_CONNECTION_901    = "Connection refused"
ERR_CONNECTION_902    = "Invalid session"
```

## Error Detection and Emission

### When to Emit Error Events

```python
# Pattern 1: Validation error (immediate)
try:
    validate_input(user_data)
except ValidationError as e:
    await emit_event(ErrorEvents.VALIDATION,
        content=str(e),
        metadata={
            "error_code": "ERR_VALIDATION_400",
            "field": e.field,
            "constraint": e.constraint,
            "timestamp": datetime.now().isoformat()
        }
    )
    # NO retry - user must correct

# Pattern 2: Transient error (auto-retry)
max_attempts = 3
for attempt in range(1, max_attempts + 1):
    try:
        result = await execute_with_timeout(task, timeout=30)
        break
    except TimeoutError as e:
        await emit_event(ErrorEvents.TIMEOUT,
            content=f"Timeout after {e.elapsed}s",
            metadata={
                "error_code": "ERR_TIMEOUT_500",
                "attempt": attempt,
                "max_attempts": max_attempts,
                "timeout_seconds": 30,
                "elapsed_seconds": e.elapsed,
                "retry_after_ms": calculate_backoff(attempt)
            }
        )
        if attempt < max_attempts:
            await asyncio.sleep(calculate_backoff(attempt) / 1000)
        else:
            # Max attempts reached
            await emit_event(ErrorEvents.RECOVERY_FAILED,
                content="Max retries exceeded",
                metadata={"error_code": "ERR_TIMEOUT_500"}
            )

# Pattern 3: Execution error with recovery
try:
    result = await execute_tool(tool_call)
except ExecutionError as e:
    await emit_event(ErrorEvents.EXECUTION,
        content=str(e),
        metadata={
            "error_code": "ERR_EXECUTION_600",
            "error_type": type(e).__name__,
            "tool_name": tool_call.name,
            "context": {"step": current_step, "retry_possible": True}
        }
    )

    if should_retry(e):
        await emit_event(ErrorEvents.RECOVERY_STARTED,
            content="Attempting recovery...",
            metadata={"recovery_action": "retry_with_cleanup"}
        )
        # Attempt recovery
        try:
            result = await execute_tool(tool_call)
            await emit_event(ErrorEvents.RECOVERY_SUCCESS,
                content="Recovery successful",
                metadata={"recovery_time_ms": elapsed}
            )
        except Exception as recovery_error:
            await emit_event(ErrorEvents.RECOVERY_FAILED,
                content=str(recovery_error),
                metadata={"error_code": "ERR_EXECUTION_600"}
            )
```

## Recovery State Machines

### Validation Error Flow

```
┌──────────────────┐
│  ValidationError │
│    Detected      │
└────────┬─────────┘
         │
         ▼
   ┌───────────────────────┐
   │ Emit error.validation │
   │ (content, metadata)   │
   └───────────┬───────────┘
               │
               ▼
         ┌──────────────────┐
         │ Await user input │
         │ with error hint  │
         └────────┬─────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
    ┌─────────┐      ┌──────────┐
    │ Corrected│     │ Cancelled│
    └────┬────┘      └─────┬────┘
         │                 │
         ▼                 ▼
   ┌──────────┐      ┌───────────┐
   │  Retry   │      │ Terminate │
   │   Flow   │      │   Flow    │
   └──────────┘      └───────────┘
```

**State Details:**
- **Initial**: User input rejected due to validation
- **Error Emitted**: Send `error.validation` with field and constraint info
- **Awaiting Correction**: Client displays error to user
- **User Corrects**: Client sends `user.response` with corrected data
- **Retry**: Server retries with corrected input
- **User Cancels**: User clicks cancel, server cleans up

### Transient Error Flow (Timeout/RateLimit)

```
┌──────────────────┐
│  Transient Error │
│  (Timeout/Rate)  │
└────────┬─────────┘
         │
         ▼
   ┌───────────────────────┐
   │ Emit error.timeout or │
   │ error.ratelimit       │
   │ Include retry_after   │
   └───────────┬───────────┘
               │
               ▼
      ┌──────────────────────────┐
      │ Wait (exponential backoff)│
      │ delay = backoff(attempt) │
      └───────────┬──────────────┘
                  │
         ┌────────┴────────┐
         │                 │
      (attempt < max)   (attempt >= max)
         │                 │
         ▼                 ▼
   ┌──────────┐      ┌──────────────┐
   │  RETRY   │      │ RECOVERY_FAIL│
   │  Task    │      │ Emit error   │
   └────┬─────┘      └──────────────┘
        │
        ├─ Success ──→ Continue
        │
        └─ Failure ──→ Backoff again (or fail)
```

**Backoff Calculation:**
```
attempt = 1:  delay = 1000ms + jitter
attempt = 2:  delay = 2000ms + jitter
attempt = 3:  delay = 4000ms + jitter
attempt = 4:  delay = 8000ms + jitter (capped at 60s)
...
```

### Execution Error with Recovery

```
┌──────────────────┐
│ ExecutionError   │
│    Detected      │
└────────┬─────────┘
         │
         ▼
   ┌───────────────────────┐
   │ Emit error.execution  │
   │ Include context       │
   └───────────┬───────────┘
               │
               ▼
        ┌──────────────────┐
        │ Assess recovery  │
        │ possibility      │
        └────────┬─────────┘
                 │
         ┌───────┴────────┐
         │                │
    (recoverable)   (not recoverable)
         │                │
         ▼                ▼
    ┌─────────────┐  ┌────────────┐
    │ RECOVERY_   │  │ RECOVERY_  │
    │ STARTED     │  │ FAILED     │
    │ Cleanup +   │  │ Terminate  │
    │ Retry       │  │ Flow       │
    └──────┬──────┘  └────────────┘
           │
           ├─ Success ──→ RECOVERY_SUCCESS
           │
           └─ Failure ──→ RECOVERY_FAILED
```

## Exponential Backoff and Retry Logic

### Backoff Calculation Algorithm

```python
import random
from dataclasses import dataclass

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1  # ±10%

    # Error-specific retry settings
    retry_on: tuple = (TimeoutError, ConnectionError, RateLimitError)
    skip_on: tuple = (ValidationError, AuthenticationError)

def calculate_retry_delay(
    attempt: int,
    config: RetryConfig
) -> int:
    """Calculate delay in milliseconds for retry attempt.

    Args:
        attempt: 1-based attempt number
        config: RetryConfig with settings

    Returns:
        Delay in milliseconds

    Example:
        attempt=1 → ~1000ms
        attempt=2 → ~2000ms ±200ms
        attempt=3 → ~4000ms ±400ms
    """
    # Exponential calculation
    delay = config.initial_delay_ms * (
        config.backoff_multiplier ** (attempt - 1)
    )

    # Cap at maximum
    delay = min(delay, config.max_delay_ms)

    # Add jitter (±10%)
    jitter_range = delay * config.jitter_factor
    jitter = random.uniform(-jitter_range, jitter_range)
    delay = max(config.initial_delay_ms, delay + jitter)

    return int(delay)

def should_retry(error: Exception, config: RetryConfig) -> bool:
    """Determine if error should trigger retry."""
    # Never retry certain error types
    if isinstance(error, config.skip_on):
        return False

    # Retry configured types
    if isinstance(error, config.retry_on):
        return True

    # Default: don't retry unknown errors
    return False
```

### Retry Loop Pattern

```python
async def execute_with_retry(
    task_func,
    *args,
    config: RetryConfig = None,
    **kwargs
) -> Any:
    """Execute task with automatic retry and backoff.

    Args:
        task_func: Async function to execute
        config: RetryConfig with retry settings

    Returns:
        Result from task_func

    Raises:
        Max retries exceeded or non-retryable error
    """
    config = config or RetryConfig()

    for attempt in range(1, config.max_attempts + 1):
        try:
            result = await task_func(*args, **kwargs)

            # Success - emit success event
            if attempt > 1:
                await emit_event(ErrorEvents.RECOVERY_SUCCESS,
                    content="Recovered after retry",
                    metadata={
                        "attempt": attempt,
                        "task": task_func.__name__
                    }
                )

            return result

        except Exception as e:
            # Check if we should retry
            if not should_retry(e, config):
                raise

            # Check if we have attempts left
            if attempt >= config.max_attempts:
                await emit_event(ErrorEvents.RECOVERY_FAILED,
                    content=f"Max retries ({config.max_attempts}) exceeded",
                    metadata={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "final_attempt": attempt
                    }
                )
                raise

            # Emit retry event
            delay_ms = calculate_retry_delay(attempt, config)
            await emit_event(ErrorEvents.RETRY,
                content=f"Retrying after {delay_ms}ms",
                metadata={
                    "attempt": attempt,
                    "max_attempts": config.max_attempts,
                    "delay_ms": delay_ms,
                    "error": str(e)
                }
            )

            # Wait before retry
            await asyncio.sleep(delay_ms / 1000)
```

## Implementation Patterns

### Pattern 1: Tool Execution with Error Handling

```python
async def execute_tool_with_recovery(
    tool_call: ToolCall,
    session_id: str,
    step_id: str
) -> ToolResult:
    """Execute tool with comprehensive error handling.

    Emits events:
    - agent.tool_call (start)
    - error.execution (if execution fails)
    - error.recovery_started (if recovery attempted)
    - error.recovery_success (if recovery succeeds)
    - error.recovery_failed (if recovery fails)
    - agent.tool_result (on success)
    """
    config = RetryConfig(max_attempts=3, initial_delay_ms=500)

    async def execute():
        try:
            return await tool_call.execute()
        except ValidationError as e:
            # Validation errors don't retry
            await emit_event(
                ErrorEvents.VALIDATION,
                session_id=session_id,
                step_id=step_id,
                content=str(e),
                metadata={
                    "error_code": "ERR_VALIDATION_400",
                    "tool": tool_call.name,
                    "field": getattr(e, 'field', None)
                }
            )
            raise
        except TimeoutError as e:
            await emit_event(
                ErrorEvents.TIMEOUT,
                session_id=session_id,
                step_id=step_id,
                content=f"Tool execution timeout",
                metadata={
                    "error_code": "ERR_TIMEOUT_500",
                    "timeout_seconds": config.initial_delay_ms / 1000,
                    "tool": tool_call.name
                }
            )
            raise
        except Exception as e:
            await emit_event(
                ErrorEvents.EXECUTION,
                session_id=session_id,
                step_id=step_id,
                content=f"Tool execution failed: {str(e)}",
                metadata={
                    "error_code": "ERR_EXECUTION_600",
                    "error_type": type(e).__name__,
                    "tool": tool_call.name
                }
            )
            raise

    try:
        result = await execute_with_retry(execute, config=config)
        return result
    except Exception as e:
        if should_retry(e, config):
            await emit_event(
                ErrorEvents.RECOVERY_FAILED,
                session_id=session_id,
                step_id=step_id,
                content="Tool execution failed after all retries",
                metadata={"tool": tool_call.name}
            )
        raise
```

### Pattern 2: Plan Execution with Step-Level Error Handling

```python
async def execute_plan_with_error_recovery(
    plan: Plan,
    session_id: str
) -> PlanResult:
    """Execute plan with per-step error handling.

    Emits:
    - plan.step_completed (on success)
    - error.validation (on invalid step)
    - solver.step_failed (on execution failure)
    - solver.retry (on retry attempt)
    """
    results = []

    for step_idx, step in enumerate(plan.steps, 1):
        step_id = f"step_{step_idx}"

        try:
            # Execute step
            result = await execute_step(step)

            await emit_event(
                PlanEvents.STEP_COMPLETED,
                session_id=session_id,
                step_id=step_id,
                content=f"Step {step_idx} completed",
                metadata={
                    "step_index": step_idx,
                    "step_name": step.name,
                    "result_summary": result.summary
                }
            )

            results.append(result)

        except ValidationError as e:
            # Log and continue or fail?
            await emit_event(
                ErrorEvents.VALIDATION,
                session_id=session_id,
                step_id=step_id,
                content=str(e),
                metadata={"step_index": step_idx}
            )
            # Decide: fail or skip
            raise

        except Exception as e:
            # Try recovery
            await emit_event(
                SolverEvents.STEP_FAILED,
                session_id=session_id,
                step_id=step_id,
                content=f"Step failed: {str(e)}",
                metadata={
                    "step_index": step_idx,
                    "error_type": type(e).__name__
                }
            )

            # Attempt recovery
            try:
                result = await execute_step(step)
                await emit_event(
                    ErrorEvents.RECOVERY_SUCCESS,
                    session_id=session_id,
                    step_id=step_id,
                    content="Step recovered",
                    metadata={"step_index": step_idx}
                )
                results.append(result)
            except Exception as final_error:
                await emit_event(
                    ErrorEvents.RECOVERY_FAILED,
                    session_id=session_id,
                    step_id=step_id,
                    content=f"Could not recover: {str(final_error)}",
                    metadata={"step_index": step_idx}
                )
                # Fail the entire plan or skip this step?
                raise

    return PlanResult(steps_completed=len(results))
```

## Configuration

### Retry Configuration in Application

```python
from dataclasses import dataclass

@dataclass
class ErrorRecoveryConfig:
    """Global error recovery configuration."""

    # Retry settings
    max_attempts: int = 3
    initial_backoff_ms: int = 1000
    max_backoff_ms: int = 60000
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1

    # Error type settings
    retry_on_timeout: bool = True
    retry_on_ratelimit: bool = True
    retry_on_connection_error: bool = True

    # Timeout settings
    tool_execution_timeout_s: int = 30
    api_call_timeout_s: int = 30

    # Recovery strategies
    enable_auto_recovery: bool = True
    enable_user_confirmation: bool = False  # For dangerous operations

    # Logging
    log_all_errors: bool = True
    log_retry_attempts: bool = True

    @classmethod
    def from_env(cls) -> "ErrorRecoveryConfig":
        """Load from environment variables."""
        import os
        return cls(
            max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", 3)),
            initial_backoff_ms=int(os.getenv("RETRY_INITIAL_MS", 1000)),
            max_backoff_ms=int(os.getenv("RETRY_MAX_MS", 60000)),
            tool_execution_timeout_s=int(os.getenv("TOOL_TIMEOUT_S", 30)),
        )
```

## Testing and Validation

### Test Scenarios

```python
import pytest

@pytest.mark.asyncio
async def test_validation_error_no_retry():
    """Validation errors should not retry."""
    config = RetryConfig(max_attempts=3)

    async def bad_func():
        raise ValidationError("Invalid input")

    with pytest.raises(ValidationError):
        await execute_with_retry(bad_func, config=config)

@pytest.mark.asyncio
async def test_timeout_with_backoff():
    """Timeout should retry with exponential backoff."""
    config = RetryConfig(
        max_attempts=3,
        initial_delay_ms=100,
        backoff_multiplier=2.0
    )

    attempt = 0
    async def sometimes_fails():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise TimeoutError("Timeout")
        return "success"

    result = await execute_with_retry(sometimes_fails, config=config)
    assert result == "success"
    assert attempt == 3  # Should have retried twice

@pytest.mark.asyncio
async def test_max_retries_exceeded():
    """Should fail after max retries."""
    config = RetryConfig(max_attempts=2)

    async def always_fails():
        raise TimeoutError("Always fails")

    with pytest.raises(TimeoutError):
        await execute_with_retry(always_fails, config=config)

@pytest.mark.asyncio
async def test_event_emission_on_retry():
    """Should emit error and retry events."""
    events = []

    async def emit_event(event_type, **kwargs):
        events.append((event_type, kwargs))

    # ... test that events are emitted correctly
    assert any(e[0] == ErrorEvents.RETRY for e in events)
    assert any(e[0] == ErrorEvents.RECOVERY_SUCCESS for e in events)
```

### Integration Test Example

```python
@pytest.mark.asyncio
async def test_full_error_recovery_flow():
    """Test complete error detection, recovery, and reporting."""

    # Setup
    session_id = "test_session_001"
    agent = create_test_agent()

    # Execute task that will fail then succeed
    result = await agent.execute_task(
        task_id="task_1",
        session_id=session_id,
        will_fail_count=1  # Fail once, then succeed
    )

    # Verify
    assert result.success
    assert result.retry_count == 1

    # Check events were emitted
    events = get_recorded_events(session_id)
    error_events = [e for e in events if e.event.startswith("error.")]
    assert len(error_events) >= 1
```

## Best Practices

1. **Always emit error events** before attempting recovery
2. **Include context in metadata** for debugging
3. **Use step_id** for request/response pairing
4. **Validate retry strategy** for each error type
5. **Log all retries** for monitoring
6. **Test error paths** explicitly
7. **Provide user feedback** during recovery
8. **Clean up resources** before retry
9. **Set reasonable timeouts** to avoid hanging
10. **Monitor error rates** in production

