# WebSocket 事件快速参考

## 改进计划摘要

| 阶段 | 优先级 | 工作量 | 状态 |
|------|--------|--------|------|
| 1️⃣ 编写协议文档 | 🔴 高 | 2-3h | ⏳ 待开始 |
| 2️⃣ 新增事件类型 | 🟡 中 | 1-2h | ⏳ 待开始 |
| 3️⃣ 规范 metadata/content | 🟡 中 | 2-3h | ⏳ 待开始 |
| 4️⃣ 明确重连事件 | 🟡 中 | 1.5-2h | ⏳ 待开始 |
| 5️⃣ 错误恢复流程 | 🔴 高 | 3-4h | ⏳ 待开始 |
| 6️⃣ Payload 文档 | 🟡 中 | 2-3h | ⏳ 待开始 |

**总计**: 12-17 小时 | **建议顺序**: 1 → 4 → 2 → 3 → 5 → 6

---

## 事件类型速查

### 核心事件流

```
用户操作
    ↓
    └─→ user.message / user.solve_tasks
            ↓
        plan.start (规划开始)
            ↓
        plan.completed (规划完成)
            ↓
        agent.user_confirm (请求确认) ← 用户可编辑任务
            ↓
        user.response (用户确认)
            ↓
        solver.start → solver.progress → solver.completed (求解阶段)
            ↓
        aggregate.start → aggregate.completed (聚合)
            ↓
        pipeline.completed (完成)
```

### 事件类型列表

**User Events (客户端发送)**
```
user.message              # 用户输入消息
user.solve_tasks          # 直接提交任务
user.response             # 响应确认（步骤 step_id 必须）
user.cancel               # 取消全部操作
user.cancel_task          # 取消特定任务
user.restart_task         # 重启任务
user.create_session       # 创建新会话
user.reconnect            # 重新连接
user.reconnect_with_state # 带状态重连（last_seq 必须）
user.request_state        # 请求完整状态
user.ack                  # 确认收到（last_seq 必须）
```

**Plan Events (服务端发送)**
```
plan.start                # 开始规划
plan.completed            # 规划完成 ← metadata 包含 tasks
plan.cancelled            # 规划取消
plan.validation_error     # 验证失败（新增）
plan.step_completed       # 步骤完成（新增）
```

**Solver Events (服务端发送)**
```
solver.start              # 开始求解任务
solver.progress           # 求解进度（新增）
solver.completed          # 求解完成
solver.cancelled          # 求解取消
solver.restarted          # 任务重启
solver.step_failed        # 步骤失败（新增）
solver.retry              # 开始重试（新增）
```

**Agent Events (服务端发送)**
```
agent.thinking            # 正在思考
agent.tool_call           # 调用工具
agent.tool_result         # 工具返回
agent.partial_answer      # 流式答案
agent.final_answer        # 最终答案
agent.user_confirm        # 请求确认 ← step_id + metadata 关键
agent.error               # 执行错误
agent.timeout             # 执行超时
agent.interrupted         # 执行中断
agent.session_created     # 会话创建
agent.session_end         # 会话结束
agent.llm_message         # LLM 消息
agent.state_exported      # 状态导出
agent.state_restored      # 状态恢复
agent.retry_attempt       # 重试尝试（新增）
agent.rate_limited        # 速率限制（新增）
agent.recovery            # 恢复成功（新增）
```

**Error Events (新增)**
```
error.execution           # 执行错误
error.validation          # 验证错误
error.timeout             # 超时错误
error.rate_limit          # 速率限制
error.recovery_started    # 恢复开始
error.recovery_success    # 恢复成功
error.recovery_failed     # 恢复失败
```

**System Events (服务端发送)**
```
system.connected          # 连接成功
system.notice             # 系统通知
system.heartbeat          # 心跳
system.error              # 系统错误
```

---

## Content 与 Metadata 对照

| 事件 | Content | Metadata |
|------|---------|----------|
| `plan.start` | "开始规划：问题文本" | `question`, `step_id` |
| `plan.completed` | "规划完成（N 个任务）" | `tasks`, `task_count`, `plan_summary`, `duration_ms` |
| `plan.cancelled` | "规划已取消" | `reason`, `details` |
| `solver.start` | "开始求解：任务名" | `task`, `task_index`, `total_tasks` |
| `solver.progress` | "求解进度：X/Y" | `current_step`, `total_steps`, `percentage` |
| `solver.completed` | "求解完成：任务名" | `task`, `result`, `success`, `duration_ms` |
| `solver.step_failed` | "步骤执行失败" | `step_number`, `error`, `recovery_possible` |
| `agent.thinking` | "" | `reasoning_type` |
| `agent.tool_call` | "调用工具：名称" | `tool_name`, `arguments`, `tool_id` |
| `agent.tool_result` | "工具返回结果" | `tool_name`, `result_preview`, `success` |
| `agent.user_confirm` | "请确认规划（N）" | `step_id`, `scope`, `tasks`, `plan_summary` ⚠️ |
| `agent.error` | "执行错误：描述" | `error_type`, `error_message`, `recoverable` |
| `agent.retry_attempt` | "第 N 次重试" | `attempt`, `max_attempts`, `strategy` |
| `error.recovery_started` | "开始恢复..." | `recovery_strategy`, `attempt`, `max_attempts` |

⚠️ **重要**: `agent.user_confirm` 时 `step_id` 必须在 metadata 中，用于与响应配对

---

## 请求/响应配对流程

### 确认规划示例

