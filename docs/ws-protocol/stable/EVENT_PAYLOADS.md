# Event Payloads Reference

Complete payload specifications for all WebSocket events.

For field naming, units, and required/optional semantics, see `FIELD_CONVENTIONS.md`.

## User Events

### user.message

User submits a query or task for processing through planning and solving stages.

```javascript
{
  event: "user.message",
  session_id: "sess_xyz789",
  content: "Generate a presentation with 5 slides about AI",
  metadata: {
    source: "web_console" | "api" | "mobile_app",
    client_id: "client_abc123",
    user_id?: "user_xyz",
    tags?: ["urgent", "high_priority"]
  },
  timestamp: "2024-10-18T12:00:00Z"
}
```

**Server Response Flow**: plan.start → agent.thinking → ... → agent.final_answer

---

### user.solve_tasks

Skip planning stage and directly run solver on provided tasks.

```javascript
{
  event: "user.solve_tasks",
  session_id: "sess_xyz789",
  content: {
    tasks: [
      {
        id: "task_1",
        title: "Generate PPT content",
        description: "Write 5 slides of AI overview",
        context?: {...}
      },
      {
        id: "task_2",
        title: "Design slides",
        description: "Create visual layout"
      }
    ]
  },
  metadata: {
    parallelizable: true,
    max_concurrent: 2,
    timeout_seconds: 300
  }
}
```

**Server Response Flow**: solver.start → ... → solver.completed → agent.final_answer

---

### user.response

Response to agent.user_confirm request, approving or rejecting proposed action.

```javascript
{
  event: "user.response",
  session_id: "sess_xyz789",
  step_id: "plan_confirm_1",  // Must match agent.user_confirm step_id
  content: {
    approved: true,  // or false
    feedback?: "Looks good, proceed",
    modified_tasks?: [
      {
        id: "task_1",
        title: "Modified title",
        // Fields to override in original task
      }
    ]
  },
  metadata: {
    response_time_ms: 5000,
    decision_confidence: 0.95
  }
}
```

---

### user.cancel

Cancel the entire current operation.

```javascript
{
  event: "user.cancel",
  session_id: "sess_xyz789",
  content: "User requested cancellation",
  metadata: {
    reason: "takes_too_long" | "wrong_direction" | "user_quit",
    cancel_reason?: "User wants to modify query"
  }
}
```

**Server Response**: agent.interrupted → agent.session_end

---

### user.cancel_task

Cancel a specific task in solver stage.

```javascript
{
  event: "user.cancel_task",
  session_id: "sess_xyz789",
  content: {
    task_id: "task_2"
  },
  metadata: {
    reason: "user_feedback" | "timeout" | "resource_limit"
  }
}
```

---

### user.restart_task

Restart a failed or completed task.

```javascript
{
  event: "user.restart_task",
  session_id: "sess_xyz789",
  content: {
    task_id: "task_1"
  },
  metadata: {
    reason: "retry" | "user_request" | "quality_improvement",
    clear_previous_result: true,
    max_attempts: 3
  }
}
```

---

### user.ack

Client acknowledges receipt of server events.

```javascript
{
  event: "user.ack",
  session_id: "sess_xyz789",
  metadata: {
    last_seq: 50,
    received_count: 8,
    gap_detected: false,
    ack_time_ms: 100
  }
}
```

---

### user.create_session

Initialize new session.

```javascript
{
  event: "user.create_session",
  content: {
    client_id: "browser_abc123",
    client_version: "1.0.0",
    user_id?: "user_xyz",
    preferences?: {
      language: "zh_CN" | "en_US",
      theme: "dark" | "light"
    }
  },
  metadata: {
    source: "web" | "mobile" | "api"
  }
}
```

**Server Response**: agent.session_created

---

### user.reconnect_with_state

Reconnect to existing session after connection loss.

```javascript
{
  event: "user.reconnect_with_state",
  session_id: "sess_xyz789",
  content: {
    last_seq: 42,
    client_state_hash?: "abc123def456"
  },
  metadata: {
    offline_duration_ms: 5000,
    disconnect_reason: "network_issue" | "user_action" | "system_restart"
  }
}
```

**Server Response**: Event replay from buffer OR error.recovery_failed

---

### user.request_state

Request full session state export for manual recovery.

```javascript
{
  event: "user.request_state",
  session_id: "sess_xyz789",
  metadata: {
    include_history: true,
    max_history_events: 100
  }
}
```

**Server Response**: agent.state_exported

---

## Plan Events

### plan.start

Planning stage initiated.

