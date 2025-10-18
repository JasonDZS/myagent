# Error Recovery Strategies and Implementation Patterns

Practical implementation patterns for error detection, recovery, and reporting in MyAgent WebSocket agents.

## Table of Contents

1. [Strategy Overview](#strategy-overview)
2. [Tool Execution with Recovery](#tool-execution-with-recovery)
3. [Plan Execution with Error Handling](#plan-execution-with-error-handling)
4. [Server-Side Error Recovery](#server-side-error-recovery)
5. [Client-Side Recovery Handling](#client-side-recovery-handling)
6. [Complete Example Flows](#complete-example-flows)
7. [Monitoring and Debugging](#monitoring-and-debugging)

## Strategy Overview

### Three-Tier Recovery Strategy

```
┌─────────────────────────────────────────────────────┐
│           ERROR RECOVERY STRATEGIES                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│  TIER 1: AUTOMATIC RECOVERY                        │
│  ────────────────────────────────────────────      │
│  Used for: Transient errors (timeout, temp fail)   │
│  Action: Retry with exponential backoff            │
│  Events: error.timeout → error.retry → success    │
│  User: No action needed, transparent               │
│                                                     │
│  TIER 2: USER-GUIDED RECOVERY                      │
│  ────────────────────────────────                  │
│  Used for: Validation/user confirmation errors     │
│  Action: Prompt user for decision/correction      │
│  Events: error.validation → user.response → retry │
│  User: Provide corrected input or decide action   │
│                                                     │
│  TIER 3: MANUAL INTERVENTION                       │
│  ─────────────────────────────────                │
│  Used for: Permanent/resource errors              │
│  Action: Alert user, may need system admin        │
│  Events: error.execution → terminal → fail        │
│  User: Manual investigation and intervention      │
│                                                     └─────────────────────────────────────────────────┘
```

## Tool Execution with Recovery

### Pattern: Retry with Exponential Backoff

```python
from myagent.ws.retry_config import (
    STANDARD_RETRY_CONFIG,
    calculate_retry_delay,
    should_retry,
)
from myagent.ws.events import ErrorEvents, create_event
import asyncio

async def execute_tool_with_retry(
    tool,
    args: dict,
    session_id: str,
    step_id: str,
    emit_event_func,
    config=None
) -> Any:
    """Execute tool with automatic retry and backoff.

    Events emitted:
    - agent.tool_call (start)
    - error.timeout / error.execution (if error)
    - error.retry (before retry)
    - agent.tool_result (success)
    - error.recovery_success (if recovered after retry)
    - error.recovery_failed (if failed after all retries)

    Returns:
        Tool result on success

    Raises:
        Final exception if all retries exhausted
    """
    config = config or STANDARD_RETRY_CONFIG
    last_error = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            # Execute tool
            result = await tool.execute(**args)

            # Success - emit result event
            await emit_event_func(create_event(
                AgentEvents.TOOL_RESULT,
                session_id=session_id,
                step_id=step_id,
                content={
                    "tool_name": tool.name,
                    "result": result,
                    "recovered": attempt > 1
                },
                metadata={
                    "attempt": attempt,
                    "execution_time_ms": elapsed_ms
                }
            ))

            if attempt > 1:
                # Recovered after retry
                await emit_event_func(create_event(
                    ErrorEvents.RECOVERY_SUCCESS,
                    session_id=session_id,
                    step_id=step_id,
                    content="Tool recovered after retry",
                    metadata={
                        "attempts": attempt,
                        "last_error": str(last_error)
                    }
                ))

            return result

        except Exception as e:
            last_error = e

            # Emit error event
            if isinstance(e, TimeoutError):
                error_event = ErrorEvents.TIMEOUT
                error_code = "ERR_TIMEOUT_500"
            elif isinstance(e, ConnectionError):
                error_event = ErrorEvents.EXECUTION
                error_code = "ERR_CONNECTION_900"
            else:
                error_event = ErrorEvents.EXECUTION
                error_code = "ERR_EXECUTION_600"

            await emit_event_func(create_event(
                error_event,
                session_id=session_id,
                step_id=step_id,
                content=str(e),
                metadata={
                    "error_code": error_code,
                    "error_type": type(e).__name__,
                    "tool": tool.name,
                    "attempt": attempt
                }
            ))

            # Check if should retry
            if not should_retry(e, config):
                raise  # Don't retry this type

            if attempt >= config.max_attempts:
                # Max attempts reached
                await emit_event_func(create_event(
                    ErrorEvents.RECOVERY_FAILED,
                    session_id=session_id,
                    step_id=step_id,
                    content=f"Tool failed after {config.max_attempts} attempts",
                    metadata={
                        "error": str(e),
                        "error_code": error_code
                    }
                ))
                raise

            # Calculate retry delay
            delay_ms = calculate_retry_delay(attempt, config)

            # Emit retry event
            await emit_event_func(create_event(
                ErrorEvents.RETRY,
                session_id=session_id,
                step_id=step_id,
                content=f"Retrying tool after {delay_ms}ms",
                metadata={
                    "attempt": attempt,
                    "max_attempts": config.max_attempts,
                    "delay_ms": delay_ms,
                    "error": str(e)
                }
            ))

            # Wait before retry
            await asyncio.sleep(delay_ms / 1000)
```

## Plan Execution with Error Handling

### Pattern: Step-Level Error Recovery

```python
from myagent.ws.events import PlanEvents, SolverEvents, ErrorEvents, create_event

async def execute_plan_with_recovery(
    plan,
    session_id: str,
    emit_event_func,
) -> PlanResult:
    """Execute plan with per-step error recovery.

    Execution flow:
    1. For each step:
       - Execute step
       - On success: emit plan.step_completed
       - On error: emit error.* and attempt recovery
       - If recovery succeeds: emit error.recovery_success, continue
       - If recovery fails: emit error.recovery_failed, fail plan or skip

    Events emitted:
    - plan.start (at beginning)
    - plan.step_completed (on each success)
    - error.validation (on invalid step)
    - solver.step_failed (on execution failure)
    - error.recovery_started (before recovery attempt)
    - error.recovery_success (if recovery succeeds)
    - error.recovery_failed (if recovery fails)
    - plan.completed (at end)

    Returns:
        PlanResult with completed steps
    """
    results = []
    failed_steps = []

    # Emit plan start
    await emit_event_func(create_event(
        PlanEvents.START,
        session_id=session_id,
        content={"plan_description": plan.description},
        metadata={"total_steps": len(plan.steps)}
    ))

    for step_idx, step in enumerate(plan.steps, 1):
        step_id = f"plan_step_{step_idx}"

        try:
            # Validate step
            if not step.is_valid():
                raise ValueError(f"Invalid step: {step.validation_error()}")

            # Execute step
            result = await step.execute()

            # Success
            await emit_event_func(create_event(
                PlanEvents.STEP_COMPLETED,
                session_id=session_id,
                step_id=step_id,
                content=f"Step {step_idx}: {step.name} completed",
                metadata={
                    "step_index": step_idx,
                    "step_name": step.name,
                    "execution_time_ms": result.elapsed_ms,
                    "result_summary": str(result)[:100]
                }
            ))

            results.append(result)

        except ValueError as e:
            # Validation error - notify and skip
            await emit_event_func(create_event(
                ErrorEvents.VALIDATION,
                session_id=session_id,
                step_id=step_id,
                content=str(e),
                metadata={
                    "step_index": step_idx,
                    "error_code": "ERR_VALIDATION_400",
                    "recoverable": False
                }
            ))

            failed_steps.append((step_idx, "validation", str(e)))
            # Continue to next step or fail?
            # raise  # Stop execution

        except Exception as e:
            # Execution error - attempt recovery
            await emit_event_func(create_event(
                SolverEvents.STEP_FAILED,
                session_id=session_id,
                step_id=step_id,
                content=f"Step {step_idx} failed: {str(e)}",
                metadata={
                    "step_index": step_idx,
                    "error_type": type(e).__name__,
                    "recoverable": is_recoverable(e)
                }
            ))

            if is_recoverable(e):
                # Attempt recovery
                await emit_event_func(create_event(
                    ErrorEvents.RECOVERY_STARTED,
                    session_id=session_id,
                    step_id=step_id,
                    content="Attempting step recovery...",
                    metadata={
                        "step_index": step_idx,
                        "recovery_action": "retry_with_cleanup"
                    }
                ))

                try:
                    # Cleanup and retry
                    await step.cleanup()
                    result = await step.execute()

                    await emit_event_func(create_event(
                        ErrorEvents.RECOVERY_SUCCESS,
                        session_id=session_id,
                        step_id=step_id,
                        content="Step recovered successfully",
                        metadata={
                            "step_index": step_idx,
                            "recovery_time_ms": recovery_elapsed
                        }
                    ))

                    results.append(result)

                except Exception as recovery_error:
                    # Recovery failed
                    await emit_event_func(create_event(
                        ErrorEvents.RECOVERY_FAILED,
                        session_id=session_id,
                        step_id=step_id,
                        content=f"Recovery failed: {str(recovery_error)}",
                        metadata={
                            "step_index": step_idx,
                            "original_error": str(e),
                            "recovery_error": str(recovery_error)
                        }
                    ))

                    failed_steps.append((step_idx, "execution", str(e)))
                    raise  # Stop execution
            else:
                # Not recoverable
                failed_steps.append((step_idx, "execution", str(e)))
                raise

    # Emit completion
    success = len(failed_steps) == 0
    await emit_event_func(create_event(
        PlanEvents.COMPLETED,
        session_id=session_id,
        content={
            "steps_completed": len(results),
            "total_steps": len(plan.steps),
            "success": success
        },
        metadata={
            "steps_total": len(plan.steps),
            "steps_successful": len(results),
            "steps_failed": len(failed_steps),
            "failed_steps": failed_steps
        }
    ))

    return PlanResult(
        completed_steps=results,
        failed_steps=failed_steps,
        success=success
    )
```

## Server-Side Error Recovery

### Pattern: Session-Level Error Handler in WebSocket Server

```python
# In server.py or session handler

async def handle_agent_execution_with_recovery(
    session: AgentSession,
    task: Task,
) -> None:
    """Execute agent task with comprehensive error recovery.

    Integrates with:
    - Session event buffer (for replay on reconnect)
    - Error tracking (for monitoring)
    - User confirmation (for dangerous operations)
    """
    session_id = session.session_id
    step_id = str(uuid.uuid4())

    try:
        # Execute task
        result = await session.agent.execute(task)

        # Emit success
        await session.send_event(create_event(
            AgentEvents.FINAL_ANSWER,
            session_id=session_id,
            step_id=step_id,
            content=result.answer,
            metadata={
                "execution_time_ms": result.elapsed_ms,
                "tokens_used": result.tokens
            }
        ))

    except Exception as e:
        # Determine error type
        error_type = classify_error(e)

        if error_type == "VALIDATION":
            # Validation error - inform user
            await session.send_event(create_event(
                ErrorEvents.VALIDATION,
                session_id=session_id,
                step_id=step_id,
                content=str(e),
                metadata={"error_code": "ERR_VALIDATION_400"}
            ))

        elif error_type == "TRANSIENT":
            # Transient error - attempt recovery
            await handle_transient_error(
                session,
                e,
                task,
                step_id
            )

        elif error_type == "PERMANENT":
            # Permanent error - inform and terminate
            await session.send_event(create_event(
                ErrorEvents.EXECUTION,
                session_id=session_id,
                step_id=step_id,
                content=f"Unrecoverable error: {str(e)}",
                metadata={
                    "error_code": "ERR_EXECUTION_600",
                    "error_type": type(e).__name__
                }
            ))

        # Log error for monitoring
        log_error(session_id, error_type, e)

async def handle_transient_error(
    session: AgentSession,
    error: Exception,
    task: Task,
    step_id: str,
) -> None:
    """Handle transient errors with automatic retry."""
    session_id = session.session_id
    config = STANDARD_RETRY_CONFIG

    for attempt in range(1, config.max_attempts + 1):
        try:
            # Emit retry event
            delay_ms = calculate_retry_delay(attempt, config)

            await session.send_event(create_event(
                ErrorEvents.RETRY,
                session_id=session_id,
                step_id=step_id,
                content=f"Retrying task attempt {attempt}/{config.max_attempts}",
                metadata={
                    "attempt": attempt,
                    "delay_ms": delay_ms,
                    "error": str(error)
                }
            ))

            # Wait before retry
            await asyncio.sleep(delay_ms / 1000)

            # Retry execution
            result = await session.agent.execute(task)

            # Success - emit recovery success
            await session.send_event(create_event(
                ErrorEvents.RECOVERY_SUCCESS,
                session_id=session_id,
                step_id=step_id,
                content="Task recovered after retry",
                metadata={
                    "attempt": attempt,
                    "recovery_time_ms": elapsed_ms
                }
            ))

            return result

        except Exception as retry_error:
            error = retry_error  # Update for next iteration
            continue

    # All retries failed
    await session.send_event(create_event(
        ErrorEvents.RECOVERY_FAILED,
        session_id=session_id,
        step_id=step_id,
        content="Task failed after all retry attempts",
        metadata={
            "attempts": config.max_attempts,
            "error": str(error)
        }
    ))
```

## Client-Side Recovery Handling

### Pattern: Client-Side Error UI and Recovery

```javascript
// JavaScript/Frontend - Error handling patterns

class AgentClient {
  constructor(url, handlers = {}) {
    this.url = url;
    this.handlers = handlers;
    this.retryQueue = [];
    this.errorState = null;
  }

  // Handle incoming error events
  async onErrorEvent(event) {
    const { event_type, content, metadata, step_id } = event;

    switch (event_type) {
      case "error.validation":
        this.showValidationError(content, metadata);
        break;

      case "error.timeout":
        this.showTimeoutError(content, metadata, step_id);
        break;

      case "error.execution":
        this.showExecutionError(content, metadata, step_id);
        break;

      case "error.retry":
        this.showRetryInProgress(content, metadata, step_id);
        break;

      case "error.recovery_started":
        this.showRecoveryInProgress(content, metadata, step_id);
        break;

      case "error.recovery_success":
        this.showRecoverySuccess(content, metadata, step_id);
        break;

      case "error.recovery_failed":
        this.showRecoveryFailed(content, metadata, step_id);
        break;
    }
  }

  // Show validation error and prompt for correction
  showValidationError(message, metadata) {
    const errorUI = {
      type: "validation_error",
      message: message,
      field: metadata?.field,
      constraint: metadata?.constraint,
      actions: [
        {
          label: "Fix and Retry",
          callback: () => this.handleUserCorrection()
        },
        {
          label: "Cancel",
          callback: () => this.cancelTask()
        }
      ]
    };

    this.handlers.onError?.(errorUI);
  }

  // Show timeout error with retry info
  showTimeoutError(message, metadata, stepId) {
    const { attempt, max_attempts, delay_ms } = metadata || {};

    if (attempt && attempt < max_attempts) {
      // Auto-retrying, show progress
      this.showProgress({
        type: "timeout_retry",
        message: `Operation timed out. Retrying in ${delay_ms}ms...`,
        retry_attempt: attempt,
        max_attempts: max_attempts,
        step_id: stepId
      });
    } else {
      // Max retries exceeded or no retry
      this.showError({
        type: "timeout_failed",
        message: message,
        step_id: stepId,
        actions: [
          {
            label: "Retry Manually",
            callback: () => this.retryTask(stepId)
          },
          {
            label: "Cancel",
            callback: () => this.cancelTask()
          }
        ]
      });
    }
  }

  // Show execution error with recovery options
  showExecutionError(message, metadata, stepId) {
    const { error_type, error_code } = metadata || {};

    this.showError({
      type: "execution_error",
      message: message,
      error_code: error_code,
      step_id: stepId,
      actions: [
        {
          label: "Retry",
          callback: () => this.sendRetryRequest(stepId)
        },
        {
          label: "Get Details",
          callback: () => this.showErrorDetails(metadata)
        },
        {
          label: "Cancel",
          callback: () => this.cancelTask()
        }
      ]
    });
  }

  // Show automatic recovery progress
  showRecoveryInProgress(message, metadata, stepId) {
    this.showProgress({
      type: "recovery",
      message: message,
      recovery_action: metadata?.recovery_action,
      step_id: stepId
    });
  }

  // Handle recovery success
  showRecoverySuccess(message, metadata, stepId) {
    this.showSuccess({
      type: "recovery_success",
      message: message,
      recovery_time_ms: metadata?.recovery_time_ms,
      step_id: stepId
    });
  }

  // Handle recovery failure
  showRecoveryFailed(message, metadata, stepId) {
    this.showError({
      type: "recovery_failed",
      message: message,
      original_error: metadata?.original_error,
      recovery_error: metadata?.recovery_error,
      step_id: stepId,
      actions: [
        {
          label: "Try Again",
          callback: () => this.retryTask(stepId)
        },
        {
          label: "Cancel",
          callback: () => this.cancelTask()
        }
      ]
    });
  }

  // Send user correction
  sendUserCorrection(correctedData) {
    this.send({
      event: "user.response",
      step_id: this.currentStepId,
      content: correctedData
    });
  }

  // Send retry request
  sendRetryRequest(stepId) {
    this.send({
      event: "user.retry_task",
      step_id: stepId,
      content: "User initiated retry"
    });
  }

  // Send cancel request
  sendCancelRequest(stepId) {
    this.send({
      event: "user.cancel",
      step_id: stepId,
      content: "User cancelled task"
    });
  }
}
```

## Complete Example Flows

### Flow 1: Validation Error Recovery

```
User Input
    ↓
Validate
    ↓
❌ Validation Error
    ↓
Emit: error.validation
  content: "Email format invalid"
  metadata: {field: "email", constraint: "RFC5321"}
    ↓
Show Error UI to User
  "Email format invalid. Please fix and retry."
    ↓
User Corrects Input
    ↓
Send: user.response (with corrected email)
    ↓
Validate Again
    ↓
✅ Valid
    ↓
Continue Processing
```

### Flow 2: Timeout with Automatic Retry

```
Execute Tool
    ↓
⏱️ Timeout (30s exceeded)
    ↓
Emit: error.timeout
  attempt: 1, max_attempts: 3
    ↓
Wait: 1000ms
    ↓
Retry Tool
    ↓
⏱️ Timeout Again
    ↓
Emit: error.retry
  attempt: 2, delay_ms: 2000
    ↓
Wait: 2000ms
    ↓
Retry Tool
    ↓
✅ Success
    ↓
Emit: error.recovery_success
    ↓
Continue
```

### Flow 3: Execution Error with Manual Recovery

```
Execute Tool
    ↓
❌ Execution Error
  "API returned 500"
    ↓
Emit: error.execution
    ↓
Is Recoverable?
  ├─ Yes → Attempt cleanup
  │   ↓
  │   Emit: error.recovery_started
  │   ↓
  │   Cleanup Resources
  │   ↓
  │   Retry Tool
  │   ↓
  │   ├─ ✅ Success
  │   │   Emit: error.recovery_success
  │   │   Continue
  │   │
  │   └─ ❌ Failed
  │       Emit: error.recovery_failed
  │       Fail Task
  │
  └─ No → Fail immediately
      Emit: error.recovery_failed
      Fail Task
```

## Monitoring and Debugging

### Error Tracking and Metrics

```python
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime, timedelta

@dataclass
class ErrorMetrics:
    """Track error patterns for monitoring."""

    error_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_recovery_rates: dict[str, float] = field(default_factory=dict)
    avg_recovery_time_ms: dict[str, float] = field(default_factory=dict)
    session_errors: dict[str, list] = field(default_factory=lambda: defaultdict(list))

    def record_error(self, error_type: str, session_id: str) -> None:
        """Record error occurrence."""
        self.error_counts[error_type] += 1
        self.session_errors[session_id].append({
            "error_type": error_type,
            "timestamp": datetime.now()
        })

    def record_recovery_success(
        self,
        error_type: str,
        recovery_time_ms: int
    ) -> None:
        """Record successful recovery."""
        # Update success rate
        # Update avg recovery time

    def get_error_report(self, time_window_hours: int = 24) -> dict:
        """Generate error report for monitoring."""
        cutoff = datetime.now() - timedelta(hours=time_window_hours)

        return {
            "error_counts": dict(self.error_counts),
            "recovery_rates": self.error_recovery_rates,
            "avg_recovery_times_ms": self.avg_recovery_time_ms,
            "top_errors": sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
```

### Debug Logging

```python
# Comprehensive error logging

def log_error_details(
    error: Exception,
    context: dict
) -> None:
    """Log error with full context for debugging."""
    logger.error(
        "Error occurred",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "session_id": context.get("session_id"),
            "step_id": context.get("step_id"),
            "attempt": context.get("attempt"),
            "error_traceback": traceback.format_exc()
        }
    )
```

