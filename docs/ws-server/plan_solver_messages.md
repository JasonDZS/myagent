# Plan & Solve WebSocket Message Guide

该文档面向前端/客户端开发者，说明如何与基于 Plan → Solve 流水线（PlanSolverSessionAgent）的 WebSocket 服务交互，涵盖事件流、消息结构以及可选的“直接任务模式”。

---

目录（Contents）

1) 快速开始（连接与会话）
2) 两种执行模式
   - 标准模式：规划 → 求解 → 聚合
   - 直接任务模式：跳过规划，直接按任务求解
3) 事件参考（按阶段）
4) 计划确认（可选，可编辑任务）
5) 细粒度控制（取消/重启单页、取消/重新规划）
6) 数据结构（任务与结果）
7) 统计信息（规划/求解/全流程）
8) 错误与取消
9) 示例时序
10) 可靠性与回放（ACK/seq/event_id）
11) 辅助脚本

---

## 1. 快速开始（连接与会话）

- 启动服务（示例）：`python examples/plan_solve_data2ppt_ws.py --host 0.0.0.0 --port 8086`
- 连接：`ws://<host>:<port>`（客户端请使用具体 IP，`0.0.0.0` 仅用于监听）

创建会话：
```json
{ "event": "user.create_session" }
```
服务端返回：
```json
{
  "event": "agent.session_created",
  "session_id": "<sid>",
  "content": "Session created successfully",
  "metadata": { "agent_name": "plan_solve_data2ppt_ws", "connection_id": "..." },
  "timestamp": "..."
}
```

---

## 2. 两种执行模式

### 2.1 标准模式（规划 → 求解 → 聚合）

触发执行：
```json
{ "event": "user.message", "session_id": "<sid>", "content": "分析数据并生成2页PPT" }
```
事件流（概要）：`plan.start` → `plan.completed` →（可选）`agent.user_confirm`/`user.response` → 多个 `solver.start`/`solver.completed` → `aggregate.start`/`aggregate.completed` → `pipeline.completed` → `agent.final_answer`。

随时中断：
```json
{ "event": "user.cancel", "session_id": "<sid>" }
```

### 2.2 直接任务模式（跳过规划）

当客户端已具备任务（例如用户从 UI 编辑而来），可直接提交任务给求解器，跳过规划：
```json
{
  "event": "user.solve_tasks",
  "session_id": "<sid>",
  "content": {
    "tasks": [ { "id": 1, "title": "销售概览", "objective": "..." } ],
    "question": "可选，问题背景",
    "plan_summary": "可选，计划摘要"
  }
}
```
服务端不会发送 `plan.completed`、`aggregate.*`、`pipeline.completed` 或 `agent.final_answer`。事件顺序为：
- 先发送 `solver.start`（每个任务）
- 再发送 `solver.completed`（每个任务）

---

## 3. 事件参考（按阶段）

- 规划阶段：
  - `plan.start` → `{ "question": "..." }`
  - `plan.completed` → `{ "tasks": [...], "plan_summary": "...", "statistics": [ { ... }, { ... } ] }`
  - `agent.user_confirm`（scope=plan，附带 tasks）
  - 客户端使用 `user.response` 回复确认

- 求解阶段（并行，按任务独立推进）：
  - `solver.start` → `{ "task": { ... } }`
  - `solver.completed` → `{ "task": { ... }, "result": { "output": {...}, "summary": "...", "agent_name": "...", "statistics": [ { ... }, { ... } ] } }`
  - `solver.cancelled`（单页取消）
  - `solver.restarted`（单页重启）

- 聚合阶段：
  - `aggregate.start` → `{ "context": { ... }, "solver_results": [...] }`
  - `aggregate.completed` → `{ "context": { ... }, "solver_results": [...], "output": ... }`
  - `pipeline.completed`（附全流程统计，statistics 为所有调用的列表）
  - `agent.final_answer`

