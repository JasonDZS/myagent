# slide_agent_ws

面向“数据库分析 → 生成 PPT”的 Plan & Solve WebSocket 实现。该包在可读性与健壮性上做了清晰的模块划分：

- `slide_types.py`：共享数据结构（例如 `SlideTask`）。
- `tools.py`：规划/求解阶段与编排器交互的工具（提交规划、提交单页草稿等），包含严格的入参校验和规范化。
- `agents.py`：
  - 规划智能体 `Data2PPTPlanAgent`（只输出幻灯片任务，不做重查询）
  - 单页求解智能体 `Data2PPTSlideSolver`（为每一页并行生成草稿）
  - 汇总函数 `compile_presentation`（使用 `GeneratePPTTool` 生成最终 PPT JSON）
- `pipeline.py`：`build_pipeline()` 工厂函数，组装 Plan→Solve 流水线（可配置并发）。
- `server.py`：WebSocket 服务入口（基于 `AgentWebSocketServer`）。

该实现支持：
- 规划确认（允许客户端在求解前审阅/修改任务）。
- 单页求解并行执行，且支持对“单页”的中断与重新生成，不影响其它页的执行。
- 规划阶段的中断与重新规划（限求解开始前）。
- 进度事件中包含 LLM 成本统计，便于前端展示。

> 事件说明与示例：
> - 快速对接版（本目录）：`slide_agent_ws/WS_MESSAGES.md`
> - 详细版（仓库统一文档）：`docs/ws-server/plan_solver_messages.md`

---

## 快速开始

1) 准备数据库环境变量（二选一）：

- SQLite：
  - `DB_TYPE=sqlite`
  - `SQLITE_DATABASE=./data/your.sqlite`
- MySQL：
  - `DB_TYPE=mysql`
  - `MYSQL_HOST=...`
  - `MYSQL_USER=...`
  - `MYSQL_PASSWORD=...`
  - `MYSQL_DATABASE=...`
  - 可选：`MYSQL_PORT`、`MYSQL_CHARSET`

2) 启动 WebSocket 服务：

- 推荐方式：
  - `python -m slide_agent_ws.server --host 0.0.0.0 --port 8086`
- 直接脚本方式（亦支持）：
  - `python slide_agent_ws/server.py --host 0.0.0.0 --port 8086`
- 或示例入口（已切换为使用本包的实现）：
  - `python examples/plan_solve_data2ppt_ws.py --host 0.0.0.0 --port 8086`

3) 客户端连接（示例）：

- 创建会话：
  ```json
  { "event": "user.create_session" }
  ```
- 提交问题：
  ```json
  { "event": "user.message", "session_id": "<sid>", "content": "请生成包含关键指标与趋势的多页PPT" }
  ```

> 可使用 `scripts/ws_print_messages.py` 作为快速测试客户端（支持自动确认计划、可配置取消时间等）。

---

## 环境变量

- 服务控制：
  - `SLIDE_WS_CONCURRENCY`：单页并发数（默认 `5`）。
  - `SLIDE_WS_BROADCAST_TASKS`：`plan.completed` 是否包含完整任务（默认 `true`）。
  - `SLIDE_WS_MAX_RETRY`：失败重试次数（默认 `1`）。
  - `SLIDE_WS_RETRY_DELAY`：重试间隔秒数（默认 `3.0`）。
  - `SLIDE_WS_REQUIRE_CONFIRM`：是否启用规划确认（默认 `true`）。
  - `SLIDE_WS_CONFIRM_TIMEOUT`：规划确认超时（秒，默认 `600`）。

- 数据库配置：见“快速开始”第一步。

---

## WebSocket 事件（摘录）

- 计划/求解/聚合进度：`plan.start`、`plan.completed`、`solver.start`、`solver.completed`、`aggregate.*`、`pipeline.completed`。
- 成本统计：`plan.completed` 和 `solver.completed` 的 `statistics` 字段，以及 `pipeline.completed.statistics` 汇总。
- 规划确认：
  - 请求：`agent.user_confirm`（`metadata.scope=plan`，携带 `tasks`）
  - 回复：`user.response`（`content.confirmed` 布尔值，可选 `tasks` 覆盖）
- 细粒度控制：
  - 取消单页：
    ```json
    { "event": "user.cancel_task", "session_id": "<sid>", "content": { "task_id": 2 } }
    ```
    服务端将推送 `solver.cancelled`，其它页不受影响。
  - 重新生成单页：
    ```json
    { "event": "user.restart_task", "session_id": "<sid>", "content": { "task_id": 2 } }
    ```
    会先取消（如在执行）再重启该页；随后可见新的 `solver.start`/`solver.completed`。
  - 取消规划：
    ```json
    { "event": "user.cancel_plan", "session_id": "<sid>" }
    ```
    若处于规划/确认阶段，将收到 `plan.cancelled`。
  - 重新规划（仅限未进入求解前）：
    ```json
    { "event": "user.replan", "session_id": "<sid>", "content": { "question": "可选新问题" } }
    ```

更多细节、字段说明与事件顺序示例，请参考 `docs/ws-server/plan_solver_messages.md`。

---

## 生成结果

- 聚合阶段会调用 `GeneratePPTTool` 生成 JSON 文件（默认保存到 `./workdir/ppt/presentation.json`）。
- 被取消但未重启的单页不会出现在最终聚合结果中。

---

## 代码结构与可读性说明

- 规划与求解职责分离：规划仅产出结构化任务（`SlideTask`），求解才做数据查询与内容生成。
- 工具输入输出严格校验，错误信息明确；`_normalize_slide_payload` 统一字段与默认值。
- 并发控制与细粒度中断/重启由 `PlanSolverPipeline` 与 `PlanSolverSessionAgent` 提供（位于 `myagent/agent/plan_solver.py`）。
- 复用 `examples/data2ppt.py` 中的数据库与 PPT 工具，避免重复实现。

---

## 进阶使用（编程方式）

```python
from slide_agent_ws.pipeline import build_pipeline
from myagent.agent.plan_solver import create_plan_solver_session_agent

pipeline = build_pipeline()
session_agent = create_plan_solver_session_agent(
    pipeline,
    name="plan_solve_data2ppt_ws",
    require_plan_confirmation=True,
    plan_confirmation_timeout=600,
)
```

将 `session_agent` 注入自定义的 WebSocket 服务器即可获取同等的事件与控制能力。

---

## 已知限制

- `user.replan` 仅在未开始求解时有效；一旦进入求解，暂不支持中途整体重规划（可通过取消会话或等待完成后重发新任务实现）。
- 单页取消/重启只影响对应页，其它页会继续执行；聚合会在“当期活动的页”全部完成后进行。

---

如需在客户端示例脚本中加入“单页取消/重启”的便捷开关，我可以补充 `scripts/ws_print_messages.py` 的相关参数与交互。
