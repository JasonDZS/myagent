# MyAgent WebSocket 管理系统文档

欢迎来到 MyAgent WebSocket 管理系统文档中心。本系统提供了完整的多智能体服务管理解决方案，支持服务注册、智能路由、健康监控和负载均衡等企业级功能。

## 📚 文档导航

### 🚀 快速开始

#### [CLI 使用指南](./cli-usage.md) ⭐ 推荐首先阅读
完整的命令行工具使用指南，包含所有命令的详细说明和实用示例。

**适合人群**: 需要快速上手的开发者

**内容包括**:
- 安装和配置
- 所有 CLI 命令详解
- 服务管理命令（register, start, stop, restart, list, status, stats）
- 服务器命令（daemon, api, proxy）
- 完整工作流示例
- 常见问题解答

---

#### [使用指南](./USAGE_GUIDE.md)
系统使用的实战指南，从安装到部署的完整流程。

**适合人群**: 初次接触系统的用户

**内容包括**:
- 系统概览
- 快速开始
- 基础使用示例
- 服务管理实践
- 客户端连接示例

---

#### [完整管理指南](./manager-guide_zh.md) 📖 详细文档
系统最完整的中文管理指南，涵盖所有核心功能和高级特性。

**适合人群**: 系统管理员和高级用户

**内容包括**:
- 系统概述和架构
- 核心组件详解（AgentManager, ServiceRegistry, ConnectionRouter, HealthMonitor）
- 服务管理完整流程
- 连接路由和策略配置
- 健康监控和自动恢复
- HTTP API 详细文档
- 命令行工具使用
- 最佳实践
- 故障排除指南

---

### 🏗️ 架构设计

#### [系统架构](./architecture.md)
WebSocket 管理系统的整体架构设计文档。

**内容包括**:
- 系统概述
- 核心组件设计
- 数据流程
- 技术选型
- 扩展性设计

---

#### [架构总结](./architecture-summary.md)
架构设计的简明总结，快速了解系统设计要点。

**内容包括**:
- 核心组件概览
- 关键设计决策
- 技术亮点

---

### 📊 技术文档

#### [数据模型](./data-models.md)
系统所有数据模型的详细定义。

**内容包括**:
- Service (服务模型)
- ServiceConfig (服务配置)
- ServiceStats (服务统计)
- RoutingRule (路由规则)
- HealthCheck (健康检查)
- Connection (连接信息)

---

#### [API 设计](./api-design.md)
HTTP API 的完整设计文档。

**内容包括**:
- RESTful API 端点
- 请求/响应格式
- 错误处理
- API 示例

---

#### [路由策略](./routing-strategies.md)
智能路由系统的策略详解。

**内容包括**:
- 轮询（Round Robin）
- 最少连接（Least Connections）
- 加权随机（Weighted Random）
- 哈希路由（Hash Based）
- 标签路由（Tag Based）
- 自定义规则引擎

---

### 📋 开发文档

#### [实现计划](./implementation-plan.md)
系统的实现计划和开发路线图。

**内容包括**:
- 开发阶段划分
- 功能优先级
- 实现进度
- 技术债务

---

#### [部署架构](./deployment-architecture.md)
生产环境部署架构指南。

**内容包括**:
- 部署拓扑
- 高可用配置
- 性能优化
- 监控告警

---

## 🎯 按场景选择文档

### 场景 1: 我想快速上手使用 CLI
→ [CLI 使用指南](./cli-usage.md)

**快速示例**:
```bash
# 安装依赖
uv sync

# 注册并启动服务
myagent-manager register my_agent examples/weather_agent.py --auto-start

# 查看服务列表
myagent-manager list

# 启动 API 服务器
myagent-manager api --port 8000
```

---

### 场景 2: 我需要了解系统架构
→ [系统架构](./architecture.md) → [架构总结](./architecture-summary.md)

---

### 场景 3: 我要部署生产环境
→ [完整管理指南](./manager-guide_zh.md) → [部署架构](./deployment-architecture.md)

---

### 场景 4: 我想开发集成功能
→ [API 设计](./api-design.md) → [数据模型](./data-models.md)

---