```javascript
{
  event: "plan.start",
  session_id: "sess_xyz789",
  content: {
    question: "Generate a presentation with 5 slides about AI",
    context?: {
      previous_interactions: [...],
      constraints: ["max_slides: 10", "format: pptx"]
    }
  },
  metadata: {
    plan_id: "plan_001",
    model: "gpt-4",
    temperature: 0.7
  },
  show_content: "开始规划：Generate a presentation with 5 slides about AI"
}
```

---

### plan.completed

Planning completed successfully, tasks identified.

```javascript
{
  event: "plan.completed",
  session_id: "sess_xyz789",
  content: {
    tasks: [
      {
        id: "task_1",
        title: "Generate PPT content",
        description: "Create 5 slides with AI overview",
        priority: 1,
        dependencies: [],
        estimated_tokens: 2000,
        estimated_time_seconds: 60
      },
      {
        id: "task_2",
        title: "Format slides",
        description: "Apply styling and layout",
        priority: 2,
        dependencies: ["task_1"],
        estimated_tokens: 800,
        estimated_time_seconds: 30
      },
      {
        id: "task_3",
        title: "Export to PPTX",
        description: "Save in PowerPoint format",
        priority: 3,
        dependencies: ["task_2"],
        estimated_tokens: 400,
        estimated_time_seconds: 10
      }
    ]
  },
  metadata: {
    task_count: 3,
    total_estimated_tokens: 3200,
    total_estimated_time_seconds: 100,
    plan_summary: "Create a 5-slide AI presentation with formatting",
    plan_reasoning: "Break down into content generation, styling, and export",
    llm_calls: 2,
    tokens_used: {input: 1200, output: 800},
    planning_time_ms: 5400
  },
  show_content: "规划完成（3 个任务）：Create a 5-slide AI presentation..."
}
```

---

### plan.cancelled

Planning was cancelled.

```javascript
{
  event: "plan.cancelled",
  session_id: "sess_xyz789",
  content: "Planning cancelled by user",
  metadata: {
    reason: "user_request" | "timeout" | "error",
    partial_plan?: {tasks: [...]},
    cancellation_time_ms: 5000
  },
  show_content: "规划已取消"
}
```

---

### plan.coercion_error

Plan output couldn't be coerced to task list.

```javascript
{
  event: "plan.coercion_error",
  session_id: "sess_xyz789",
  content: "Failed to parse plan output as task list",
  metadata: {
    error_code: "COERCE_001",
    raw_output: "LLM output here...",
    error_message: "Expected list, got string",
    recovery_action: "retry" | "manual_input" | "fallback"
  }
}
```

---

## Solver Events

### solver.start

Solver starting work on a task.

```javascript
{
  event: "solver.start",
  session_id: "sess_xyz789",
  step_id: "solve_task_1",
  content: {
    task: {
      id: "task_1",
      title: "Generate PPT content",
      description: "Create 5 slides with AI overview",
      context: {...}
    }
  },
  metadata: {
    task_id: "task_1",
    solver_id: "solver_default",
    attempt: 1,
    dependencies_completed: true
  },
  show_content: "开始求解：Generate PPT content"
}
```

---

### solver.completed

Solver finished task successfully.

```javascript
{
  event: "solver.completed",
  session_id: "sess_xyz789",
  step_id: "solve_task_1",
  content: {
    task: {
      id: "task_1",
      title: "Generate PPT content"
    },
    result: {
      status: "success",
      output: "Generated 5 slides content...",
      artifacts: [
        {
          type: "text",
          content: "..."
        }
      ]
    }
  },
  metadata: {
    task_id: "task_1",
    execution_time_ms: 45000,
    llm_calls: 3,
    tokens_used: {input: 2000, output: 1500},
    tool_calls: [
      {name: "search_web", calls: 2},
      {name: "format_text", calls: 1}
    ],
    quality_score: 0.92
  },
  show_content: "求解完成：Generate PPT content"
}
```

---

### solver.cancelled

Task was cancelled during solving.

```javascript
{
  event: "solver.cancelled",
  session_id: "sess_xyz789",
  content: {
    task_id: "task_2"
  },
  metadata: {
    reason: "user_request" | "dependency_failed" | "timeout",
    execution_time_ms: 5000,
    partial_result?: {...}
  },
  show_content: "求解已取消"
}
```

---

### solver.restarted

Task restarted after previous failure.

```javascript
{
  event: "solver.restarted",
  session_id: "sess_xyz789",
  content: {
    task_id: "task_1",
    previous_error: "Timeout on first attempt"
  },
  metadata: {
    attempt: 2,
    max_attempts: 3,
    reason: "retry_after_error" | "user_request",
    backoff_ms: 2000
  },
  show_content: "任务已重启（尝试 2/3）"
}
```

