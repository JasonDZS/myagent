# MyAgent Documentation

Welcome to the MyAgent documentation! MyAgent is a lightweight toolkit for building tool-aware LLM agents with comprehensive tracing capabilities.

## 📚 Documentation Structure

### Getting Started
- **[Quick Start](guides/quick-start.md)** - Get up and running in minutes
- **[Installation](guides/installation.md)** - Detailed installation instructions
- **[Basic Concepts](guides/basic-concepts.md)** - Core concepts and terminology

### Guides
- **[Creating Agents](guides/creating-agents.md)** - How to build your first agent
- **[Custom Tools](guides/custom-tools.md)** - Building custom tools for your agents
- **[Configuration](guides/configuration.md)** - Environment variables and settings
- **[Best Practices](guides/best-practices.md)** - Recommended patterns and practices

### API Reference
- **[Agent Classes](api/agents.md)** - BaseAgent, ToolCallAgent, ReActAgent
- **[Tool System](api/tools.md)** - BaseTool, ToolCollection, built-in tools
- **[Schema Types](api/schema.md)** - Message, ToolCall, ToolResult, and more
- **[LLM Integration](api/llm.md)** - LLM configuration and usage

### WebSocket Server
- **[Server Setup](websocket/server-setup.md)** - Running the WebSocket server
- **[Protocol Documentation](websocket/protocol.md)** - WebSocket message format and events
- **[Client Integration](websocket/client-integration.md)** - Connecting clients to the server
- **[Session Management](websocket/session-management.md)** - Managing agent sessions

### Tracing & Debugging
- **[Trace System Overview](tracing/overview.md)** - Understanding the tracing system
- **[Trace Decorators](tracing/decorators.md)** - Using trace decorators
- **[Query & Analysis](tracing/query.md)** - Querying and analyzing traces
- **[Trace Viewer](tracing/viewer.md)** - Using the web-based trace viewer

### Examples
- **[Simple Agent](examples/simple-agent.md)** - Basic agent example
- **[Web Search Agent](examples/web-search.md)** - Agent with web search capabilities
- **[WebSocket Agent](examples/websocket-agent.md)** - Real-time WebSocket agent
- **[Custom Tool Examples](examples/custom-tools.md)** - Various custom tool implementations

## Existing Documentation (Legacy)

### 🔍 [Trace系统架构](./trace_system_architecture.md)
详细介绍MyAgent框架的trace系统设计架构，包括：
- 扁平化trace结构设计
- 各层级的数据格式和字段说明
- Think→Tools直接关系的实现原理
- 信息冗余消除的技术细节

**适用对象**: 框架开发者、架构师、需要深入了解trace系统内部机制的用户

### 🛠️ [Trace使用指南](./trace_usage_guide.md)
全面的trace系统实用手册，涵盖：
- 快速开始和基础配置
- 数据分析和可视化方法
- 调试技巧和故障排查
- 性能监控和告警设置
- 自定义工具的trace集成

**适用对象**: 应用开发者、运维人员、需要使用trace功能进行开发和监控的用户

### 🔐 [工具确认功能集成指南](./client-confirmation-guide.md)
完整的工具确认功能客户端集成文档，包括：
- WebSocket事件协议规范
- JavaScript/React/Python客户端实现示例
- 用户体验设计最佳实践
- 错误处理和安全考虑
- 国际化和测试工具

**适用对象**: 客户端开发人员、前端工程师、需要集成工具确认功能的开发者

### 📖 [工具确认 API 参考](./confirmation-api-reference.md)
工具确认功能的详细API技术规范：
- WebSocket事件结构定义
- TypeScript/Python SDK 示例
- 错误处理规范和配置参数
- 完整的类型定义和接口说明

**适用对象**: API集成开发者、需要详细技术规范的高级开发人员

### 🚀 [工具确认快速开始](./confirmation-quickstart.md)
5分钟快速集成工具确认功能：
- 最小化集成示例
- 常见问题解决方案
- 生产环境部署建议
- 进阶自定义配置

**适用对象**: 希望快速上手的开发者、项目负责人

### 🔧 [工具确认故障排除](./confirmation-troubleshooting.md)
工具确认功能的详细故障排除指南：
- 常见问题及解决方案
- step_id 冲突修复说明
- 调试技巧和最佳实践
- 版本更新和升级建议

**适用对象**: 遇到问题的开发者、运维人员、技术支持

## 🚀 Quick Links

- **[GitHub Repository](https://github.com/yourusername/myagent)**
- **[PyPI Package](https://pypi.org/project/myagent/)**
- **[Examples Directory](../examples/)**
- **[Issue Tracker](https://github.com/yourusername/myagent/issues)**

## 📖 Reading Order

If you're new to MyAgent, we recommend following this reading order:

1. **[Quick Start](guides/quick-start.md)** - Get your first agent running
2. **[Basic Concepts](guides/basic-concepts.md)** - Understand the framework
3. **[Creating Agents](guides/creating-agents.md)** - Learn to build agents
4. **[Custom Tools](guides/custom-tools.md)** - Extend with custom functionality
5. **[WebSocket Server](websocket/server-setup.md)** - Add real-time capabilities
6. **[Tracing System](tracing/overview.md)** - Debug and monitor agents

## 🔧 Core Features

### ✅ ReAct Pattern Implementation
- Reasoning and Acting in unified workflow
- Tool-aware agent architecture
- Flexible tool selection strategies

### ✅ Comprehensive Tracing
- Complete execution tracking
- Detailed performance monitoring
- Web-based trace viewer

### ✅ Real-time WebSocket Support
- Live agent interactions
- Session management
- Event-based communication

### ✅ Extensible Tool System
- Custom tool development
- Built-in tool collection
- Tool confirmation workflows

## 🆘 Getting Help

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/yourusername/myagent/issues)
- **Discussions**: Join the community discussion on [GitHub Discussions](https://github.com/yourusername/myagent/discussions)
- **Examples**: Check the [examples directory](../examples/) for practical implementations

---

*Last updated: 2024-09-26*
