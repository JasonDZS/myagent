# Plan & Solve WebSocket Message Guide

该文档面向客户端开发者，说明如何与基于 `PlanSolverSessionAgent` 的 WebSocket 服务交互，并解析服务端推送的各类事件。

## 1. 建立连接与会话

快速启动（示例服务）

- 启动服务：`python examples/plan_solve_data2ppt_ws.py --host 0.0.0.0 --port 8086`
- 客户端连接：`ws://127.0.0.1:8086`（使用具体 IP 连接，`0.0.0.0` 仅用于监听）

1. 连接 `ws://<host>:<port>`。
2. 发送 `user.create_session` 创建会话：
   ```json
   { "event": "user.create_session" }
   ```
3. 等待 `agent.session_created`，记录 `session_id`：
   ```json
   {
     "event": "agent.session_created",
     "session_id": "8202880d-6eab-4a1b-9ac0-0ff023bc6947",
     "content": "Session created successfully",
     "metadata": {
       "agent_name": "plan_solve_data2ppt_ws",
       "connection_id": "..."
     },
     "timestamp": "2025-10-10T18:58:24.905105"
   }
   ```
4. 发送 `user.message` 触发任务执行：
   ```json
   {
     "event": "user.message",
     "session_id": "<session_id>",
     "content": "分析数据并生成2页PPT"
   }
   ```

5. 如需中断执行，可在任意时刻发送 `user.cancel`（详见第 6 节）：
   ```json
   { "event": "user.cancel", "session_id": "<session_id>" }
   ```

会话创建后，服务器会按照以下事件顺序推送进度。客户端应监听所有消息，按 `event` 字段解析。

## 2. 进度事件一览

| 事件 | 说明 | content 结构 |
| --- | --- | --- |
| `plan.start` | 计划阶段开始 | `{ "question": "<原始问题>" }` |
| `plan.completed` | 计划阶段结束 | `{ "tasks": [...], "plan_summary": "<文本>", "statistics": { ... } }` |
| `solver.start` | 单个求解器开始处理某任务 | `{ "task": { ... } }` |
| `solver.completed` | 单个求解器完成 | `{ "task": { ... }, "result": { "output": ..., "summary": ..., "agent_name": ..., "statistics": { ... } } }` |
| `aggregate.start` | 聚合阶段开始 | `{ "context": { ... }, "solver_results": [...] }` |
| `aggregate.completed` | 聚合阶段完成 | `{ "context": { ... }, "solver_results": [...], "output": ... }` |
| `pipeline.completed` | 全流程收尾（全部求解与聚合完成） | `{ "context": { ... }, "solver_results": [...], "aggregate_output": ..., "statistics": { ... } }` |
| `agent.final_answer` | Agent 最终回应 | `"<最终总结文本>"` |
| `agent.session_end` | 会话被关闭（断开连接或显式关闭） | `"Session closed"` |
| `plan.coercion_error` | 计划确认后的任务无法被服务端转换 | `{ "message": "...", "error": "..." }` |

相关通用事件（用于更细粒度调试/可视化）：

- `agent.tool_call` / `agent.tool_result`：工具调用开始与返回（含工具名、状态、可选数据）。
- `agent.user_confirm` / `user.response`：请求用户确认（可能出现在“计划确认”或“工具执行确认”两种场景）。
- `system.heartbeat`：服务端心跳（含活跃会话数量等元信息）。

### 2.1 计划阶段的用户确认（可选）

若服务器端启用了“计划后需要用户确认”（示例服务已启用），在 `plan.completed` 之后会推送一个 `agent.user_confirm` 请求，等待用户确认或编辑任务后继续：

请求示例：

```json
{
  "event": "agent.user_confirm",
  "session_id": "<session_id>",
  "step_id": "confirm_plan_ab12cd34",
  "content": "Confirm plan before solving",
  "metadata": {
    "requires_confirmation": true,
    "scope": "plan",
    "plan_summary": "生成 2 页销售概览幻灯片",
    "tasks": [ ... 与 plan.completed 中的一致 ... ]
  },
  "timestamp": "..."
}
```

客户端可通过 `user.response` 回复，回传 `step_id` 并在 `content` 中给出确认结果与可选的任务修改：

```json
{
  "event": "user.response",
  "session_id": "<session_id>",
  "step_id": "confirm_plan_ab12cd34",
  "content": {
    "confirmed": true,
    "tasks": [
      { "id": 1, "title": "销售概览(修改)", ... },
      { "id": 2, "title": "重点区域分析", ... }
    ]
  }
}
```

注意：

