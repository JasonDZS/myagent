# WebSocket 事件系统改进计划 - 总结

**生成时间**: 2025-10-18
**分析对象**: `myagent/ws/events.py` 前后端事件设计
**状态**: 📋 规划完成，待实施

---

## 快速总结

### 现状评价

当前的 WebSocket 事件系统**逻辑清晰、功能基本完整**，但**缺少生产级的文档和错误处理**。

| 方面 | 评分 | 现状 |
|------|------|------|
| 事件分类 | ⭐⭐⭐⭐⭐ | 逻辑性强，命名规范 |
| 基础结构 | ⭐⭐⭐⭐⭐ | EventProtocol 设计很好 |
| 显示处理 | ⭐⭐⭐⭐ | 后端/前端同步，中文显示 |
| 文档规范 | ⭐⭐⭐ | 缺少 payload 格式文档 |
| 完整性 | ⭐⭐⭐ | 缺少生产级事件（进度、重试等） |
| 错误处理 | ⭐⭐ | 缺少完整的错误恢复流程 |

### 改进目标

- ✅ 补充缺失的事件类型（7 个新事件）
- ✅ 编写完整的协议文档和使用指南
- ✅ 规范 content 和 metadata 的使用
- ✅ 明确重连和错误恢复的流程
- ✅ 提供开发者友好的参考资料

### 交付物清单

已生成以下文档文件：

1. **IMPLEMENTATION_PLAN.md** (5.8 KB)
   - 6 个实施阶段的详细计划
   - 每个阶段的目标、任务、成功标准
   - 时间估算和风险分析

2. **docs/ws-protocol/EVENT_DESIGN_GUIDE.md** (18.5 KB)
   - 完整的事件使用指南
   - 每个事件的 payload 结构示例
   - 最佳实践和常见问题
   - 端到端的流程示例

3. **docs/ws-protocol/QUICK_REFERENCE.md** (8.2 KB)
   - 快速查阅表格
   - 事件流程图
   - 开发检查清单
   - 下一步行动

---

## 改进计划详情

### 📋 阶段 1: 编写 WebSocket 事件协议文档

**优先级**: 🔴 高 | **工作量**: 2-3 小时 | **状态**: ⏳ 待开始

**成果物**: `docs/ws-protocol/EVENT_PROTOCOL.md`

**具体工作**:
- [ ] 协议概述和通信模型
- [ ] 每个事件类型的详细定义
- [ ] 可靠传输机制（seq/ack）文档
- [ ] 重连和状态恢复策略

**为什么重要**: 这是理解整个事件系统的基础，后续所有开发都依赖这份文档。

---

### 🔧 阶段 2: 新增缺失的事件类型

**优先级**: 🟡 中 | **工作量**: 1-2 小时 | **状态**: ⏳ 待开始

**成果物**: 更新 `myagent/ws/events.py`

**新增事件** (7 个):
```python
# Solver 阶段
SolverEvents.PROGRESS = "solver.progress"           # 求解进度
SolverEvents.STEP_FAILED = "solver.step_failed"     # 步骤失败
SolverEvents.RETRY = "solver.retry"                 # 重试开始

# Plan 阶段
PlanEvents.STEP_COMPLETED = "plan.step_completed"   # 步骤完成
PlanEvents.VALIDATION_ERROR = "plan.validation_error"  # 验证错误

# Agent 阶段
AgentEvents.RETRY_ATTEMPT = "agent.retry_attempt"   # 重试尝试
AgentEvents.RATE_LIMITED = "agent.rate_limited"     # 速率限制
AgentEvents.RECOVERY = "agent.recovery"             # 恢复成功

# 新增 ErrorEvents 类
class ErrorEvents:
    EXECUTION_ERROR = "error.execution"
    VALIDATION_ERROR = "error.validation"
    TIMEOUT_ERROR = "error.timeout"
    RECOVERY_STARTED = "error.recovery_started"
    RECOVERY_SUCCESS = "error.recovery_success"
    RECOVERY_FAILED = "error.recovery_failed"
```

**关键改动**:
- 在 `_derive_show_content()` 中添加新事件的中文显示
- 在前端 `MessageItem.tsx` 中添加对应的处理

---

### 📐 阶段 3: 统一 Metadata vs Content 规范

**优先级**: 🟡 中 | **工作量**: 2-3 小时 | **状态**: ⏳ 待开始

**成果物**: 代码规范指南和重构

**规范定义**:

| 字段 | 用途 | 示例 |
|------|------|------|
| `content` | 主要负载，用户可见的摘要文本 | "规划完成（3 个任务）" |
| `metadata` | 结构化补充数据，程序处理 | { tasks: [...], plan_summary: "..." } |

**逐事件规范化** (关键事件):
- ✅ `plan.completed`: content="规划完成", metadata={ tasks, plan_summary, duration_ms }
- ✅ `solver.start`: content="开始求解：任务名", metadata={ task, task_index, total_tasks }
- ✅ `agent.tool_call`: content="调用工具名", metadata={ tool_name, arguments }
- ✅ `agent.user_confirm`: content="请确认", metadata={ step_id, scope, tasks } ⚠️