---

## Agent Events

### agent.thinking

Agent is reasoning about the problem.

```javascript
{
  event: "agent.thinking",
  session_id: "sess_xyz789",
  content: "Analyzing the task and planning approach...",
  metadata: {
    stage: "planning" | "solving" | "aggregation",
    model: "gpt-4",
    max_tokens: 2000
  },
  show_content: "正在思考…"
}
```

---

### agent.tool_call

Agent is calling a tool.

```javascript
{
  event: "agent.tool_call",
  session_id: "sess_xyz789",
  content: "Calling web search for AI articles",
  metadata: {
    tool_name: "web_search",
    tool_args: {
      query: "latest AI research 2024",
      max_results: 5
    },
    call_id: "call_123"
  },
  show_content: "执行工具调用…"
}
```

---

### agent.tool_result

Tool returned a result.

```javascript
{
  event: "agent.tool_result",
  session_id: "sess_xyz789",
  content: "Search returned 5 articles",
  metadata: {
    tool_name: "web_search",
    call_id: "call_123",
    result: {
      status: "success",
      items: [...],
      count: 5
    },
    execution_time_ms: 1200
  },
  show_content: "工具返回结果"
}
```

---

### agent.partial_answer

Streaming partial response.

```javascript
{
  event: "agent.partial_answer",
  session_id: "sess_xyz789",
  content: "Slide 1: Introduction\nSummary of artificial intelligence...",
  metadata: {
    completion_percent: 33,
    model: "gpt-4",
    tokens_so_far: 500
  },
  show_content: "Slide 1: Introduction\nSummary of artificial intelligence..."
}
```

---

### agent.final_answer

Complete final response.

```javascript
{
  event: "agent.final_answer",
  session_id: "sess_xyz789",
  content: "Complete response text or structured result",
  metadata: {
    type: "text" | "structured" | "file",
    total_tokens: 2500,
    cost_usd: 0.05,
    generation_time_ms: 45000
  },
  show_content: "Complete response text or structured result"
}
```

---

### agent.user_confirm

Request user confirmation on proposed action.

```javascript
{
  event: "agent.user_confirm",
  step_id: "plan_confirm_1",
  session_id: "sess_xyz789",
  content: "请确认规划（3 个任务）",
  metadata: {
    scope: "plan" | "task" | "modification",
    tasks: [
      {id: "task_1", title: "...", description: "..."},
      {id: "task_2", title: "...", description: "..."},
      {id: "task_3", title: "...", description: "..."}
    ],
    task_count: 3,
    plan_summary: "Full plan description",
    options: [
      {value: "approve", label: "Approve and proceed"},
      {value: "modify", label: "Modify tasks"},
      {value: "reject", label: "Reject plan"}
    ],
    timeout_seconds: 300
  },
  show_content: "请确认规划（3 个任务）：内容生成、样式优化、文件导出"
}
```

**Expected Response**: user.response with matching step_id

---

### agent.error

Agent encountered an error.

```javascript
{
  event: "agent.error",
  session_id: "sess_xyz789",
  content: "Failed to process task: Invalid input format",
  metadata: {
    error_code: "AGENT_001",
    error_type: "ValueError",
    stage: "planning",
    operation: "parse_input",
    context: {...},
    recovery_action: "retry" | "escalate" | "skip"
  },
  show_content: "Agent 错误：Invalid input format"
}
```

---

### agent.session_created

Session initialized successfully.

```javascript
{
  event: "agent.session_created",
  session_id: "sess_xyz789",
  content: {
    session_id: "sess_xyz789",
    created_at: "2024-10-18T12:00:00Z"
  },
  metadata: {
    server_version: "1.0.0",
    server_capabilities: ["planning", "solving", "aggregation"],
    session_ttl_hours: 24,
    max_concurrent_tasks: 10,
    heartbeat_interval_seconds: 30
  },
  show_content: "会话创建成功"
}
```

---

### agent.session_end

Session closed.

```javascript
{
  event: "agent.session_end",
  session_id: "sess_xyz789",
  content: "Session ended normally",
  metadata: {
    reason: "user_request" | "timeout" | "error" | "completion",
    duration_seconds: 345,
    total_messages: 12,
    total_tasks: 3,
    completion_status: "success" | "partial" | "failed",
    stats: {
      llm_calls: 15,
      tool_calls: 8,
      tokens_used: {input: 5000, output: 3000}
    }
  },
  show_content: "会话已结束"
}
```