- `confirmed=false` 或超时未确认时，当前执行会被结束（推送 `agent.final_answer`，提示计划被拒绝）。
- 若提供了 `tasks`，服务端将以该任务列表为准进入 `solver.*` 阶段；未提供则使用规划阶段原始 `tasks`。
- 默认确认超时为 300 秒（示例服务设置为 600 秒）。
 - 任务结构要求：需与计划阶段输出的任务结构一致。若服务器的 Planner 支持“任务类型转换”（coerce），将把字典任务转换为内部任务对象（如 SlideTask）；否则不合法的任务结构会导致执行失败。

### 2.2 工具执行的用户确认（可选）

某些工具在执行前会请求用户确认，服务端同样推送 `agent.user_confirm`，但 `metadata.scope` 不再是 `plan`，而包含工具信息：

请求示例：

```json
{
  "event": "agent.user_confirm",
  "session_id": "<session_id>",
  "step_id": "confirm_7b2b3e1a_toolname",
  "content": "Confirm tool execution: fetch_private_data",
  "metadata": {
    "requires_confirmation": true,
    "tool_name": "fetch_private_data",
    "tool_description": "将读取私有数据...",
    "tool_args": { "id": 123 }
  },
  "timestamp": "..."
}
```

客户端使用相同的 `user.response` 回复，确认结果仅要求 `confirmed` 布尔值即可：

```json
{
  "event": "user.response",
  "session_id": "<session_id>",
  "step_id": "confirm_7b2b3e1a_toolname",
  "content": { "confirmed": true }
}
```

> `context` 与 `solver_results` 会随着 `_make_serializable` 自动展开成 JSON 结构，其中 `tasks`、`plan_summary` 等字段与前述事件保持一致。`aggregate_output` 通常包含生成的 PPT JSON 以及工具返回信息。

## 3. 任务与求解结构

### 3.1 任务 (`tasks` / `task`)

由计划阶段生成，默认结构如下（来自 `SlideTask`）：
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

### 3.2 求解结果 (`result`)

`solver.completed` 的 `result` 字段携带求解结果与成本统计：
```json
{
  "output": {
    "id": 1,
    "title": "销售概览",
    "text": "本季度销售额同比增长 12%...",
    "charts": [
      {
        "type": "bar",
        "title": "地区销售额对比",
        "data": [
          { "name": "华东", "value": 540 },
          { "name": "华南", "value": 420 }
        ]
      }
    ]
  },
  "summary": "Slide 1: 销售概览 draft ready.",
  "agent_name": "ppt_slide_solver_1",
  "statistics": {
    "agent": "ppt_slide_solver_1",
    "model": "gpt-4o",
    "total_calls": 2,
    "total_input_tokens": 684,
    "total_output_tokens": 412,
    "total_tokens": 1096,
    "running_totals": {
      "input_tokens": 684,
      "output_tokens": 412,
      "max_input_tokens": null
    },
    "calls": [
      {
        "id": 1,
        "call_type": "ask",
        "timestamp": "2025-05-20T03:50:11.532412",
        "input_tokens": 352,
        "output_tokens": 210,
        "total_tokens": 562,
        "stream": false,
        "response_length": 512,
        "messages_count": 6
      },
      {
        "id": 2,
        "call_type": "ask",
        "timestamp": "2025-05-20T03:50:29.918004",
        "input_tokens": 332,
        "output_tokens": 202,
        "total_tokens": 534,
        "stream": true,
        "response_length": 498,
        "messages_count": 7
      }
    ]
  }
}
```
`output` 通常遵循 `GeneratePPTTool` 的幻灯片格式（`id`、`title`、`text` 和可选 `charts` 等）。`statistics` 源自求解 agent 的 `get_statistics()`，用于实时展示 LLM 调用次数及 token 消耗；若求解器未实现该接口则字段缺失。

### 3.3 规划统计 (`statistics` on `plan.completed`)

`plan.completed` 会包含同样格式的 `statistics` 字段，记录规划阶段使用的模型、请求次数以及累计 token。示例：

```json
{
  "tasks": [...],
  "plan_summary": "生成 2 页销售概览幻灯片",
  "statistics": {
    "agent": "planner",
    "model": "gpt-4o-mini",
    "total_calls": 1,
    "total_input_tokens": 420,
    "total_output_tokens": 188,
    "total_tokens": 608,
    "running_totals": {
      "input_tokens": 420,
      "output_tokens": 188,
      "max_input_tokens": null
    }
  }
}
```

若服务器配置 `broadcast_tasks=False`，`plan.completed` 仍会保留 `plan_summary` 与 `statistics`，便于客户端展示成本信息。

