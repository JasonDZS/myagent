# 改进计划执行指南

**作者**: Claude Code
**日期**: 2025-10-18
**状态**: 📋 规划完成，准备开始实施

---

## 📚 文档导航

刚才为你生成了完整的改进计划文档。根据你的需要选择阅读：

### 1. 快速概览（5 分钟）
- **文件**: `IMPROVEMENT_SUMMARY.md`
- **内容**: 改进的目标、现状、交付物清单
- **何时读**: 第一次审查计划时

### 2. 详细计划（20 分钟）
- **文件**: `IMPLEMENTATION_PLAN.md`
- **内容**: 6 个阶段的详细任务和成功标准
- **何时读**: 批准计划，准备开始时

### 3. 快速参考（10 分钟）
- **文件**: `docs/ws-protocol/QUICK_REFERENCE.md`
- **内容**: 事件速查表、流程图、开发检查清单
- **何时读**: 开发过程中快速查阅

### 4. 完整指南（30 分钟）
- **文件**: `docs/ws-protocol/EVENT_DESIGN_GUIDE.md`
- **内容**: 事件设计原则、最佳实践、Payload 示例
- **何时读**: 深入理解事件系统

### 5. 流程图详解（15 分钟）
- **文件**: `docs/ws-protocol/FLOWCHARTS.md`
- **内容**: 10 个关键流程的可视化
- **何时读**: 理解复杂流程（如重连、错误恢复）

---

## 🎯 改进计划概览

### 目标

提升 WebSocket 事件系统的规范性、完整性和可维护性。

### 现状

✅ 逻辑清晰
✅ 基础结构合理
✅ 前后端显示同步

❌ 缺少生产级文档
❌ 缺少进度/重试等事件
❌ 错误恢复流程不完整
❌ 没有统一的规范

### 改进成果

| 项目 | 数量 | 状态 |
|------|------|------|
| 新增事件类型 | 7 个 | 待实施 |
| 新增文档 | 4 份 | ✅ 已生成 |
| 代码改动 | ~150 行 | 待实施 |
| 总工作量 | 12-17h | 分 3 周 |

---

## 📋 6 个实施阶段

### 阶段 1: 编写协议文档 🔴 高优先级
**时间**: 2-3 小时
**工作**: 创建 `docs/ws-protocol/EVENT_PROTOCOL.md`

主要内容：
- [ ] WebSocket 通信模型和事件结构
- [ ] 事件命名规范和分类
- [ ] 可靠传输机制（seq/ack）
- [ ] 重连和状态恢复

---

### 阶段 2: 新增事件类型 🟡 中优先级
**时间**: 1-2 小时
**工作**: 更新 `myagent/ws/events.py`

新增 7 个事件：
```
SolverEvents.PROGRESS = "solver.progress"
SolverEvents.STEP_FAILED = "solver.step_failed"
SolverEvents.RETRY = "solver.retry"
PlanEvents.STEP_COMPLETED = "plan.step_completed"
PlanEvents.VALIDATION_ERROR = "plan.validation_error"

# ErrorEvents 新类
class ErrorEvents:
    EXECUTION_ERROR = "error.execution"
    VALIDATION_ERROR = "error.validation"
    RECOVERY_STARTED = "error.recovery_started"
    RECOVERY_SUCCESS = "error.recovery_success"
    RECOVERY_FAILED = "error.recovery_failed"
```

更新 `_derive_show_content()` 支持新事件的中文显示。

---

### 阶段 3: 规范 Content/Metadata 🟡 中优先级
**时间**: 2-3 小时
**工作**: 统一使用规范，更新 plan_solver.py

规范定义：
- **content**: 主要负载，用户可见的摘要
- **metadata**: 结构化补充数据，程序处理

关键事件检查：
- [ ] plan.completed
- [ ] solver.start / solver.progress / solver.completed
- [ ] agent.tool_call / agent.tool_result
- [ ] agent.user_confirm (最关键)
- [ ] error.* 事件

---

### 阶段 4: 明确重连事件 🟡 中优先级
**时间**: 1.5-2 小时
**工作**: 文档澄清 + 服务端注释

三个事件的差异：
```
user.reconnect
  └─ 完整恢复会话，返回所有历史事件

user.reconnect_with_state
  └─ 快速重连，只返回新事件（seq > last_seq）

user.request_state
  └─ 主动查询状态（非重连场景）
```

---

### 阶段 5: 错误恢复流程 🔴 高优先级
**时间**: 3-4 小时
**工作**: 在 plan_solver.py 中实现错误恢复

实现要点：
- [ ] 错误捕获和分类
- [ ] 发送错误事件
- [ ] 实现重试逻辑（指数退避）
- [ ] 重试失败处理
- [ ] 用户决策流程

---

### 阶段 6: Payload 文档 🟡 中优先级
**时间**: 2-3 小时
**工作**: 创建 `docs/ws-protocol/EVENT_PAYLOADS.md`

内容：
- [ ] 每个事件的完整 Payload 示例
- [ ] Payload 快速参考表
- [ ] Python/TypeScript 代码示例
- [ ] 版本控制和迁移指南

---

## ⚡ 快速开始

### 第一步: 审查改进计划

1. 阅读 `IMPROVEMENT_SUMMARY.md` (5 分钟)
2. 审查 `IMPLEMENTATION_PLAN.md` (15 分钟)
3. 讨论和批准方向

### 第二步: 准备开发环境

```bash
# 创建特性分支
git checkout -b feature/event-system-improvement

# 确保本地环境正常
uv sync

# 启动 WebSocket 服务器用于测试
uv run python -m myagent.cli.server server examples/ws_weather_agent.py --port 8889
```