---

### agent.state_exported

Full session state exported for recovery.

```javascript
{
  event: "agent.state_exported",
  session_id: "sess_xyz789",
  metadata: {
    exported_at: "2024-10-18T12:05:00Z",
    valid_until: "2024-10-19T12:05:00Z",
    session_state: {
      stage: "solving",
      plan_context: {
        question: "...",
        tasks: [...],
        status: "in_progress"
      },
      current_task_id: "task_1",
      completed_task_ids: [],
      agent_state: {
        llm_memory: [...],
        tool_state: {...}
      }
    }
  }
}
```

---

## System Events

### system.connected

Connection established successfully.

```javascript
{
  event: "system.connected",
  session_id?: "sess_xyz789",
  content: {
    server_name: "MyAgent WebSocket Server",
    server_version: "1.0.0"
  },
  metadata: {
    server_capabilities: ["planning", "solving", "aggregation"],
    heartbeat_interval_seconds: 30,
    max_session_ttl_hours: 24,
    server_uptime_seconds: 86400
  },
  show_content: "已连接到服务器"
}
```

---

### system.heartbeat

Keep-alive signal.

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
  },
  show_content: "心跳"
}
```

---

### system.notice

Informational message.

```javascript
{
  event: "system.notice",
  session_id: "sess_xyz789",
  content: {
    message: "Server maintenance in 1 hour",
    event_list?: [...]  // For buffered events during reconnect
  },
  metadata: {
    type: "info" | "warning" | "maintenance",
    severity: "low" | "medium" | "high"
  },
  show_content: "服务器将在 1 小时后进行维护"
}
```

---

### system.error

System-level error.

```javascript
{
  event: "system.error",
  session_id: "sess_xyz789",
  content: "Database connection failed",
  metadata: {
    error_code: "SYS_DB_001",
    error_type: "ConnectionError",
    severity: "critical",
    recovery_action: "server_restart_required"
  },
  show_content: "系统错误：数据库连接失败"
}
```

---

## Error Events

### error.validation

Input validation failed.

```javascript
{
  event: "error.validation",
  session_id: "sess_xyz789",
  content: "Task count must be greater than 0",
  metadata: {
    error_code: "ERR_VAL_001",
    recoverable: true,
    recovery_strategy: "escalate_to_user",
    field: "task_count",
    constraint: "> 0",
    provided_value: 0
  }
}
```

---

### error.timeout

Operation timed out.

```javascript
{
  event: "error.timeout",
  session_id: "sess_xyz789",
  content: "Planning timeout after 300 seconds",
  metadata: {
    error_code: "ERR_TIMEOUT_001",
    timeout_seconds: 300,
    elapsed_seconds: 305.2,
    stage: "planning",
    recovery_strategy: "retry",
    attempt: 1,
    max_attempts: 3,
    retry_after_ms: 2000
  }
}
```

---

### error.retry_attempt

Automatic retry in progress.

```javascript
{
  event: "error.retry_attempt",
  session_id: "sess_xyz789",
  metadata: {
    attempt: 1,
    max_attempts: 3,
    retry_after_ms: 2000,
    error_type: "TimeoutError",
    error_message: "Request timeout"
  }
}
```

---

## Aggregate Events

### aggregate.start

Aggregation stage starting.

```javascript
{
  event: "aggregate.start",
  session_id: "sess_xyz789",
  metadata: {
    task_count: 3,
    completed_tasks: 3,
    failed_tasks: 0
  },
  show_content: "开始聚合"
}
```

---

### aggregate.completed

Aggregation completed.

```javascript
{
  event: "aggregate.completed",
  session_id: "sess_xyz789",
  content: {
    final_result: {...}
  },
  metadata: {
    aggregation_time_ms: 5000,
    result_size_bytes: 125000
  },
  show_content: "聚合完成"
}
```

---

## Pipeline Events

### pipeline.completed

Entire plan → solve → aggregate pipeline completed.

```javascript
{
  event: "pipeline.completed",
  session_id: "sess_xyz789",
  metadata: {
    total_time_ms: 180000,
    plan_time_ms: 45000,
    solve_time_ms: 120000,
    aggregate_time_ms: 15000,
    status: "success" | "partial_success" | "failed",
    result_summary: "Generated 5-slide presentation successfully"
  },
  show_content: "流水线完成"
}
```

---

## See Also

- `EVENT_PROTOCOL.md` - Protocol specification
- `ERROR_HANDLING.md` - Error handling strategies
- `RECONNECTION.md` - Connection recovery