- 通用：
  - `agent.tool_call` / `agent.tool_result`：工具调用过程
  - `agent.llm_message`：可选，发送 LLM 对话记录（需开启环境变量，见其他文档）
  - `agent.error` / `system.error` / `agent.timeout` / `agent.interrupted`
  - `system.notice` / `system.heartbeat`

---

## 4. 计划确认（可选，可编辑任务）

服务端启用计划确认时，`plan.completed` 后会推送：
```json
{
  "event": "agent.user_confirm",
  "session_id": "<sid>",
  "step_id": "confirm_plan_xxxx",
  "content": "Confirm plan before solving",
  "metadata": {
    "requires_confirmation": true,
    "scope": "plan",
    "plan_summary": "...",
    "tasks": [ { "id": 1, "title": "...", "objective": "..." }, ... ]
  }
}
```
客户端用 `user.response` 回复，带相同 `step_id`：
- 沿用任务：`{ "confirmed": true }`
- 覆盖任务：`{ "confirmed": true, "tasks": [ ...与原结构一致... ] }`
- 拒绝：`{ "confirmed": false }`

备注：
- 超时或拒绝会结束本次执行（`agent.final_answer` 给出提示）。
- 服务端会尝试将字典任务“类型转换”（coerce）为内部任务对象（如 SlideTask）；失败将推送 `plan.coercion_error` 并终止本次执行。
- 确认超时默认 300 秒（示例服务 600 秒）。

---

## 5. 细粒度控制（不中断其他任务）

- 取消单页：
  ```json
  { "event": "user.cancel_task", "session_id": "<sid>", "content": { "task_id": 2 } }
  ```
  推送 `system.notice` 确认（`metadata`: `{ "task_id": 2, "action": "cancel_task", "ok": true }`），随后该页 `solver.cancelled`。

- 重新生成单页：
  ```json
  { "event": "user.restart_task", "session_id": "<sid>", "content": { "task_id": 2 } }
  ```
  推送 `system.notice`（`metadata`: `{ "task_id": 2, "action": "restart_task", "ok": true }`），稍后看到该页新的 `solver.start` 与 `solver.completed`。

- 取消规划（规划/确认阶段）：
  ```json
  { "event": "user.cancel_plan", "session_id": "<sid>" }
  ```
  推送 `system.notice`（`metadata`: `{ "action": "cancel_plan", "ok": true }`），以及（由流水线）`plan.cancelled`。

- 重新规划（仅限未开始求解前）：
  ```json
  { "event": "user.replan", "session_id": "<sid>", "content": { "question": "可选" } }
  ```
  若允许，将重新进入 `plan.start` → `plan.completed` → 确认流程。

---

## 6. 数据结构（任务与结果）

- 任务（示例，SlideTask）：
  ```json
  {
    "id": 1,
    "title": "销售概览",
    "objective": "总结本季度销售表现",
    "insights": ["同比增长 12%", "华东地区贡献最大"],
    "query_suggestions": ["SELECT region, sum(amount) ..."],
    "chart_hint": "bar",
    "notes": "聚焦前三大品类"
  }
  ```

- 求解结果（`solver.completed.result`）：
  ```json
  {
    "output": { "id": 1, "title": "销售概览", "text": "...", "charts": [ ... ] },
    "summary": "Slide 1: 销售概览 draft ready.",
    "agent_name": "ppt_slide_solver_1",
    "statistics": [
      { "id": 1, "call_type": "ask", "timestamp": "...", "input_tokens": 320, "output_tokens": 180, "total_tokens": 500, "origin": "solver", "agent": "ppt_slide_solver_1", "metadata": { ... } },
      { "id": 2, "call_type": "ask", "timestamp": "...", "input_tokens": 364, "output_tokens": 232, "total_tokens": 596, "origin": "solver", "agent": "ppt_slide_solver_1", "metadata": { ... } }
    ]
  }
  ```

---

## 7. 统计信息