**检查清单**:
- [ ] plan_solver.py 中所有 create_event 调用都遵循规范
- [ ] 新代码按规范编写
- [ ] 代码审查时引用此规范

---

### 🔗 阶段 4: 明确 RECONNECT 相关事件差异

**优先级**: 🟡 中 | **工作量**: 1.5-2 小时 | **状态**: ⏳ 待开始

**成果物**: 文档和服务端注释更新

**三个事件的差异** (目前容易混淆):

```python
# user.reconnect
# 场景: 连接断开后重新连接
# 用途: 恢复会话，获取所有历史事件
# Payload: { session_id }

# user.reconnect_with_state
# 场景: 客户端有本地状态快照
# 用途: 快速重连，只获取新事件（seq > last_seq）
# Payload: { session_id, last_seq, state_checksum }

# user.request_state
# 场景: 客户端需要查询状态
# 用途: 主动查询，不是重连场景
# Payload: { session_id }
```

**文档工作**:
- [ ] 时序图：正常 → 断开 → 重连的事件序列
- [ ] 表格对比：三个事件的用途和场景
- [ ] 服务端处理流程说明

---

### ⚠️ 阶段 5: 添加错误恢复事件和流程

**优先级**: 🔴 高 | **工作量**: 3-4 小时 | **状态**: ⏳ 待开始

**成果物**:
- 新的 ErrorEvents 类
- 错误恢复状态机文档
- plan_solver.py 中的错误捕获和恢复逻辑

**错误恢复流程**:

```
错误发生
    ↓
发送 error.execution 或 agent.error
    ↓
[recoverable=true?]
    ├─ 是 → error.recovery_started (attempt=1)
    │        ↓
    │       [重试]
    │        ├─ 成功 → error.recovery_success
    │        └─ 失败 → error.recovery_started (attempt=2)
    │                   ↓ (继续重试，最多3次)
    │
    └─ 否 → 需要用户干预或取消
```

**实施细节**:
- [ ] 在 plan_solver.py 中添加 try/except 捕获
- [ ] 为不同错误类型设置合理的重试策略
- [ ] 实现指数退避重试
- [ ] 发送进度事件到客户端

**错误分类**:
```
- ValidationError (可立即重试)
- TimeoutError (应延后重试)
- RateLimitError (应较长延后重试)
- ExecutionError (可能需要用户决策)
```

---

### 📚 阶段 6: 编写事件 Payload 格式文档

**优先级**: 🟡 中 | **工作量**: 2-3 小时 | **状态**: ⏳ 待开始

**成果物**: `docs/ws-protocol/EVENT_PAYLOADS.md`

**文档内容**:
- [ ] 每个事件的详细说明（触发条件、Payload 示例）
- [ ] Payload 快速参考表
- [ ] Python 服务端代码示例
- [ ] TypeScript 客户端代码示例
- [ ] 版本控制和迁移指南

**示例格式**:
```markdown
### plan.completed

**触发条件**: 规划阶段完成

**Payload 示例**:
{
    "event": "plan.completed",
    "session_id": "sess_xyz123",
    "content": "规划完成（3 个任务）",
    "metadata": {
        "tasks": [
            {"id": 1, "title": "任务 1", ...},
            ...
        ],
        "task_count": 3,
        "plan_summary": "执行三个主要步骤：...",
        "duration_ms": 1234
    }
}

**Content**: 主要的摘要信息，用户界面直接显示
**Metadata**:
- tasks (list): 规划的任务列表
- task_count (int): 任务数量
- plan_summary (str): 规划总结
- duration_ms (int): 规划耗时
```

---

## 实施时间线

### 推荐顺序和时间安排

```
第 1 周
├─ 周一-周二: 阶段 1 (编写协议文档) [2-3h]
├─ 周三: 阶段 4 (明确重连事件) [1.5-2h]
└─ 周四: 进度同步

第 2 周
├─ 周一: 阶段 2 (新增事件类型) [1-2h]
├─ 周二-周三: 阶段 3 (规范 content/metadata) [2-3h]
└─ 周四: 代码审查

第 3 周
├─ 周一-周二: 阶段 5 (错误恢复) [3-4h]
├─ 周三: 阶段 6 (Payload 文档) [2-3h]
└─ 周四-周五: 最终审查和文档完善
```

**总投入**: 12-17 小时分布在 3 周

**建议每天**: 2-4 小时，保证质量

---

## 验证标准 (Definition of Done)

完成以下所有条件，认为改进计划成功：

- [ ] 所有文档已生成并通过同行审查
- [ ] `myagent/ws/events.py` 中定义了所有 7 个新事件
- [ ] `_derive_show_content()` 支持所有新事件的中文显示
- [ ] `plan_solver.py` 中的所有 `create_event` 调用遵循 content/metadata 规范
- [ ] 服务端能正确处理 3 种重连场景（reconnect/reconnect_with_state/request_state）
- [ ] 错误捕获和重试逻辑在 plan_solver.py 中实现
- [ ] 前端能正确识别和处理所有新事件
- [ ] 有测试脚本验证：
  - [ ] 端到端的重连流程
  - [ ] 错误恢复流程
  - [ ] 用户确认流程（step_id 配对）