## 4. 全流程统计 (`statistics` on `pipeline.completed`)

`pipeline.completed` 的 `statistics` 字段汇总规划与求解阶段的成本信息，结构如下：

```json
{
  "plan": { ... 与 plan.completed 中一致 ... },
  "solvers": [
    {
      "task": { ... },
      "agent_name": "ppt_slide_solver_1",
      "statistics": { ... 与 solver.completed 中一致 ... }
    }
  ],
  "totals": {
    "total_calls": 5,
    "total_input_tokens": 1580,
    "total_output_tokens": 920,
    "total_tokens": 2500
  },
  "calls": [
    {
      "id": 1,
      "origin": "plan",
      "agent": "planner",
      "call_type": "ask",
      "input_tokens": 420,
      "output_tokens": 188,
      "total_tokens": 608,
      "stream": false,
      "timestamp": "2025-05-20T03:50:11.532412"
    },
    {
      "id": 3,
      "origin": "solver",
      "agent": "ppt_slide_solver_1",
      "call_type": "ask",
      "input_tokens": 352,
      "output_tokens": 210,
      "total_tokens": 562,
      "stream": false,
      "timestamp": "2025-05-20T03:50:30.112093"
    }
  ]
}
```

`totals` 将所有可用统计数据相加，`calls` 则汇总各阶段的调用明细并标记来源与 agent 便于客户端独立展示。若某阶段缺乏统计数据，相应字段会省略。

## 5. 聚合阶段事件

`aggregate.start` / `aggregate.completed` 提供全量上下文，便于客户端需要时自行渲染最终结果：

- `context`: 再次包含 `name`、`question`、`tasks`、`plan_summary` 等元信息。
- `solver_results`: 每个元素对应一次 `solver.completed`，结构与 `result` 相同。
- `output` / `aggregate_output`: 由聚合函数返回，示例：
  ```json
  {
    "slides": [...],
    "ppt_result": {
      "output": "PPT JSON generated successfully!\n\nFile saved to: ./workdir/ppt/presentation.json\n...",
      "system": "PPT generation completed with 2 slides"
    }
  }
  ```

若客户端仅需最终汇总内容，可直接监听 `agent.final_answer` 与 `aggregate.completed`；若需要详细进度，可解析 `plan.*` / `solver.*`。

## 6. 错误与取消

- `agent.error`: Agent 在执行过程中出现异常。
- `agent.timeout`: 超过最大步数或超时。
- `agent.interrupted`: 执行被中断（如收到 `user.cancel`）。
- `system.error`: 协议层错误（如 JSON 解析失败）。

中断（用户取消）的要点：

- 取消方式：发送 `user.cancel`，必须携带要取消的 `session_id`。
  ```json
  { "event": "user.cancel", "session_id": "<session_id>" }
  ```
- 服务端行为：
  - 取消当前执行任务（异步任务被 `cancel()`）。
  - 清理未完成的 tool_calls 记录，重置 Agent 到 `IDLE`，将会话状态置为 `idle`。
  - 推送 `agent.interrupted` 事件，内容示例：
    ```json
    {
      "event": "agent.interrupted",
      "session_id": "<session_id>",
      "content": "Execution cancelled",
      "timestamp": "..."
    }
    ```
- 取消并不会关闭会话，不会触发 `agent.session_end`。同一个 `session_id` 仍可继续发送新的 `user.message` 复用会话。

## 7. 示例事件序列

```
user.create_session
└─ agent.session_created (含 session_id)
user.message (带 session_id)
├─ plan.start
├─ plan.completed
├─ solver.start (task 1)
├─ solver.completed (task 1)
├─ solver.start (task 2)
├─ solver.completed (task 2)
├─ aggregate.start
├─ aggregate.completed
├─ pipeline.completed
├─ agent.final_answer
└─ agent.session_end
  ```
  
客户端按 `event` 订阅处理即可获取完整的执行过程与成果。若服务端启用了并发，多个 `solver.start` / `solver.completed` 可能交错出现，客户端应通过 `content.task.id` 区分。

### 7.1 含取消的序列（示例）

```
user.create_session
└─ agent.session_created (含 session_id)
user.message (带 session_id)
├─ plan.start
├─ plan.completed
user.cancel (带 session_id)
└─ agent.interrupted
```

取消后会话保持 `idle` 可复用，若需要彻底结束会话，可断开连接或让服务器端执行会话关闭（收到 `agent.session_end`）。

### 7.2 含计划确认并编辑任务（示例）

