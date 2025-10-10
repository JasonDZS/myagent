# Plan & Solver WebSocket 实施计划

## 1. 目标概述
- 将 `create_plan_solver` 管线封装为可被 WebSocket 客户端调用的服务
- 支持实时推送规划、求解和聚合阶段的进度消息
- 保留已有 CLI 示例的可用性，确保管线复用同一套 planner / solver / aggregator

## 2. 现状分析
- `plan_solver.py` 提供 PlanAgent / SolverAgent / PlanSolverPipeline
- `plan_solve_data2ppt.py` 已演示 CLI orchestration
- WebSocket 层（`myagent/ws`）针对单个 `BaseAgent` 实例运行

问题：PlanSolverPipeline 非 BaseAgent，无法直接挂载在 WebSocket 会话上；缺少针对 Plan/Solver 的事件推送策略。

## 3. 设计方案
1. 新增 `PlanSolverSessionAgent`（继承 BaseAgent）
   - 持有 `PlanSolverPipeline`
   - 在 `run(question)` 中调用 pipeline，捕获 `PlanSolveResult`
   - 重写 `run` 或添加 hook，向 WebSocket 发送阶段性事件：
     - `planner.start` / `planner.done`
     - `solver.{id}.start` / `solver.{id}.done`
     - `aggregate.done`
   - 默认 `final_response` = `PlanSolveResult.plan_summary`
2. 提供工厂函数 `create_plan_solver_session_agent(pipeline)` 返回上述 Agent
3. WebSocket server 层（`AgentWebSocketServer`）
   - `agent_factory_func` 返回 `PlanSolverSessionAgent`
   - 维护现有事件协议，必要时扩展 `EventProtocol`
4. 消息格式建议
   ```json
   { "event": "planner.done", "summary": "...", "tasks": [...] }
   ```
   ```json
   { "event": "solver.done", "slide_id": 3, "summary": "..." }
   ```
5. 并发控制
   - 利用 `PlanSolverPipeline(concurrency=N)` 控制 solver 并发
   - 若需中断执行，调用 BaseAgent 现有 cancel / state 检查

## 4. 实现步骤
1. **封装 Agent**
   - 在 `myagent/agent/plan_solver.py` 新增 `PlanSolverSessionAgent`
   - 支持自定义事件名称、消息体模板
2. **事件集成**
   - 在 session agent 中获取当前 WebSocket（`get_ws_session_context()`）
   - 使用 `send_websocket_message()` 发送 JSON
3. **示例/测试**
   - 新建 `examples/plan_solve_data2ppt_ws.py`
     - 构造 pipeline → session agent → WebSocket server
     - Demo: 客户端通过 `CREATE_SESSION` → `MESSAGE(question)` → 接收事件流
4. **文档更新**
   - `docs/plan_and_solve_flow.md` 补充 WebSocket 交互流程
   - README 中提供运行 & 客户端示例

## 5. 时间与资源评估
| 阶段 | 任务 | 预估耗时 |
| --- | --- | --- |
| 1 | 实现 `PlanSolverSessionAgent` | 0.5 天 |
| 2 | WebSocket 集成与事件定义 | 0.5 天 |
| 3 | 编写示例、联调测试 | 0.5 天 |
| 4 | 文档与指南 | 0.5 天 |
| **合计** |  | **2 天左右** |

## 6. 风险与缓解
- **风险**：Plan/Solver 内部调用工具较多，事件过于频繁 → 缓解：设置关键信息级别、必要时打包消息
- **风险**：WebSocket 中断导致任务失联 → 缓解：使用 `StateManager`，允许前端重连后继续获取状态
- **风险**：并发 Solver 的数据库访问冲突 → 缓解：在 SQL 工具里加入节流 / 单连接池配置

## 7. 交付物
- `PlanSolverSessionAgent` 实现及测试
- WebSocket 示例脚本 & 客户端交互说明
- 更新后的架构文档与使用指南

## 8. 实施进展（2025-10-10）
- ✅ `myagent/agent/plan_solver.py` 新增 `PlanSolverSessionAgent` 与进度回调机制，可选 `progress_callback` 触发 `plan.*` / `solver.*` / `aggregate.*` 事件。
- ✅ `create_plan_solver_session_agent` 封装 WebSocket 友好的 agent。
- ✅ `examples/plan_solve_data2ppt_ws.py` 提供 WebSocket 服务器入口，默认事件名为通用的 `plan.start`/`solver.completed`/`aggregate.completed` 等。
- ✅ `PlanSolverPipeline` 支持 `set_progress_callback`，在规划完成、求解开始与完成、聚合阶段推送上下文数据。
- 🔄 后续可视化/客户端示例：待根据前端需求补充。
