# Plan & Solve WebSocket Message Guide

该文档面向客户端开发者，说明如何与基于 `PlanSolverSessionAgent` 的 WebSocket 服务交互，并解析服务端推送的各类事件。

## 1. 建立连接与会话

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
| `agent.session_end` | 会话结束（可能因取消或正常结束产生） | `"Session closed"` |

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
- `agent.interrupted`: 服务器端取消执行（如收到 `user.cancel`）。
- `system.error`: 协议层错误（如 JSON 解析失败）。

客户端可在收到这些事件时提示用户或尝试重新发起会话。

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