```
user.create_session
└─ agent.session_created (含 session_id)
user.message (带 session_id)
├─ plan.start
├─ plan.completed
├─ agent.user_confirm (scope=plan, 携带 tasks)
user.response (step_id 对应，confirmed=true，含编辑后的 tasks)
├─ solver.start (task 1 - 已按编辑后的任务)
├─ solver.completed (task 1)
├─ solver.start (task 2)
├─ solver.completed (task 2)
├─ aggregate.start
├─ aggregate.completed
├─ pipeline.completed
└─ agent.final_answer
```

若 `confirmed=false` 或超时，计划被拒绝，本次执行结束（收到 `agent.final_answer` 提示），会话仍可复用。

## 8. 细粒度控制：打断/重试（不影响其他任务）

为满足“单页 PPT 可中断/重新生成，且不影响其他页”的需求，服务端扩展了如下用户事件与对应的 Agent 事件：

- 用户事件：
  - `user.cancel_task`：中断指定任务（单页 PPT）
  - `user.restart_task`：重新生成指定任务（若正在生成则先中断再重启）
  - `user.cancel_plan`：中断规划阶段（若处于规划或计划确认中）
  - `user.replan`：在进入求解前请求重新规划（不允许在已开始求解后）

- Agent 事件：
  - `solver.cancelled`：某个任务被中断
  - `solver.restarted`：某个任务被安排重启
  - `plan.cancelled`：规划被中断

使用方式：

- 取消单页任务：
  ```json
  { "event": "user.cancel_task", "session_id": "<session_id>", "content": { "task_id": 2 } }
  ```
  成功后将收到 `system.notice` 确认，随后对应页会推送 `solver.cancelled`；其他页不受影响继续生成。

- 重新生成单页任务：
  ```json
  { "event": "user.restart_task", "session_id": "<session_id>", "content": { "task_id": 2 } }
  ```
  服务端会先取消当前执行（若有），然后重新触发该页处理；会收到 `system.notice` 确认，并在稍后观察到该页新的 `solver.start` 与 `solver.completed`。

- 中断规划：
  ```json
  { "event": "user.cancel_plan", "session_id": "<session_id>" }
  ```
  若此时处于规划/计划确认阶段将推送 `plan.cancelled`，当前流程结束；会话可复用重新发起。

- 重新规划（仅限未开始求解前）：
  ```json
  { "event": "user.replan", "session_id": "<session_id>", "content": { "question": "<可选的新问题>" } }
  ```
  若允许，将立即取消当前规划/确认并重新进入 `plan.start`→`plan.completed` 流程；如已开始求解会返回错误提示。

注意：
- 重新生成单页任务不会阻塞其他任务；聚合阶段会在所有当期活动任务完成后执行。
- 若取消了某些页且未重新生成，这些页将不会出现在后续聚合结果中。

## 9. 客户端辅助工具

内置测试脚本：`scripts/ws_print_messages.py`

- 自动取消：`--cancel-after <seconds>` 在会话建立（及问题发送）后 N 秒发送 `user.cancel`。
- 自动确认计划：`--auto-confirm-plan` 在收到 `agent.user_confirm(scope=plan)` 时自动回 `user.response`，默认仅设置 `{"confirmed": true}`。
- 覆盖计划任务：`--confirm-plan-tasks-file <file>` 指定一个包含任务数组的 JSON 文件，与 `--auto-confirm-plan` 搭配用于替换 `tasks`。
- 交互式确认：默认开启，收到 `agent.user_confirm` 时在终端等待输入（`y`/`n`），可用 `--no-interactive-confirm` 关闭；可用 `--confirm-timeout <seconds>` 设置超时。

示例：

- 启动服务：
  - `python examples/plan_solve_data2ppt_ws.py --host 0.0.0.0 --port 8086`
- 自动同意计划：
  - `python scripts/ws_print_messages.py --host 127.0.0.1 --port 8086 --question "请根据数据生成PPT" --auto-confirm-plan`
- 自动同意并覆盖任务：
  - `python scripts/ws_print_messages.py --host 127.0.0.1 --port 8086 --question "请根据数据生成PPT" --auto-confirm-plan --confirm-plan-tasks-file ./my_tasks.json`
 - 交互式确认并可选覆盖任务（运行时输入）：
   - `python scripts/ws_print_messages.py --host 127.0.0.1 --port 8086 --question "请根据数据生成PPT" --confirm-timeout 60`

注意：示例服务已启用计划确认（`require_plan_confirmation=True`），确认超时 600 秒（`plan_confirmation_timeout=600`）。此外已支持 `user.cancel_task` / `user.restart_task` / `user.cancel_plan` / `user.replan` 事件以进行细粒度控制。