### 场景 5: 我需要配置路由策略
→ [路由策略](./routing-strategies.md) → [完整管理指南 - 连接路由](./manager-guide_zh.md#连接路由)

---

## 🔧 核心功能概览

### 服务管理
- ✅ 多服务注册和管理
- ✅ 服务启动/停止/重启
- ✅ 端口自动分配
- ✅ 服务标签和分组
- ✅ 配置持久化（SQLite）

### 智能路由
- ✅ 5种路由策略
- ✅ 自定义路由规则
- ✅ 条件匹配引擎
- ✅ 会话亲和性
- ✅ 负载均衡

### 健康监控
- ✅ 自动健康检查
- ✅ 服务故障恢复
- ✅ 自动重启机制
- ✅ 性能指标收集
- ✅ 健康历史记录

### 管理工具
- ✅ 命令行工具（myagent-manager）
- ✅ HTTP API 服务器
- ✅ WebSocket 代理服务器
- ✅ 守护进程模式
- ✅ 在线 API 文档

---

## 📖 文档阅读路径

### 新手路径
1. [CLI 使用指南](./cli-usage.md) - 快速上手
2. [使用指南](./USAGE_GUIDE.md) - 基础实践
3. [完整管理指南](./manager-guide_zh.md) - 深入学习

### 架构师路径
1. [架构总结](./architecture-summary.md) - 快速了解
2. [系统架构](./architecture.md) - 详细设计
3. [数据模型](./data-models.md) - 模型定义
4. [API 设计](./api-design.md) - 接口设计

### 运维路径
1. [完整管理指南](./manager-guide_zh.md) - 管理操作
2. [CLI 使用指南](./cli-usage.md) - 命令工具
3. [部署架构](./deployment-architecture.md) - 生产部署
4. [路由策略](./routing-strategies.md) - 流量管理

### 开发者路径
1. [API 设计](./api-design.md) - API 接口
2. [数据模型](./data-models.md) - 数据结构
3. [实现计划](./implementation-plan.md) - 开发计划
4. [系统架构](./architecture.md) - 技术架构

---

## 🚀 快速命令参考

### 服务管理
```bash
# 注册服务
myagent-manager register <name> <agent_path> --auto-start

# 启动/停止/重启
myagent-manager start <service_name>
myagent-manager stop <service_name>
myagent-manager restart <service_name>

# 查看服务
myagent-manager list
myagent-manager status <service_name>
myagent-manager stats
```

### 服务器启动
```bash
# 守护进程模式
myagent-manager daemon

# API 服务器
myagent-manager api --port 8000

# 代理服务器
myagent-manager proxy --port 9000

# API + 代理组合
myagent-manager api --port 8000 --proxy-port 9000
```

---

## 🔗 相关链接

- **项目主页**: [MyAgent](../../README.md)
- **核心文档**: [docs/](../)
- **示例代码**: [examples/](../../examples/)
- **API 文档**: http://localhost:8000/docs (启动 API 服务器后访问)

---

## 📝 文档贡献

如发现文档问题或需要改进，请：
1. 提交 Issue 描述问题
2. 提交 Pull Request 改进文档

---

## 📊 文档统计

| 文档 | 类型 | 适合人群 | 长度 |
|-----|------|---------|-----|
| [CLI 使用指南](./cli-usage.md) | 实践指南 | 所有用户 | ⭐⭐⭐ |
| [使用指南](./USAGE_GUIDE.md) | 快速入门 | 新手 | ⭐⭐ |
| [完整管理指南](./manager-guide_zh.md) | 完整文档 | 管理员 | ⭐⭐⭐⭐⭐ |
| [系统架构](./architecture.md) | 设计文档 | 架构师 | ⭐⭐⭐ |
| [架构总结](./architecture-summary.md) | 概览文档 | 架构师 | ⭐⭐ |
| [数据模型](./data-models.md) | 技术文档 | 开发者 | ⭐⭐⭐ |
| [API 设计](./api-design.md) | 技术文档 | 开发者 | ⭐⭐⭐ |
| [路由策略](./routing-strategies.md) | 技术文档 | 运维/开发 | ⭐⭐⭐ |
| [实现计划](./implementation-plan.md) | 开发文档 | 开发者 | ⭐⭐ |
| [部署架构](./deployment-architecture.md) | 运维文档 | 运维 | ⭐⭐ |

---

## 🆘 获取帮助

### 常见问题
参考文档中的"故障排除"章节：
- [完整管理指南 - 故障排除](./manager-guide_zh.md#故障排除)
- [CLI 使用指南 - 常见问题](./cli-usage.md#常见问题)

### 命令帮助
```bash
# 查看所有命令
myagent-manager --help

# 查看特定命令帮助
myagent-manager <command> --help
```

### 在线支持
- GitHub Issues: 报告问题和功能请求
- 文档仓库: 提交文档改进建议

---

**最后更新**: 2024-10-05

**维护者**: MyAgent Team
