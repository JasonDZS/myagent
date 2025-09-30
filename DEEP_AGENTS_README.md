# Deep Agents Implementation for MyAgent

基于 DeepAgents 架构在 myagent 框架中的完整实现，提供复杂多步骤任务的智能体解决方案。

## 🚀 概述

这个实现将 DeepAgents 的四大核心组件完美集成到 myagent 框架中：

1. **规划工具 (Planning Tool)** - 任务分解和进度管理
2. **虚拟文件系统** - 会话内文件持久化和管理
3. **子智能体系统 (Sub Agents)** - 专业智能体委托和上下文隔离
4. **中间件系统** - 模块化能力扩展

## 📋 核心功能

### ✅ 规划工具 (Planning Tool)
- `write_todos` 工具用于任务规划和管理
- 支持任务状态：pending → in_progress → completed
- 进度可视化和优先级管理
- 任务依赖关系处理

### 📁 虚拟文件系统
- `ls` - 列出所有文件
- `read_file` - 读取文件内容（支持行号和分页）
- `write_file` - 创建/覆盖文件
- `edit_file` - 精确文本替换编辑

### 🤖 子智能体系统
- `task` 工具用于委托专业任务
- 内置子智能体类型：
  - `general-purpose` - 通用复杂任务
  - `research-agent` - 研究和分析专家
  - `code-reviewer` - 代码审查专家
- 支持自定义子智能体注册

### ⚙️ 中间件系统
- 模块化架构支持能力组合
- 自动提示增强和工具集成
- 可扩展的自定义中间件支持

## 🛠 安装和使用

### 基本使用

```python
from myagent import create_deep_agent

# 创建 Deep Agent
agent = create_deep_agent(
    tools=[your_custom_tools],  # 可选：添加自定义工具
    llm_config={
        "model": "gpt-4",
        "temperature": 0.7
    },
    name="my_deep_agent",
    description="专业的深度智能体"
)

# 执行复杂任务
result = await agent.run("请帮我分析市场数据并创建完整的报告")
```

### 高级配置

```python
from myagent.middleware import DeepAgentMiddleware, PlanningMiddleware
from myagent.tool import SubAgentTool

# 使用单独的中间件
planning_middleware = PlanningMiddleware()
subagent_tool = SubAgentTool()

# 注册自定义子智能体
subagent_tool.register_subagent({
    "name": "data-analyst",
    "description": "专业数据分析师",
    "prompt": "你是数据分析专家，提供准确的数据洞察...",
    "tools": [custom_data_tools],
    "max_steps": 10
})
```

## 🧪 测试验证

运行测试确保功能正常：

```bash
# 基础功能测试
python examples/deep_agent_simple_test.py

# 完整功能测试（需要 OpenAI API Key）
python examples/deep_agent_test.py

# 运行特定测试
python examples/deep_agent_test.py --test planning
```

## 📝 使用示例

### 1. 复杂研究项目

```python
agent = create_deep_agent(tools=[web_search_tool])

result = await agent.run("""
我需要进行AI安全的综合研究，包括：
1. 文献综述和现状分析
2. 主要风险评估
3. 技术解决方案研究
4. 政策建议整理
5. 完整报告撰写

请系统化完成这个研究项目。
""")
```

### 2. 软件开发项目规划

```python
agent = create_deep_agent(tools=[code_analysis_tools])

result = await agent.run("""
帮我规划一个新的Web应用开发项目：
- 用户认证系统
- 任务管理功能
- 协作特性
- 移动端适配

创建完整的开发计划和技术文档。
""")
```

### 3. 数据分析流水线

```python
agent = create_deep_agent(tools=[data_tools])

result = await agent.run("""
分析销售数据并生成报告：
1. 数据清理和预处理
2. 趋势分析和预测
3. 可视化图表生成
4. 业务洞察提取
5. 执行摘要撰写
""")
```

## 🏗 架构设计

### 核心组件映射

| DeepAgents 组件 | MyAgent 实现 | 文件位置 |
|----------------|-------------|---------|
| Planning Tool | `PlanningTool` | `myagent/tool/planning.py` |
| Sub Agents | `SubAgentTool` | `myagent/tool/subagent.py` |
| Virtual Filesystem | Filesystem Tools | `myagent/tool/filesystem.py` |
| Middleware System | Middleware Framework | `myagent/middleware/` |

### 中间件架构

```
DeepAgentMiddleware
├── PlanningMiddleware (优先级: 10)
├── FilesystemMiddleware (优先级: 20)
└── SubAgentMiddleware (优先级: 30)
```

## 🔧 扩展开发

### 创建自定义中间件

```python
from myagent.middleware.base import BaseMiddleware, MiddlewareContext

class CustomMiddleware(BaseMiddleware):
    name = "custom_middleware"
    description = "自定义功能中间件"
    priority = 40
    
    async def process(self, context: MiddlewareContext) -> MiddlewareContext:
        # 添加自定义工具
        context.tools.append(your_custom_tool)
        
        # 添加自定义提示
        context.system_prompt_parts.append("你的自定义指令...")
        
        return context
```

### 创建自定义工具

```python
from myagent.tool.base_tool import BaseTool, ToolResult

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "自定义工具描述"
    parameters = {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "参数描述"}
        },
        "required": ["param"]
    }
    
    async def execute(self, param: str, **kwargs) -> ToolResult:
        # 工具实现逻辑
        result = f"处理结果: {param}"
        return ToolResult(output=result)
```

## 📊 性能特点

- **内存效率**: 虚拟文件系统基于内存，快速访问
- **并行执行**: 子智能体支持独立并行处理
- **上下文隔离**: 避免主线程上下文污染
- **模块化设计**: 按需加载能力组件
- **追踪集成**: 完整的执行追踪和调试支持

## 🔍 调试和监控

Deep Agent 集成了 myagent 的完整追踪系统：

```python
# 启用详细追踪
agent = create_deep_agent(
    tools=tools,
    enable_tracing=True
)

# 查看执行追踪
from myagent.trace import get_trace_manager
trace_manager = get_trace_manager()
# 访问详细的执行记录
```

## 🎯 最佳实践

1. **任务规划**: 对于3步以上的复杂任务，使用规划工具
2. **文件管理**: 利用虚拟文件系统维护复杂工作流状态
3. **专业委托**: 将独立的专业任务委托给子智能体
4. **模块化扩展**: 使用中间件系统添加自定义能力
5. **追踪调试**: 启用追踪功能进行性能分析和调试

## 📚 参考资源

- **原始 DeepAgents**: 基于 LangGraph 的智能体框架
- **MyAgent 框架**: 轻量级 LLM 智能体工具包
- **示例代码**: `examples/deep_agent_*.py`
- **测试套件**: 验证所有功能的完整测试

## 🤝 贡献和反馈

这个实现完全基于开源框架构建，欢迎：
- 报告 Bug 和问题
- 提出功能建议
- 贡献代码改进
- 分享使用案例

Deep Agents + MyAgent = 强大而灵活的复杂任务智能体解决方案！