- 结构变更：`statistics` 统一为 `List<Dict>`，每个元素代表一次具体的 LLM 调用（含 `input_tokens`、`output_tokens`、`total_tokens` 等字段）。
  - `plan.completed.statistics`: 该阶段内的所有调用列表，元素带 `origin: "plan"`、`agent: <planner_name>`。
  - `solver.completed.result.statistics`: 当前任务求解阶段的所有调用列表，元素带 `origin: "solver"`、`agent: <solver_name>`。
  - `pipeline.completed.statistics`: 整个流水线（规划 + 各任务求解）的所有调用列表，按时间顺序汇总。

- 示例（`pipeline.completed.statistics`）：
  ```json
  [
    { "id": 1, "call_type": "ask", "timestamp": "...", "input_tokens": 220, "output_tokens": 120, "total_tokens": 340, "origin": "plan", "agent": "planner_x", "metadata": { ... } },
    { "id": 1, "call_type": "ask", "timestamp": "...", "input_tokens": 320, "output_tokens": 180, "total_tokens": 500, "origin": "solver", "agent": "solver_a", "metadata": { ... } }
  ]
  ```

- 说明：
  - 若某阶段没有调用则可省略 `statistics` 字段。
  - 当 `broadcast_tasks=false` 时，`plan.completed` 仍包含 `plan_summary` 与 `statistics`（若有）。

---

## 8. 错误与取消

- `agent.error`：执行异常
- `agent.timeout`：超时或步数耗尽
- `agent.interrupted`：收到 `user.cancel` 后中断
- `system.error`：协议层错误（如 JSON 解析失败）

中断（用户取消）：
```json
{ "event": "user.cancel", "session_id": "<sid>" }
```
服务端会取消当前执行、清理未完成 tool_calls、重置 Agent 状态，推送 `agent.interrupted`。会话不关闭，可复用。

---

## 9. 示例时序

标准模式：
```
user.create_session
└─ agent.session_created
user.message
├─ plan.start
├─ plan.completed
├─ agent.user_confirm (scope=plan)
user.response (confirmed=true)
├─ solver.start (task 1)
├─ solver.completed (task 1)
├─ solver.start (task 2)
├─ solver.completed (task 2)
├─ aggregate.start
├─ aggregate.completed
├─ pipeline.completed
└─ agent.final_answer
```

直接任务模式：
```
user.create_session
└─ agent.session_created
user.solve_tasks (含 tasks)
├─ solver.start (task 1)
├─ solver.completed (task 1)
├─ solver.start (task 2)
├─ solver.completed (task 2)
```

---

## 10. 可靠性与回放（ACK/seq/event_id）

- 服务器为每条下行事件注入：
  - `seq`：连接内单调递增序号
  - `event_id`：`<connectionId>-<seq>` 唯一标识
- 客户端建议：
  - 按节流策略发送 ACK：`{ "event": "user.ack", "content": { "last_event_id": "<cid>-<seq>" } }`
    - 若无法持有 `last_event_id`，可用 `{ "last_seq": <number> }`
  - 断线重连使用 `user.reconnect_with_state`，并在 `content` 中携带 `last_event_id`（推荐）或 `last_seq`；服务端将基于会话级缓冲进行“差量回放”（单次最多 200 条）
- 简要示例（浏览器）：
```javascript
let lastEventId = null, lastSeq = 0;
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (typeof m.event_id === 'string') lastEventId = m.event_id;
  if (typeof m.seq === 'number') lastSeq = m.seq;
  // ...
};
setInterval(() => {
  if (ws.readyState !== WebSocket.OPEN) return;
  const content = lastEventId ? { last_event_id: lastEventId } : { last_seq: lastSeq };
  ws.send(JSON.stringify({ event: 'user.ack', content }));
}, 200);
```

---

## 11. 辅助脚本

- 终端打印与交互脚本：`scripts/ws_print_messages.py`
  - 支持：
    - `--cancel-after <sec>`：在会话建立/提问后 N 秒自动发送 `user.cancel`
    - 计划确认自动回复/交互确认（可附带覆盖 tasks）
    - 直接任务模式：`user.solve_tasks`（从文件或命令行提供 tasks）
  - 适合快速验证事件流与交互逻辑
