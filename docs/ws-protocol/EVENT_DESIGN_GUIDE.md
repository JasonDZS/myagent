# WebSocket 事件设计指南

## 快速导航

- **新开发者**: 先阅读 [事件类型概览](#事件类型概览)
- **事件定义**: 查看 [完整事件参考](#完整事件参考)
- **集成开发**: 参考 [实施最佳实践](#实施最佳实践)
- **问题排查**: 查看 [常见问题](#常见问题)

---

## 事件类型概览

### 核心概念

WebSocket 事件是前后端之间的通信单元，遵循以下原则：

```
EventProtocol
├── session_id        ← 会话标识
├── connection_id     ← 连接标识
├── step_id           ← 步骤标识（用于请求/响应配对）
├── event             ← 事件类型（命名空间.事件名）
├── timestamp         ← ISO 8601 时间戳
├── content           ← 主要负载（可见信息）
├── metadata          ← 结构化数据（补充信息）
└── show_content      ← 可读显示文本（后端生成）
```

### 事件类型分类

| 分类 | 来源 | 用途 | 命名空间 |
|------|------|------|---------|
| **User Events** | 客户端 | 用户操作和命令 | `user.*` |
| **Agent Events** | 服务端 | 代理执行状态 | `agent.*` |
| **Plan Events** | 服务端 | 规划阶段进展 | `plan.*` |
| **Solver Events** | 服务端 | 求解阶段进展 | `solver.*` |
| **Aggregate Events** | 服务端 | 聚合阶段进展 | `aggregate.*` |
| **System Events** | 服务端 | 系统级消息 | `system.*` |
| **Error Events** | 服务端 | 错误和恢复 | `error.*` |

---

## Content 与 Metadata 的使用规范

### 基本原则

```python
# ✅ GOOD
event = {
    "event": "plan.completed",
    "content": "规划完成（3 个任务）",  # 用户可见的摘要
    "metadata": {                    # 结构化数据
        "tasks": [...],
        "task_count": 3,
        "plan_summary": "..."
    }
}

# ❌ BAD
event = {
    "event": "plan.completed",
    "content": {                     # 不要在 content 中放结构化数据
        "tasks": [...],
        "task_count": 3
    }
}
```

### 事件类型的规范用法

#### User Events

```python
# user.message - 用户输入消息
{
    "event": "user.message",
    "content": "用户输入的文本",
    "metadata": {
        "source": "console" | "api",  # 消息来源
        "context_id": "..."            # 相关上下文
    }
}

# user.create_session - 创建会话
{
    "event": "user.create_session",
    "content": "Create session",  # 或为空
    "metadata": {
        "user_id": "...",           # 可选用户标识
        "config": {...}             # 会话配置
    }
}

# user.ack - 确认收到事件
{
    "event": "user.ack",
    "metadata": {
        "last_seq": 42              # 最后接收的事件序号
    }
}

# user.response - 用户响应（如确认对话）
{
    "event": "user.response",
    "content": "",
    "metadata": {
        "step_id": "confirm_plan_abc123",  # 对应的请求 step_id
        "confirmed": true,
        "tasks": [...]              # 编辑后的任务列表（如有）
    }
}
```

#### Plan Events

```python
# plan.start - 开始规划
{
    "event": "plan.start",
    "content": "开始规划",
    "metadata": {
        "question": "用户的问题文本",
        "step_id": "plan_step_001"
    }
}

# plan.completed - 规划完成
{
    "event": "plan.completed",
    "content": "规划完成（3 个任务）",
    "metadata": {
        "tasks": [
            {"id": 1, "title": "任务 1", "description": "..."},
            {"id": 2, "title": "任务 2", "description": "..."},
            {"id": 3, "title": "任务 3", "description": "..."}
        ],
        "task_count": 3,
        "plan_summary": "执行三个主要步骤：...",
        "duration_ms": 1234
    }
}

# plan.cancelled - 规划取消
{
    "event": "plan.cancelled",
    "content": "规划已取消",
    "metadata": {
        "reason": "user_cancel" | "timeout" | "error",
        "details": "..."
    }
}
```

#### Solver Events

```python
# solver.start - 开始求解
{
    "event": "solver.start",
    "content": "开始求解：任务名称",  # 或简化为空
    "metadata": {
        "task": {
            "id": 1,
            "title": "任务 1",
            "description": "..."
        },
        "task_index": 0,            # 任务序号
        "total_tasks": 3,           # 总任务数
        "step_id": "solver_step_001"
    }
}

# solver.progress - 求解进度（新增）
{
    "event": "solver.progress",
    "content": "求解进度：已处理 2/5 个子步骤",
    "metadata": {
        "current_step": 2,
        "total_steps": 5,
        "percentage": 40,
        "estimated_remaining_ms": 5000
    }
}

# solver.completed - 求解完成
{
    "event": "solver.completed",
    "content": "求解完成：任务名称",
    "metadata": {
        "task": {...},
        "result": "输出结果摘要",
        "success": true,
        "duration_ms": 2345
    }
}

# solver.step_failed - 单个步骤失败（新增）
{
    "event": "solver.step_failed",
    "content": "步骤执行失败",
    "metadata": {
        "step_number": 2,
        "error": "错误信息",
        "recovery_possible": true
    }
}
```

#### Agent Events

```python
# agent.thinking - 代理正在思考
{
    "event": "agent.thinking",
    "content": "",  # 通常为空
    "metadata": {
        "reasoning_type": "planning" | "reflection"
    }
}

# agent.tool_call - 工具调用
{
    "event": "agent.tool_call",
    "content": "调用工具：google_search",
    "metadata": {
        "tool_name": "google_search",
        "arguments": {
            "query": "Python async/await"
        },
        "tool_id": "tool_001"
    }
}

# agent.tool_result - 工具返回结果
{
    "event": "agent.tool_result",
    "content": "工具返回结果",
    "metadata": {
        "tool_name": "google_search",
        "result_preview": "前 100 字的结果摘要",
        "success": true
    }
}

# agent.user_confirm - 请求用户确认
{
    "event": "agent.user_confirm",
    "content": "请确认规划（3 个任务）",
    "metadata": {
        "step_id": "confirm_plan_abc123",  # 重要：用于配对请求/响应
        "scope": "plan" | "tool" | "action",
        "requires_confirmation": true,
        "plan_summary": "执行以下规划：...",
        "tasks": [
            {"id": 1, "title": "任务 1", ...},
            {"id": 2, "title": "任务 2", ...}
        ]
    }
}

# agent.error - 代理执行错误
{
    "event": "agent.error",
    "content": "执行出错：LLM 调用失败",
    "metadata": {
        "error_type": "llm_error" | "tool_error" | "validation_error",
        "error_message": "详细错误信息",
        "context": {...},
        "recoverable": true
    }
}

# agent.session_created - 会话创建
{
    "event": "agent.session_created",
    "content": "会话创建成功",
    "metadata": {
        "session_id": "sess_xyz789",
        "connection_id": "conn_abc123",
        "agent_name": "..."
    }
}
```

#### Error Events（新增）

```python
# error.execution - 执行错误
{
    "event": "error.execution",
    "content": "执行失败：请求超时",
    "metadata": {
        "error_code": "EXECUTION_TIMEOUT",
        "error_message": "Request timeout after 30s",
        "context": {...},
        "recoverable": true,
        "suggested_action": "retry" | "manual_intervention" | "cancel"
    }
}

# error.validation - 验证错误
{
    "event": "error.validation",
    "content": "输入数据验证失败",
    "metadata": {
        "field": "task_description",
        "issue": "字段为空",
        "recoverable": true
    }
}

# error.recovery_started - 开始恢复
{
    "event": "error.recovery_started",
    "content": "开始恢复操作",
    "metadata": {
        "recovery_strategy": "retry" | "fallback" | "escalate",
        "attempt": 1,
        "max_attempts": 3
    }
}

# error.recovery_success - 恢复成功
{
    "event": "error.recovery_success",
    "content": "操作已恢复",
    "metadata": {
        "recovery_strategy": "retry",
        "attempts": 2,
        "duration_ms": 5000
    }
}
```

---

## 实施最佳实践

### 1. 发送事件时的规范

```python
# ✅ 推荐做法
from myagent.ws.events import create_event, PlanEvents

event = create_event(
    PlanEvents.COMPLETED,
    session_id=session.session_id,
    step_id="plan_step_001",
    content="规划完成（3 个任务）",
    metadata={
        "tasks": [...],
        "task_count": 3,
        "plan_summary": "..."
    }
)
await session._send_event(event)

# ❌ 避免
event = create_event(
    "plan.completed",  # 使用字符串而非常量
    content={...}      # 在 content 中放结构化数据
)
```

### 2. 处理用户确认请求

```python
# 服务端：发送确认请求
confirm_step_id = f"confirm_plan_{uuid.uuid4().hex[:8]}"
event = create_event(
    AgentEvents.USER_CONFIRM,
    session_id=session.session_id,
    step_id=confirm_step_id,  # 重要！用于识别这个请求
    metadata={
        "scope": "plan",
        "tasks": tasks,
        "plan_summary": "..."
    }
)
await session._send_event(event)

# 服务端：等待用户响应
response = await session._wait_for_user_response(
    step_id=confirm_step_id,
    timeout=300  # 5 分钟超时
)

# 客户端：发送响应
response_event = create_event(
    UserEvents.RESPONSE,
    session_id=session_id,
    metadata={
        "step_id": confirm_step_id,     # 引用服务端的请求 step_id
        "confirmed": True,
        "tasks": edited_tasks if user_edited else None
    }
)
```

### 3. 错误处理和恢复

```python
# 服务端：捕获错误并发送事件
try:
    result = await solver.execute(task)
except TimeoutError as e:
    event = create_event(
        ErrorEvents.EXECUTION_ERROR,
        session_id=session.session_id,
        content="执行超时",
        metadata={
            "error_type": "timeout",
            "error_message": str(e),
            "recoverable": True,
            "suggested_action": "retry"
        }
    )
    await session._send_event(event)

    # 尝试恢复
    for attempt in range(3):
        event = create_event(
            ErrorEvents.RECOVERY_STARTED,
            metadata={"attempt": attempt + 1, "max_attempts": 3}
        )
        try:
            result = await solver.execute(task)
            event = create_event(ErrorEvents.RECOVERY_SUCCESS)
            break
        except:
            continue
```

### 4. 重连和状态恢复

```python
# 客户端：重连请求
reconnect_event = create_event(
    UserEvents.RECONNECT_WITH_STATE,
    metadata={
        "session_id": stored_session_id,
        "last_seq": client_last_seq,  # 客户端最后接收的事件序号
        "state_checksum": compute_checksum(client_state)
    }
)

# 服务端：处理重连并重放事件
if last_seq < current_seq:
    # 从缓冲区重放遗漏的事件
    for seq in range(last_seq + 1, current_seq + 1):
        await send_buffered_event(seq)
```

### 5. ACK 机制实现

```python
# 客户端：定期发送 ACK
async def send_ack(session_id, last_seq):
    ack_event = create_event(
        UserEvents.ACK,
        session_id=session_id,
        metadata={"last_seq": last_seq}
    )
    await websocket.send(json.dumps(ack_event))

# 服务端：基于 ACK 清理缓冲区
def on_ack_received(connection_id, last_acked_seq):
    buffer = self.buffers[connection_id]
    while buffer and buffer[0][0] <= last_acked_seq:
        buffer.popleft()
```

---

## 完整事件参考

### 事件命名规范

```
事件命名 = [命名空间].[事件名]

示例:
- user.message         ← user 命名空间中的 message 事件
- plan.completed       ← plan 命名空间中的 completed 事件
- agent.tool_call      ← agent 命名空间中的 tool_call 事件
- error.execution      ← error 命名空间中的 execution 事件
```

### 所有事件类型速查表

| 事件 | 来源 | 用途 | 中文显示 |
|------|------|------|---------|
| `user.message` | 客户端 | 用户输入 | "用户消息" |
| `user.create_session` | 客户端 | 创建会话 | "创建会话" |
| `user.response` | 客户端 | 响应确认 | "用户响应" |
| `user.cancel` | 客户端 | 取消操作 | "取消操作" |
| `user.reconnect` | 客户端 | 重新连接 | "重新连接" |
| `user.ack` | 客户端 | 确认收到 | "客户端确认" |
| `plan.start` | 服务端 | 开始规划 | "开始规划" |
| `plan.completed` | 服务端 | 规划完成 | "规划完成" |
| `plan.cancelled` | 服务端 | 规划取消 | "规划已取消" |
| `plan.validation_error` | 服务端 | 验证错误 | "规划验证失败" |
| `solver.start` | 服务端 | 开始求解 | "开始求解" |
| `solver.progress` | 服务端 | 求解进度 | "求解中..." |
| `solver.completed` | 服务端 | 求解完成 | "求解完成" |
| `solver.cancelled` | 服务端 | 求解取消 | "求解已取消" |
| `solver.restarted` | 服务端 | 任务重启 | "任务已重启" |
| `solver.step_failed` | 服务端 | 步骤失败 | "步骤执行失败" |
| `aggregate.start` | 服务端 | 开始聚合 | "开始聚合" |
| `aggregate.completed` | 服务端 | 聚合完成 | "聚合完成" |
| `agent.thinking` | 服务端 | 代理思考 | "正在思考..." |
| `agent.tool_call` | 服务端 | 工具调用 | "执行工具调用..." |
| `agent.tool_result` | 服务端 | 工具结果 | "工具返回结果" |
| `agent.partial_answer` | 服务端 | 部分答案 | "[流式内容]" |
| `agent.final_answer` | 服务端 | 最终答案 | "[最终答案]" |
| `agent.user_confirm` | 服务端 | 请求确认 | "请确认规划..." |
| `agent.error` | 服务端 | 执行错误 | "Agent 错误..." |
| `agent.session_created` | 服务端 | 会话创建 | "会话创建成功" |
| `agent.retry_attempt` | 服务端 | 重试尝试 | "重试中..." |
| `error.execution` | 服务端 | 执行错误 | "执行失败" |
| `error.validation` | 服务端 | 验证错误 | "验证失败" |
| `error.recovery_started` | 服务端 | 恢复开始 | "正在恢复..." |
| `error.recovery_success` | 服务端 | 恢复成功 | "已恢复" |
| `system.connected` | 服务端 | 已连接 | "已连接到服务器" |
| `system.error` | 服务端 | 系统错误 | "系统错误" |
| `system.heartbeat` | 服务端 | 心跳 | "心跳" |

---

## 常见问题

### Q1: 什么时候用 content，什么时候用 metadata？

**A**:
- **content**: 主要信息，用户界面直接显示，通常是字符串摘要
- **metadata**: 结构化补充数据，用于程序处理或高级功能

示例：规划完成事件
- content: "规划完成（3 个任务）" ← 显示给用户
- metadata: { tasks: [...], plan_summary: "..." } ← 程序用来展示任务列表

### Q2: 怎样配对请求/响应事件？

**A**: 使用 `step_id` 字段：
1. 服务端发送请求时，在 metadata 中设置 step_id（如 `confirm_plan_abc123`）
2. 客户端响应时，在 metadata 中引用相同的 step_id
3. 服务端等待时，使用 `_wait_for_user_response(step_id)` 来配对

### Q3: 如何处理事件丢失？

**A**: 使用 seq 编号和 ACK 机制：
1. 每个事件自动分配 seq 号
2. 客户端接收后定期发送 ACK
3. 服务端维护事件缓冲区，根据 ACK 清理
4. 重连时，根据 last_seq 从缓冲区重放

### Q4: 如何实现进度通知？

**A**: 使用新的 `solver.progress` 事件：
```python
for i in range(total_steps):
    await send_event(
        SolverEvents.PROGRESS,
        metadata={
            "current_step": i + 1,
            "total_steps": total_steps,
            "percentage": (i + 1) / total_steps * 100
        }
    )
    # 执行步骤
```

### Q5: 如何优雅地处理用户取消？

**A**:
```python
# 服务端：监听取消事件
@on_event(UserEvents.CANCEL_TASK)
async def handle_cancel(event):
    task_id = event.metadata.get("task_id")
    await cancel_task(task_id)
    # 发送确认事件
    await send_event(
        SolverEvents.CANCELLED,
        metadata={"task_id": task_id, "reason": "user_cancelled"}
    )
```

---

## 相关文档

- 📄 [事件协议详解](./EVENT_PROTOCOL.md)
- 📄 [错误处理指南](./ERROR_HANDLING.md)
- 📄 [重连机制详解](./RECONNECTION.md)
- 📝 [API 参考](./API_REFERENCE.md)
