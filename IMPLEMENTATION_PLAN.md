# WebSocket 事件系统改进计划

## 概述

基于对 `myagent/ws/events.py` 的分析，本计划用于完善前后端交互的事件设计，提高系统的规范性、完整性和可维护性。

---

## 阶段 1：编写 WebSocket 事件协议文档

**目标**: 创建完整的事件协议文档，定义所有事件的 payload 格式和通信流程

**成果物**: `docs/ws-protocol/EVENT_PROTOCOL.md`

**具体任务**:

1. **事件协议概述**
   - WebSocket 消息结构（EventProtocol）
   - 事件分类和命名规范
   - 可靠传输机制（seq/ack）

2. **用户事件文档**
   - `user.message` - 用户消息输入
   - `user.solve_tasks` - 直接任务提交
   - `user.response` - 用户响应（用于确认对话）
   - `user.cancel` / `user.cancel_task` / `user.cancel_plan` - 取消操作
   - `user.create_session` - 会话创建
   - `user.reconnect` / `user.reconnect_with_state` - 重连
   - `user.request_state` - 请求状态
   - `user.ack` - 确认收到

3. **服务端事件文档**
   - Agent Events（agent.*）- 代理执行事件
   - Plan Events（plan.*）- 规划阶段事件
   - Solver Events（solver.*）- 求解阶段事件
   - Aggregate Events（aggregate.*）- 聚合阶段事件
   - System Events（system.*）- 系统消息

4. **重连和恢复策略**
   - seq 编号机制
   - 事件缓冲和重放逻辑
   - 状态一致性保证

**成功标准**:
- [ ] 文档包含所有事件类型的 payload 示例
- [ ] 文档说明每个事件的触发条件和预期客户端行为
- [ ] 文档包含端到端的 user flow 示例（如确认规划流程）
- [ ] 没有歧义或遗漏的事件定义

**预计工作量**: 2-3 小时

---

## 阶段 2：新增缺失的事件类型

**目标**: 补充生产环境必需的事件，完善错误处理和进度反馈

**成果物**: 更新后的 `myagent/ws/events.py`

**具体任务**:

1. **SolverEvents 新增事件**
   ```python
   PROGRESS = "solver.progress"      # 求解中的进度更新
   STEP_FAILED = "solver.step_failed" # 单个步骤失败
   RETRY = "solver.retry"             # 重试开始
   ```

2. **PlanEvents 新增事件**
   ```python
   STEP_COMPLETED = "plan.step_completed"  # 规划步骤完成
   VALIDATION_ERROR = "plan.validation_error"  # 验证错误
   ```

3. **AgentEvents 新增事件**
   ```python
   RATE_LIMITED = "agent.rate_limited"  # 遇到速率限制
   RETRY_ATTEMPT = "agent.retry_attempt"  # 重试尝试
   RECOVERY = "agent.recovery"  # 从错误恢复
   ```

4. **ErrorEvents 新类**
   ```python
   class ErrorEvents:
       """错误和恢复事件"""
       EXECUTION_ERROR = "error.execution"
       VALIDATION_ERROR = "error.validation"
       TIMEOUT_ERROR = "error.timeout"
       RECOVERY_STARTED = "error.recovery_started"
       RECOVERY_SUCCESS = "error.recovery_success"
       RECOVERY_FAILED = "error.recovery_failed"
   ```

5. **更新 _derive_show_content() 函数**
   - 为新事件类型添加中文显示文本
   - 保持前后端显示一致性

**成功标准**:
- [ ] 所有新事件在 events.py 中定义
- [ ] _derive_show_content() 支持新事件的中文显示
- [ ] 新事件有明确的触发场景说明
- [ ] 向后兼容，不破坏现有事件

**预计工作量**: 1-2 小时

---

## 阶段 3：统一 Metadata vs Content 的使用规范

**目标**: 明确定义何时使用 content 和 metadata，提高代码一致性

**成果物**:
- 更新 `myagent/ws/events.py` 的文档字符串
- 代码规范指南

**具体任务**:

1. **定义使用规范**
   ```
   content:
     - 主要负载或用户可见的文本信息
     - 示例：最终答案、用户界面显示的信息

   metadata:
     - 结构化、可选的补充数据
     - 示例：task 对象、步骤序号、进度百分比
   ```

2. **逐事件类型规范化**
   - `plan.completed`:
     - content: "规划完成"（摘要文本）
     - metadata: { tasks: [], plan_summary: "", ... }

   - `solver.start`:
     - content: "" (保留为空或简要信息)
     - metadata: { task: {...}, step_id: ... }

   - `agent.tool_call`:
     - content: "工具名" + "参数摘要"
     - metadata: { tool_name: "", args: {...}, tool_id: "" }

3. **添加代码注释**
   - 在 EventProtocol 类中明确说明字段用途
   - 在各 Events 类中提供使用示例

4. **更新 plan_solver.py**
   - 检查所有 create_event 调用
   - 确保遵循新的 content/metadata 规范

**成功标准**:
- [ ] 规范文档清晰明确
- [ ] 所有新代码遵循规范
- [ ] 现有代码逐步迁移到新规范
- [ ] 代码审查中可引用此规范

**预计工作量**: 2-3 小时

---

## 阶段 4：明确 RECONNECT 相关事件的差异

**目标**: 清晰定义三个重连事件的用途和使用场景

**成果物**:
- 更新 `myagent/ws/events.py` 中的文档
- 更新 `myagent/ws/server.py` 中的重连处理逻辑文档

**具体任务**:

1. **定义三个事件的差异**
   ```python
   # user.reconnect
   # 场景：客户端连接断开后重新连接
   # 用途：恢复会话，服务端应返回会话状态和事件日志
   # payload: { session_id: str }

   # user.reconnect_with_state
   # 场景：客户端有完整的本地状态快照
   # 用途：加速重连，避免完整的状态传输
   # payload: { session_id: str, last_seq: int, state_checksum: str }

   # user.request_state
   # 场景：客户端需要完整的当前会话状态
   # 用途：主动查询而不是重连场景
   # payload: { session_id: str }
   ```

2. **更新服务端处理逻辑**
   - 在 server.py 中添加详细注释
   - 说明每个事件的处理流程

3. **添加时序图文档**
   - 说明正常连接 → 断开 → 重连的事件序列
   - 说明异常场景（如超时后的状态恢复）

**成功标准**:
- [ ] 三个事件的用途和差异明确
- [ ] 有代码注释和文档说明
- [ ] 有时序图示例
- [ ] 服务端处理逻辑对应清晰

**预计工作量**: 1.5-2 小时

---

## 阶段 5：添加错误恢复事件和流程

**目标**: 设计完整的错误处理和恢复流程，提高系统可靠性

**成果物**:
- 新的 ErrorEvents 类
- 错误恢复状态机文档
- 更新后的 plan_solver.py 和 server.py

**具体任务**:

1. **设计错误分类**
   ```
   - ValidationError: 数据验证失败（可立即重试）
   - ExecutionError: 执行失败（可能需要用户干预）
   - TimeoutError: 超时（应重试）
   - RateLimitError: 速率限制（应延后重试）
   ```

2. **实现错误事件发送**
   - 在 plan_solver.py 中添加错误捕获
   - 发送相应的 ErrorEvent
   - 记录错误上下文在 metadata 中

3. **实现客户端错误恢复流程**
   ```
   错误发生 → agent.error 事件 + error.execution
   ↓
   用户决策（自动重试、手动操作、取消）
   ↓
   客户端发送 user.retry_task 或 user.cancel
   ↓
   服务端执行恢复或清理
   ```

4. **添加重试配置**
   - 可配置的重试策略（指数退避）
   - 可配置的最大重试次数
   - 超时和速率限制的特殊处理

**成功标准**:
- [ ] ErrorEvents 类已定义
- [ ] plan_solver.py 中有错误捕获和事件发送
- [ ] 错误恢复流程文档清晰
- [ ] 有测试脚本验证错误恢复流程

**预计工作量**: 3-4 小时

---

## 阶段 6：编写事件 Payload 格式文档

**目标**: 创建详细的 payload 格式参考，作为开发者指南

**成果物**: `docs/ws-protocol/EVENT_PAYLOADS.md`

**具体任务**:

1. **为每个事件类编写详细文档**
   - 事件类型名称
   - 触发条件
   - Payload 示例（JSON）
   - Content 和 metadata 的具体字段
   - 特殊处理说明

2. **创建 Payload 快速参考表**
   ```markdown
   | 事件 | Content | Metadata 字段 | 触发者 |
   |------|---------|----------------|--------|
   | plan.start | question | - | server |
   | plan.completed | summary | tasks, task_count | server |
   | solver.start | "" | task, step_id | server |
   ```

3. **添加代码示例**
   - Python 服务端：如何创建和发送事件
   - TypeScript 客户端：如何解析和处理事件
   - 错误处理示例

4. **添加版本控制说明**
   - 事件协议版本号
   - 向后兼容性说明
   - 废弃事件类型的迁移指南

**成功标准**:
- [ ] 所有事件类型都有详细文档
- [ ] 有完整的 payload 示例
- [ ] 有代码示例
- [ ] 文档易于搜索和理解

**预计工作量**: 2-3 小时

---

## 总体时间线

| 阶段 | 任务 | 预计工时 | 优先级 |
|------|------|----------|--------|
| 1 | 编写协议文档 | 2-3h | 🔴 高 |
| 2 | 新增事件类型 | 1-2h | 🟡 中 |
| 3 | 规范 metadata/content | 2-3h | 🟡 中 |
| 4 | 明确重连事件 | 1.5-2h | 🟡 中 |
| 5 | 错误恢复流程 | 3-4h | 🔴 高 |
| 6 | Payload 文档 | 2-3h | 🟡 中 |

**总计**: 12-17 小时

**建议执行顺序**: 1 → 4 → 2 → 3 → 5 → 6
- 先完成基础文档和澄清（1、4）
- 再增加事件类型（2）
- 然后规范格式（3）
- 最后补充错误处理（5）和详细文档（6）

---

## 验证标准（Definition of Done）

完成以下条件后，认为改进计划成功：

- [ ] 所有新文档已创建并通过审查
- [ ] 所有新事件类型已在 events.py 中定义
- [ ] _derive_show_content() 支持所有新事件类型
- [ ] plan_solver.py 中的 create_event 调用遵循新规范
- [ ] 没有破坏现有功能
- [ ] 前端可以正确识别和处理所有事件
- [ ] 有测试用例验证端到端的重连和错误恢复流程
- [ ] 文档在项目的 CLAUDE.md 中引用

---

## 风险和缓解方案

| 风险 | 影响 | 缓解方案 |
|------|------|---------|
| 破坏向后兼容性 | 🔴 高 | 使用 event_version 字段，新旧事件并存过渡 |
| 前端更新滞后 | 🟡 中 | 新事件仅在前端支持后发送 |
| 文档过于复杂 | 🟡 中 | 使用清晰的表格和示例，提供快速参考 |

---

## 后续优化

- 添加事件通过工具自动生成 TypeScript 类型定义
- 实现事件验证中间件（Pydantic）
- 创建事件监控和性能分析工具
- 支持事件过滤和订阅机制