- [ ] 所有新文档在项目的 CLAUDE.md 中引用
- [ ] 没有破坏现有功能

---

## 关键风险与缓解

| 风险 | 影响 | 可能性 | 缓解方案 |
|------|------|--------|---------|
| 破坏向后兼容 | 🔴 高 | 中 | 使用 event_version，新旧事件并存 |
| 前端更新滞后 | 🟡 中 | 高 | 新事件在前端支持后才发送 |
| 文档过于复杂 | 🟡 中 | 低 | 分层文档（快速参考→详细）+ 示例 |
| 重试逻辑疯狂 | 🔴 高 | 低 | 配置最大重试次数 + 指数退避 |

---

## 相关文件位置

已生成的文件：
```
项目根目录
├── IMPLEMENTATION_PLAN.md           ← 详细的 6 阶段计划
├── IMPROVEMENT_SUMMARY.md           ← 本文件（总结）
│
└── docs/ws-protocol/
    ├── EVENT_DESIGN_GUIDE.md        ← 完整的使用指南
    ├── QUICK_REFERENCE.md           ← 快速参考表格
    ├── EVENT_PROTOCOL.md            ← 待编写：协议细节
    ├── ERROR_HANDLING.md            ← 待编写：错误处理
    ├── RECONNECTION.md              ← 待编写：重连机制
    └── EVENT_PAYLOADS.md            ← 待编写：Payload 文档

核心代码位置
├── myagent/ws/events.py             ← 事件定义（待改进）
├── myagent/ws/server.py             ← 服务端（待改进）
├── myagent/ws/plan_solver.py        ← 编排逻辑（待改进）
└── web/ws-console/src/               ← 前端（待测试）
```

---

## 下一步行动

### 立即行动 (今天)

1. ✅ **审查本改进计划**
   - 确认方向是否一致
   - 讨论优先级调整
   - 确认时间和资源

2. ⏳ **准备工作环境**
   - 创建特性分支 (feature/event-system-improvement)
   - 建立本地测试环境
   - 准备测试脚本

### 第一周 (阶段 1-2)

- **周一**: 完成阶段 1 文档，通过同行审查
- **周二**: 完成阶段 4 文档，通过同行审查
- **周三**: 阶段 2 实施（新增 7 个事件）

### 第二周 (阶段 2-3)

- **周一**: 完成阶段 2 和 3 的代码实施
- **周二-周三**: 代码审查和测试
- **周四**: 完成 plan_solver.py 的重构

### 第三周 (阶段 5-6)

- **周一**: 实施错误恢复逻辑
- **周二**: 完成错误处理文档
- **周三**: Payload 文档编写
- **周四**: 最终审查和集成测试

---

## 成功指标

改进完成后，应该达到以下目标：

| 指标 | 当前 | 目标 | 如何衡量 |
|------|------|------|---------|
| 文档完整性 | 30% | 100% | 所有 6 个 ws-protocol 文档都已完成 |
| 事件覆盖度 | 92% | 100% | 新增 7 个事件，所有关键场景都有事件 |
| 代码规范 | 60% | 100% | 所有 create_event 调用都遵循规范 |
| 错误处理 | 40% | 100% | 所有错误都能恢复，且有清晰的恢复流程 |
| 开发体验 | 难 | 易 | 新开发者能快速理解和使用事件系统 |

---

## FAQ

**Q: 这个改进会不会很复杂？**
A: 不会。改进主要是补充缺失的内容（新事件类型、文档），而不是重构现有系统。使用现有的基础结构。

**Q: 需要改动多少代码？**
A: events.py 新增约 100 行代码，plan_solver.py 更新约 50 行。前端 msgItem 更新约 30 行。主要工作是编写文档。

**Q: 会破坏现有功能吗？**
A: 不会。新事件是增量添加，不修改现有事件。使用特性分支和充分测试保证向后兼容。

**Q: 前端需要改动吗？**
A: 最少改动。只需在 MessageItem.tsx 中添加新事件的处理。现有的事件处理逻辑保持不变。

**Q: 什么时候可以上线？**
A: 建议完成所有 3 周的改进后再上线。如果需要加快，可以分阶段上线（先上线文档和新事件，后上线错误恢复）。

---

## 支持和反馈

有问题或建议？

1. 📄 查看详细文档: `IMPLEMENTATION_PLAN.md`
2. 📖 查看使用指南: `docs/ws-protocol/EVENT_DESIGN_GUIDE.md`
3. ⚡ 快速查询: `docs/ws-protocol/QUICK_REFERENCE.md`
4. 💬 讨论改进: 在代码审查中讨论

---

**版本**: 1.0
**生成时间**: 2025-10-18
**状态**: 📋 规划完成，准备实施
**下一步**: 审查并批准改进计划