### 第三步: 开始实施

按照推荐顺序：**1 → 4 → 2 → 3 → 5 → 6**

每个阶段：
1. 创建子分支或留下清晰的 TODO 注释
2. 实施变更
3. 自测验证
4. 提交 PR 并引用改进计划

---

## ✅ 验证检查清单

### 完成后验证

- [ ] 所有 6 个文档已创建
- [ ] 7 个新事件已在 events.py 中定义
- [ ] _derive_show_content() 支持新事件
- [ ] plan_solver.py 遵循 content/metadata 规范
- [ ] 错误恢复逻辑已实现
- [ ] 没有破坏现有功能
- [ ] 前端可正确处理新事件
- [ ] 代码审查通过
- [ ] 文档在 CLAUDE.md 中引用

### 测试验证

```bash
# 启动服务器
uv run python -m myagent.cli.server server examples/ws_weather_agent.py --port 8889

# 在另一个终端运行 e2e 测试
uv run python template_agent/scripts/ws_e2e_check.py

# 测试重连
# 1. 断开网络
# 2. 观察事件缓冲
# 3. 恢复连接
# 4. 验证事件重放

# 测试错误恢复
# 1. 注入模拟错误
# 2. 观察错误事件流
# 3. 验证重试逻辑
```

---

## 📁 生成的文件结构

```
myagent/
├── IMPLEMENTATION_PLAN.md           ← 6 阶段详细计划
├── IMPROVEMENT_SUMMARY.md           ← 改进总结
├── GET_STARTED.md                   ← 本文件
│
├── docs/ws-protocol/
│   ├── EVENT_DESIGN_GUIDE.md        ← 完整使用指南 ✅
│   ├── QUICK_REFERENCE.md           ← 快速参考表 ✅
│   ├── FLOWCHARTS.md                ← 流程图详解 ✅
│   ├── EVENT_PROTOCOL.md            ← 协议详解 (待编写)
│   ├── ERROR_HANDLING.md            ← 错误处理 (待编写)
│   ├── RECONNECTION.md              ← 重连机制 (待编写)
│   └── EVENT_PAYLOADS.md            ← Payload 文档 (待编写)
│
├── myagent/ws/
│   ├── events.py                    ← 事件定义 (待改进)
│   ├── server.py                    ← 服务端 (待改进)
│   ├── plan_solver.py               ← 编排逻辑 (待改进)
│   └── ...
│
└── web/ws-console/
    └── src/                         ← 前端 (待改进)
```

---

## 💡 开发建议

### 代码审查检查点

当审查改进代码时，检查：

1. **事件定义**
   - [ ] 使用常量，不用字符串
   - [ ] 添加中文显示支持
   - [ ] 添加文档字符串

2. **事件发送**
   - [ ] 设置 session_id
   - [ ] 请求事件设置 step_id
   - [ ] 使用 metadata，不用 content 放结构数据
   - [ ] 数据 JSON 可序列化

3. **错误处理**
   - [ ] 捕获异常
   - [ ] 分类错误类型
   - [ ] 实现合理的重试策略
   - [ ] 发送错误事件

4. **测试**
   - [ ] 正常流程测试
   - [ ] 错误场景测试
   - [ ] 重连场景测试
   - [ ] 并发任务测试

### 常见问题

**Q: 新增事件会破坏现有功能吗？**
A: 不会。新事件是增量的，可选的。现有代码不变。

**Q: 何时上线这些改进？**
A: 建议完成所有 3 周后整体上线。如急需，可分阶段上线。

**Q: 前端需要大改吗？**
A: 最少改动。在 MessageItem.tsx 中添加新事件处理即可。

**Q: 如何处理已连接的客户端？**
A: 服务端发送新事件时检查前端版本。初期可在文档中标注最小版本要求。

---

## 🚀 下一步

### 立即行动（今天）

1. ✅ 审查改进计划（阅读本文件和总结）
2. ⏳ 讨论和批准方向
3. 💬 提出建议或问题

### 本周行动（第一周）

1. 完成阶段 1: 编写协议文档
2. 完成阶段 4: 明确重连事件
3. 进度同步会议

### 后续行动

按照推荐顺序继续阶段 2-6。

---

## 📞 支持和反馈

有问题？

1. **文档查询**: 查看相应的 docs/ws-protocol/ 文件
2. **快速查阅**: 使用 QUICK_REFERENCE.md
3. **讨论**: 在代码审查或会议中讨论
4. **反馈**: 更新此文件或改进计划

---

## 📊 进度跟踪

### 阶段 1: 编写协议文档
- 状态: ⏳ 待开始
- 进度: 0%
- 预计完成: [待更新]

### 阶段 2: 新增事件类型
- 状态: ⏳ 待开始
- 进度: 0%
- 预计完成: [待更新]

### 阶段 3: 规范 Content/Metadata
- 状态: ⏳ 待开始
- 进度: 0%
- 预计完成: [待更新]

### 阶段 4: 明确重连事件
- 状态: ⏳ 待开始
- 进度: 0%
- 预计完成: [待更新]

### 阶段 5: 错误恢复流程
- 状态: ⏳ 待开始
- 进度: 0%
- 预计完成: [待更新]

### 阶段 6: Payload 文档
- 状态: ⏳ 待开始
- 进度: 0%
- 预计完成: [待更新]

---

## 版本历史

| 版本 | 日期 | 状态 | 备注 |
|------|------|------|------|
| 1.0 | 2025-10-18 | 📋 规划完成 | 初版文档生成 |

---

**祝你实施顺利！** 🎉

有任何问题，参考相关的文档文件或提出讨论。
