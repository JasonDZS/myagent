# Payload Validation Guide and Code Generation

Comprehensive guide for validating event payloads and generating type-safe code for MyAgent WebSocket events.

## Table of Contents

1. [Validation Rules](#validation-rules)
2. [Python Validation](#python-validation)
3. [TypeScript Validation](#typescript-validation)
4. [Code Generation](#code-generation)
5. [Runtime Validation](#runtime-validation)
6. [Testing](#testing)

---

## Validation Rules

### Core Validation Principles

1. **Required Fields**: Validate presence of required fields
2. **Type Checking**: Ensure field types match specification
3. **Content Rules**: Validate content field structure
4. **Metadata Rules**: Validate metadata field structure
5. **Constraint Checking**: Validate business logic constraints

### Field Validation Matrix

| Event Type | Required Fields | Validation Rules |
|------------|-----------------|------------------|
| user.message | session_id, content | content: string; len > 0 |
| user.response | session_id, step_id, content | content.approved: boolean |
| plan.completed | session_id, content, metadata | content.tasks: array; metadata.task_count: int |
| agent.tool_call | session_id, step_id, content | content.tool_name: string; content.arguments: object |
| agent.final_answer | session_id, step_id, content | content.answer: string; content.answer_type: enum |
| error.timeout | session_id, step_id, content, metadata | metadata.error_code == "ERR_TIMEOUT_500" |

---

## Python Validation

### Validation Functions

```python
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

class PayloadValidator:
    """Validate WebSocket event payloads."""

    # Required fields per event type
    REQUIRED_FIELDS = {
        "user.message": ["session_id", "content"],
        "user.response": ["session_id", "step_id", "content"],
        "user.ack": ["session_id", "content"],
        "plan.completed": ["session_id", "step_id", "content", "metadata"],
        "plan.validation_error": ["session_id", "step_id", "content", "metadata"],
        "solver.progress": ["session_id", "step_id", "metadata"],
        "agent.tool_call": ["session_id", "step_id", "content", "metadata"],
        "agent.final_answer": ["session_id", "step_id", "content", "metadata"],
        "error.timeout": ["session_id", "step_id", "content", "metadata"],
        "error.execution": ["session_id", "step_id", "content", "metadata"],
    }

    # Type constraints per field
    TYPE_CONSTRAINTS = {
        "user.message": {
            "content": str,
            "session_id": str,
        },
        "user.response": {
            "content": dict,
            "session_id": str,
            "step_id": str,
        },
        "plan.completed": {
            "content": dict,
            "metadata": dict,
        },
        "agent.tool_call": {
            "content": dict,
            "metadata": dict,
        },
    }

    @classmethod
    def validate(cls, event: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate event payload.

        Args:
            event: Event dictionary to validate

        Returns:
            (is_valid, error_message)
        """
        event_type = event.get("event")
        if not event_type:
            return False, "Missing 'event' field"

        # Check required fields
        required = cls.REQUIRED_FIELDS.get(event_type, [])
        for field in required:
            if field not in event:
                return False, f"Missing required field: {field}"

        # Check types
        type_checks = cls.TYPE_CONSTRAINTS.get(event_type, {})
        for field, expected_type in type_checks.items():
            if field in event and not isinstance(event[field], expected_type):
                return False, f"Field '{field}' has wrong type. Expected {expected_type.__name__}"

        # Event-specific validation
        is_valid, error = cls.validate_event_specific(event)
        if not is_valid:
            return False, error

        return True, None

    @classmethod
    def validate_event_specific(cls, event: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Event-specific validation rules."""
        event_type = event.get("event")

        # Validate user.response
        if event_type == "user.response":
            content = event.get("content", {})
            if "approved" not in content or not isinstance(content["approved"], bool):
                return False, "user.response content must have 'approved' boolean field"

        # Validate plan.completed
        elif event_type == "plan.completed":
            content = event.get("content", {})
            if "tasks" not in content or not isinstance(content["tasks"], list):
                return False, "plan.completed content must have 'tasks' array"
            metadata = event.get("metadata", {})
            if metadata.get("task_count") != len(content["tasks"]):
                return False, "metadata.task_count must match number of tasks"

        # Validate agent.tool_call
        elif event_type == "agent.tool_call":
            content = event.get("content", {})
            required_fields = ["tool_name", "tool_description", "arguments"]
            for field in required_fields:
                if field not in content:
                    return False, f"agent.tool_call content missing '{field}'"

        # Validate agent.final_answer
        elif event_type == "agent.final_answer":
            content = event.get("content", {})
            if "answer" not in content or not isinstance(content["answer"], str):
                return False, "agent.final_answer content must have 'answer' string field"
            answer_type = content.get("answer_type")
            valid_types = ["text", "json", "code", "structured"]
            if answer_type not in valid_types:
                return False, f"answer_type must be one of {valid_types}"

        # Validate error events
        elif event_type.startswith("error."):
            metadata = event.get("metadata", {})
            if "error_code" not in metadata:
                return False, f"{event_type} metadata must have 'error_code'"

        return True, None

    @classmethod
    def validate_timestamp(cls, timestamp: str) -> tuple[bool, Optional[str]]:
        """Validate ISO8601 timestamp."""
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return True, None
        except (ValueError, TypeError):
            return False, f"Invalid timestamp format: {timestamp}"

    @classmethod
    def get_validation_report(cls, event: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed validation report."""
        is_valid, error = cls.validate(event)

        return {
            "is_valid": is_valid,
            "event_type": event.get("event"),
            "error": error,
            "missing_fields": cls.get_missing_fields(event),
            "type_errors": cls.get_type_errors(event),
        }

    @classmethod
    def get_missing_fields(cls, event: Dict[str, Any]) -> List[str]:
        """Get list of missing required fields."""
        event_type = event.get("event")
        required = cls.REQUIRED_FIELDS.get(event_type, [])
        return [f for f in required if f not in event]

    @classmethod
    def get_type_errors(cls, event: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get list of type mismatches."""
        event_type = event.get("event")
        type_checks = cls.TYPE_CONSTRAINTS.get(event_type, {})
        errors = []

        for field, expected_type in type_checks.items():
            if field in event and not isinstance(event[field], expected_type):
                errors.append({
                    "field": field,
                    "expected": expected_type.__name__,
                    "actual": type(event[field]).__name__,
                })

        return errors
```

### Usage Example

```python
validator = PayloadValidator()

# Validate event
event = {
    "session_id": "sess_001",
    "event": "user.message",
    "content": "Hello",
    "timestamp": "2024-10-18T14:30:00Z"
}

is_valid, error = validator.validate(event)
if is_valid:
    print("✓ Valid event")
else:
    print(f"✗ Invalid event: {error}")

# Get detailed report
report = validator.get_validation_report(event)
print(f"Validation report: {report}")
```

---

## TypeScript Validation

### Runtime Type Guards

```typescript
import { EventProtocol, AnyEvent } from "./event_types";

/**
 * Runtime type validation for events
 */
export class EventValidator {
  /**
   * Validate event payload structure
   */
  static validate(event: unknown): event is AnyEvent {
    if (!this.isObject(event)) return false;
    if (typeof event.event !== "string") return false;

    const eventType = event.event;

    // Validate based on event type
    switch (eventType) {
      case "user.message":
        return this.validateUserMessage(event);
      case "user.response":
        return this.validateUserResponse(event);
      case "plan.completed":
        return this.validatePlanCompleted(event);
      case "agent.tool_call":
        return this.validateAgentToolCall(event);
      case "agent.final_answer":
        return this.validateAgentFinalAnswer(event);
      default:
        return true; // Unknown events are allowed
    }
  }

  private static isObject(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
  }

  private static validateUserMessage(event: unknown): boolean {
    if (!this.isObject(event)) return false;
    return (
      typeof event.session_id === "string" &&
      typeof event.content === "string" &&
      event.content.length > 0
    );
  }

  private static validateUserResponse(event: unknown): boolean {
    if (!this.isObject(event)) return false;
    const content = event.content;
    return (
      typeof event.session_id === "string" &&
      typeof event.step_id === "string" &&
      this.isObject(content) &&
      typeof content.approved === "boolean"
    );
  }

  private static validatePlanCompleted(event: unknown): boolean {
    if (!this.isObject(event)) return false;
    const content = event.content;
    const metadata = event.metadata;

    if (!this.isObject(content) || !Array.isArray(content.tasks)) {
      return false;
    }

    if (!this.isObject(metadata)) {
      return false;
    }

    return metadata.task_count === content.tasks.length;
  }

  private static validateAgentToolCall(event: unknown): boolean {
    if (!this.isObject(event)) return false;
    const content = event.content;

    if (!this.isObject(content)) return false;

    return (
      typeof content.tool_name === "string" &&
      typeof content.tool_description === "string" &&
      this.isObject(content.arguments)
    );
  }

  private static validateAgentFinalAnswer(event: unknown): boolean {
    if (!this.isObject(event)) return false;
    const content = event.content;

    if (!this.isObject(content)) return false;

    const validTypes = ["text", "json", "code", "structured"];
    return (
      typeof content.answer === "string" &&
      validTypes.includes(content.answer_type as string)
    );
  }

  /**
   * Get validation errors for event
   */
  static getErrors(event: unknown): string[] {
    const errors: string[] = [];

    if (!this.isObject(event)) {
      errors.push("Event must be an object");
      return errors;
    }

    if (!event.event) {
      errors.push("Missing 'event' field");
      return errors;
    }

    if (typeof event.event !== "string") {
      errors.push("'event' field must be a string");
    }

    // Add event-specific validation
    const eventType = event.event as string;
    if (eventType === "user.message" && !event.content) {
      errors.push("user.message requires 'content' field");
    }

    return errors;
  }
}
```

### Usage Example

```typescript
import { EventValidator } from "./event_validator";

const event = {
  session_id: "sess_001",
  event: "user.message",
  content: "Hello",
  timestamp: "2024-10-18T14:30:00Z"
};

// Type-safe validation
if (EventValidator.validate(event)) {
  // event is now typed as AnyEvent
  console.log("✓ Valid event");
} else {
  const errors = EventValidator.getErrors(event);
  console.error("✗ Validation errors:", errors);
}
```

---

## Code Generation

### Python Dataclass Generator

```python
"""
Generate Python dataclasses from event specifications.

Usage:
    python generate_models.py --output myagent/ws/event_models.py
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

def generate_user_message():
    @dataclass
    class UserMessage:
        """User message event."""
        session_id: str
        content: str
        event: str = "user.message"
        timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
        metadata: Optional[Dict[str, Any]] = None

        def validate(self) -> tuple[bool, Optional[str]]:
            if not self.session_id:
                return False, "session_id is required"
            if not self.content:
                return False, "content is required"
            if len(self.content) > 10000:
                return False, "content exceeds max length"
            return True, None

    return UserMessage

def generate_plan_completed():
    @dataclass
    class Task:
        """Task in plan."""
        id: str
        title: str
        description: str
        estimated_duration_sec: Optional[int] = None

    @dataclass
    class PlanCompleted:
        """Plan completed event."""
        session_id: str
        step_id: str
        tasks: List[Task]
        task_count: int
        plan_summary: str
        total_estimated_tokens: int
        llm_calls: int
        planning_time_ms: int
        event: str = "plan.completed"
        timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

        def validate(self) -> tuple[bool, Optional[str]]:
            if len(self.tasks) != self.task_count:
                return False, "tasks count mismatch"
            return True, None

    return PlanCompleted, Task
```

### TypeScript Type Generator

```typescript
/**
 * Generate TypeScript interfaces from JSON schema
 *
 * Usage:
 *   npx ts-json-schema-generator --path EVENT_PAYLOADS_DETAILED.md --output event_types.ts
 */

export function generateEventType(eventSpec: {
  name: string;
  content: Record<string, any>;
  metadata: Record<string, any>;
}): string {
  const contentFields = Object.entries(eventSpec.content)
    .map(([name, type]) => `${name}: ${type};`)
    .join("\n  ");

  const metadataFields = Object.entries(eventSpec.metadata)
    .map(([name, type]) => `${name}: ${type};`)
    .join("\n  ");

  return `
export interface ${eventSpec.name} extends EventProtocol {
  event: "${eventSpec.name}";
  content: {
    ${contentFields}
  };
  metadata: {
    ${metadataFields}
  };
}
  `.trim();
}
```

---

## Runtime Validation

### Middleware for WebSocket Server

```python
from typing import Callable, Any

class PayloadValidationMiddleware:
    """Validate payloads on server before processing."""

    def __init__(self, validator: PayloadValidator):
        self.validator = validator

    async def validate_incoming(self, event: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate incoming event."""
        return self.validator.validate(event)

    async def validate_outgoing(self, event: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate outgoing event."""
        return self.validator.validate(event)

    async def process(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate event."""
        is_valid, error = await self.validate_incoming(event)

        if not is_valid:
            return {
                "event": "system.error",
                "content": f"Invalid payload: {error}",
                "metadata": {"error_code": "ERR_VALIDATION_400"}
            }

        return event
```

### TypeScript Event Bus with Validation

```typescript
export class EventBus {
  private handlers: Map<string, EventHandler[]> = new Map();

  /**
   * Emit event with validation
   */
  async emit(event: unknown): Promise<void> {
    // Validate event
    if (!EventValidator.validate(event)) {
      const errors = EventValidator.getErrors(event);
      console.error("Invalid event:", errors);
      return;
    }

    // Get handlers for event type
    const eventType = (event as AnyEvent).event;
    const handlers = this.handlers.get(eventType) || [];

    // Call handlers
    for (const handler of handlers) {
      try {
        await handler(event as AnyEvent);
      } catch (error) {
        console.error(`Handler error for ${eventType}:`, error);
      }
    }
  }

  /**
   * Register event handler
   */
  on<T extends AnyEvent>(
    eventType: T["event"],
    handler: EventHandler<T>
  ): void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler as EventHandler);
  }
}
```

---

## Testing

### Python Unit Tests

```python
import pytest
from myagent.ws.validation import PayloadValidator

class TestPayloadValidation:
    """Test payload validation."""

    def test_valid_user_message(self):
        event = {
            "session_id": "sess_001",
            "event": "user.message",
            "content": "Hello",
        }
        is_valid, error = PayloadValidator.validate(event)
        assert is_valid
        assert error is None

    def test_missing_required_field(self):
        event = {
            "event": "user.message",
            "content": "Hello",
        }
        is_valid, error = PayloadValidator.validate(event)
        assert not is_valid
        assert "session_id" in error

    def test_wrong_type(self):
        event = {
            "session_id": "sess_001",
            "event": "user.message",
            "content": 123,  # Should be string
        }
        is_valid, error = PayloadValidator.validate(event)
        assert not is_valid

    def test_plan_completed_task_count_mismatch(self):
        event = {
            "session_id": "sess_001",
            "step_id": "step_001",
            "event": "plan.completed",
            "content": {"tasks": [{}, {}]},  # 2 tasks
            "metadata": {"task_count": 3},  # But count is 3
        }
        is_valid, error = PayloadValidator.validate(event)
        assert not is_valid
```

### TypeScript Unit Tests

```typescript
import { EventValidator } from "./event_validator";

describe("EventValidator", () => {
  it("should validate user message", () => {
    const event = {
      session_id: "sess_001",
      event: "user.message",
      content: "Hello"
    };
    expect(EventValidator.validate(event)).toBe(true);
  });

  it("should reject missing required field", () => {
    const event = {
      event: "user.message",
      content: "Hello"
    };
    expect(EventValidator.validate(event)).toBe(false);
  });

  it("should reject wrong type", () => {
    const event = {
      session_id: "sess_001",
      event: "user.message",
      content: 123 // Should be string
    };
    expect(EventValidator.validate(event)).toBe(false);
  });
});
```

---

## Best Practices

1. **Always validate before processing** - Validate incoming events immediately
2. **Include detailed error messages** - Help developers debug issues
3. **Use type safety** - Leverage TypeScript for frontend type checking
4. **Test edge cases** - Empty strings, null values, oversized arrays
5. **Document constraints** - Make validation rules explicit
6. **Generate code** - Use tools to keep types in sync
7. **Version types** - Track breaking changes in event schemas
8. **Monitor validation failures** - Log and alert on unexpected payloads