**1. 服务端发送确认请求**
```python
import uuid
step_id = f"confirm_plan_{uuid.uuid4().hex[:8]}"

await send_event(
    AgentEvents.USER_CONFIRM,
    session_id=sid,
    step_id=step_id,  # ⚠️ 关键字段
    metadata={
        "scope": "plan",
        "tasks": tasks,
        "plan_summary": "..."
    }
)
```

**2. 客户端发送响应**
```javascript
// 前端收到 agent.user_confirm，用户确认后
const response = {
    event: "user.response",
    session_id: sessionId,
    metadata: {
        step_id: stepId,      // ⚠️ 必须引用服务端的 step_id
        confirmed: true,
        tasks: editedTasks    // 可选：用户编辑后的任务
    }
}
websocket.send(JSON.stringify(response))
```

**3. 服务端接收响应**
```python
response = await session._wait_for_user_response(
    step_id=step_id,
    timeout=300
)
confirmed = response.get("confirmed", False)
edited_tasks = response.get("tasks")
```

---

## 重连流程

### 场景：客户端连接断开 → 重新连接

```
连接状态          客户端                服务端
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
正常连接                 ←──── system.connected

接收事件
seq=1                   ←──── plan.start
seq=2                   ←──── plan.completed
seq=3                   ←──── agent.user_confirm

响应确认           user.ack
                  (last_seq=3)  ────→

                  [网络断开]

重新连接    user.reconnect_with_state
            (session_id,
             last_seq=3,      ────→
             state_checksum)

                              ←──── 重放 seq > 3 的事件
                              ←──── system.connected (重连成功)
```

**关键点**:
- `user.reconnect`: 完整恢复会话，服务端返回所有历史事件
- `user.reconnect_with_state`: 快速重连，只返回 seq > last_seq 的事件
- `user.request_state`: 主动查询状态（非重连场景）

---

## 错误恢复流程

```
正常执行
    ↓
[错误发生]
    ↓
error.execution 或 agent.error
    ↓ (recoverable=true)
error.recovery_started (attempt=1, max_attempts=3)
    ↓
[重试执行]
    ↓
├─ 成功 → error.recovery_success
└─ 失败 → error.recovery_started (attempt=2)
           ↓
           [再次重试]
           ├─ 成功 → error.recovery_success
           └─ 失败 → error.recovery_started (attempt=3)
                      ↓
                      [最后重试]
                      ├─ 成功 → error.recovery_success
                      └─ 失败 → error.recovery_failed
                                 (超过最大重试次数)
                                 ↓
                              需要用户干预或取消
```

---

## 开发检查清单

### 发送事件时

- [ ] 使用事件常量，不用字符串（如 `PlanEvents.COMPLETED`）
- [ ] 设置 `session_id`（如果在会话中）
- [ ] 对于请求事件，设置 `step_id`
- [ ] 将结构化数据放在 `metadata` 中，摘要放在 `content`
- [ ] 调用 `_derive_show_content()` 或手动设置 `show_content`
- [ ] 所有数据都是 JSON 可序列化的（使用 `_make_serializable()`）

### 接收事件时

- [ ] 检查事件类型（`event` 字段）
- [ ] 对于需要响应的事件（如 `user_confirm`），提取 `step_id`
- [ ] 定期发送 `ACK` 以确认收到
- [ ] 处理 `error` 事件并展示给用户
- [ ] 实现重连逻辑（`reconnect_with_state`）

### 测试时

- [ ] 验证 content 和 metadata 的一致性
- [ ] 测试请求/响应配对（step_id 匹配）
- [ ] 测试网络中断后的重连流程
- [ ] 测试错误恢复流程
- [ ] 验证前后端显示一致（show_content）

---

## 文件结构

```
docs/ws-protocol/
├── IMPLEMENTATION_PLAN.md       ← 6个阶段的完整计划
├── EVENT_DESIGN_GUIDE.md        ← 最佳实践和详细说明
├── QUICK_REFERENCE.md           ← 本文件（快速查阅）
├── EVENT_PROTOCOL.md            ← 协议细节（待编写）
├── ERROR_HANDLING.md            ← 错误处理（待编写）
├── RECONNECTION.md              ← 重连机制（待编写）
└── API_REFERENCE.md             ← API 文档（待编写）

myagent/ws/
├── events.py                    ← 核心事件定义
├── server.py                    ← WebSocket 服务端
├── session.py                   ← 会话管理
├── plan_solver.py               ← 规划/求解编排
└── ...
```

---

## 参考命令

### 启动服务器测试改进

```bash
# 启动 WebSocket 服务器
uv run python -m myagent.cli.server server examples/ws_weather_agent.py --port 8889

# 在另一个终端运行测试
uv run python scripts/ws_print_messages.py

# 或使用前端 console
cd web/ws-console && npm run dev
```

### 查看事件流

```bash
# 监听所有 WebSocket 事件
uv run python template_agent/scripts/ws_e2e_check.py
```

---

## 下一步

1. **立即**: 审查本改进计划，确认方向和范围
2. **第一周**: 完成阶段 1 和 4（基础文档）
3. **第二周**: 完成阶段 2 和 3（事件定义和规范）
4. **第三周**: 完成阶段 5 和 6（错误处理和详细文档）

**总投入**: 12-17 小时分布在 3 周内

---

## 联系和讨论

- 文档位置: `/docs/ws-protocol/`
- 计划文件: `IMPLEMENTATION_PLAN.md`
- 问题跟踪: 在代码审查中讨论
- 反馈: 更新此快速参考

---

**版本**: 1.0 | **更新**: 2025-10-18 | **状态**: 📋 规划中
