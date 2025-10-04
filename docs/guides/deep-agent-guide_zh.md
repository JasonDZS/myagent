# Deep Agent 使用指南

Deep Agent 是 MyAgent 的高级中间件层，提供任务规划、文件系统、子智能体等企业级能力。

## 什么是 Deep Agent？

Deep Agent 是一个智能体包装器，自动集成以下能力：

- 📋 **任务规划**：创建和管理 TODO 列表
- 📁 **文件系统**：虚拟文件系统 + 磁盘持久化
- 🤖 **子智能体**：创建和管理子智能体
- 🔧 **工具集成**：自动添加所有 Deep Agent 工具

## 快速开始

### 基础使用

```python
from myagent.agent import create_deep_agent

# 创建 Deep Agent
agent = create_deep_agent(
    tools=[],  # 可选：添加自定义工具
    name="my_agent",
    description="我的 Deep Agent"
)

# 使用智能体
result = await agent.run("创建一个项目计划")
```

### 与普通智能体的区别

**普通智能体：**
```python
from myagent import create_toolcall_agent

agent = create_toolcall_agent(
    tools=[CustomTool()],
    name="basic_agent"
)
# 只有自定义工具和 terminate
```

**Deep Agent：**
```python
from myagent.agent import create_deep_agent

agent = create_deep_agent(
    tools=[CustomTool()],
    name="deep_agent"
)
# 自动包含：
# - 3 个规划工具 (write_todos, read_todos, complete_todo)
# - 4 个文件系统工具 (ls, read_file, write_file, edit_file)
# - 1 个子智能体工具 (create_subagent)
# - 自定义工具
# - terminate 工具
```

## 核心能力详解

### 1. 任务规划能力

Deep Agent 可以创建和管理任务清单。

#### 创建任务清单

```python
agent = create_deep_agent(name="planner")

result = await agent.run("""
创建一个网站开发项目的任务清单：
1. 设计数据库架构
2. 实现后端 API
3. 开发前端界面
4. 编写测试用例
5. 部署到生产环境
""")
```

**智能体会自动使用 `write_todos` 工具创建任务列表。**

#### 查看任务进度

```python
result = await agent.run("显示当前的任务列表")
# 智能体使用 read_todos 工具
```

**输出示例：**
```
📋 当前任务：
⏳ 1. 设计数据库架构
⏳ 2. 实现后端 API
⏳ 3. 开发前端界面
⏳ 4. 编写测试用例
⏳ 5. 部署到生产环境
```

#### 标记任务完成

```python
result = await agent.run("我已经完成了数据库设计，请标记任务 1 为完成")
# 智能体使用 complete_todo 工具
```

**输出示例：**
```
✅ 已完成任务 1：设计数据库架构
```

### 2. 文件系统能力

Deep Agent 提供虚拟文件系统，所有文件自动持久化到磁盘。

#### 创建文件

```python
agent = create_deep_agent(name="writer")

result = await agent.run("""
创建一个项目文档 project_plan.md，包含以下内容：
- 项目概述
- 技术栈选择
- 开发时间线
""")
# 智能体使用 write_file 工具
# 文件自动保存到 workspace/project_plan.md
```

#### 读取文件

```python
result = await agent.run("读取 project_plan.md 的内容")
# 智能体使用 read_file 工具
```

#### 编辑文件

```python
result = await agent.run("""
编辑 project_plan.md，
将"技术栈选择"章节改为"技术架构设计"
""")
# 智能体使用 edit_file 工具
```

#### 列出所有文件

```python
result = await agent.run("显示当前所有文件")
# 智能体使用 ls 工具
```

**输出示例：**
```
📁 虚拟文件系统内容：
📄 project_plan.md (2.3 KB)
📄 data/requirements.txt (0.5 KB)
📄 docs/api_spec.md (5.1 KB)
📊 总计：3 个文件
```

### 3. 子智能体能力

Deep Agent 可以创建子智能体来处理特定任务。

#### 基础用法

```python
agent = create_deep_agent(name="manager")

result = await agent.run("""
创建一个子智能体来处理以下任务：
分析 sales_data.csv 并生成月度销售报告
""")
# 智能体使用 create_subagent 工具
```

#### 指定工具

```python
result = await agent.run("""
创建子智能体处理数据分析任务，
给它提供以下工具：
- read_file（读取数据）
- analyze_data（分析数据）
- write_file（保存报告）
""")
```

#### 多层级委托

```python
# 父智能体
parent_agent = create_deep_agent(name="project_manager")

result = await parent_agent.run("""
项目任务：开发一个数据分析系统

请创建子智能体处理以下子任务：
1. 子智能体 A：设计数据库架构
2. 子智能体 B：实现数据处理逻辑
3. 子智能体 C：开发可视化界面
""")
```

## 实际应用场景

### 场景 1：软件项目管理

```python
async def manage_software_project():
    agent = create_deep_agent(name="project_manager")

    # 1. 创建项目计划
    await agent.run("""
    创建软件开发项目计划：
    1. 需求分析
    2. 系统设计
    3. 编码实现
    4. 测试验证
    5. 上线部署

    并创建 project_overview.md 文档记录项目概述
    """)

    # 2. 执行各个阶段
    await agent.run("开始需求分析，完成后标记任务 1 为完成")

    # 3. 委托子任务
    await agent.run("""
    创建子智能体处理系统设计任务，
    要求生成设计文档保存到 docs/system_design.md
    """)

    # 4. 查看进度
    await agent.run("显示项目进度和所有生成的文档")
```

### 场景 2：研究项目

```python
async def conduct_research():
    # 集成研究工具
    from myagent.tool.web_search import create_search_tools
    from myagent.tool.academic_search import create_academic_tools

    tools = []
    tools.extend(create_search_tools())
    tools.extend(create_academic_tools())

    agent = create_deep_agent(
        tools=tools,
        name="researcher"
    )

    # 1. 创建研究计划
    await agent.run("""
    创建"量子计算"研究项目的任务计划：
    1. 文献综述
    2. 技术分析
    3. 应用场景调研
    4. 报告撰写
    """)

    # 2. 执行研究并保存结果
    await agent.run("""
    执行任务 1：文献综述
    - 使用 arxiv_search 搜索相关论文
    - 使用 web_search 搜索最新新闻
    - 将结果保存到 research/literature_review.md
    - 完成后标记任务 1
    """)

    # 3. 生成最终报告
    await agent.run("""
    整合所有研究结果，
    生成完整的研究报告 final_report.md
    """)
```

### 场景 3：数据处理流水线

```python
async def data_pipeline():
    from myagent.tool.code_execution import create_code_execution_tools

    agent = create_deep_agent(
        tools=create_code_execution_tools(),
        name="data_engineer"
    )

    # 1. 创建处理流程
    await agent.run("""
    创建数据处理任务清单：
    1. 数据清洗
    2. 特征工程
    3. 数据分析
    4. 生成报告
    """)

    # 2. 执行数据处理
    await agent.run("""
    执行数据清洗任务：
    - 读取 raw_data.csv
    - 使用 execute_code 工具执行清洗脚本
    - 保存结果到 cleaned_data.csv
    - 标记任务 1 完成
    """)

    # 3. 生成可视化
    await agent.run("""
    使用 execute_code 创建数据可视化图表，
    自动保存到 workspace/images/
    """)
```

## 工作空间管理

### 文件组织结构

Deep Agent 使用 `workspace/` 目录存储所有文件：

```
workspace/
├── project_plan.md              # 项目文档
├── data/                        # 数据目录
│   ├── raw_data.csv
│   └── cleaned_data.csv
├── docs/                        # 文档目录
│   ├── system_design.md
│   └── api_spec.md
├── research/                    # 研究目录
│   └── literature_review.md
├── images/                      # 图片目录
│   └── plot_*.png
└── reports/                     # 报告目录
    └── final_report.md
```

### 最佳实践

#### 1. 使用子目录组织文件

```python
await agent.run("""
创建以下文件：
- docs/requirements.md（需求文档）
- docs/design.md（设计文档）
- code/main.py（主程序）
- tests/test_main.py（测试文件）
""")
```

#### 2. 明确的文件命名

✅ **好的命名：**
```python
- project_requirements.md
- api_design_v2.md
- user_authentication_flow.md
```

❌ **不好的命名：**
```python
- doc1.md
- temp.md
- file.txt
```

#### 3. 使用任务清单追踪进度

```python
# 开始项目时
await agent.run("创建项目任务清单")

# 完成每个任务后
await agent.run("标记任务 N 为完成")

# 定期检查进度
await agent.run("显示当前项目进度")
```

## 高级功能

### 1. 自定义工具集成

```python
from myagent.tool import BaseTool, ToolResult

class DatabaseTool(BaseTool):
    name = "query_database"
    description = "查询数据库"

    async def execute(self, query: str) -> ToolResult:
        # 实现数据库查询
        result = await db.execute(query)
        return ToolResult(output=result)

# 集成到 Deep Agent
agent = create_deep_agent(
    tools=[DatabaseTool()],
    name="data_agent"
)

# 智能体可以使用所有工具
await agent.run("""
1. 使用 query_database 查询用户数据
2. 将结果保存到 user_report.md
""")
```

### 2. 多智能体协作

```python
# 创建多个专门的智能体
planner = create_deep_agent(name="planner")
coder = create_deep_agent(
    tools=[CodeExecutionTool()],
    name="coder"
)
writer = create_deep_agent(name="writer")

# 协作完成任务
async def team_work():
    # 规划阶段
    plan = await planner.run("创建项目开发计划")

    # 开发阶段
    code = await coder.run("根据计划实现核心功能")

    # 文档阶段
    docs = await writer.run("编写项目文档")
```

### 3. 工作流自动化

```python
async def automated_workflow(data_file: str):
    agent = create_deep_agent(
        tools=[
            *create_code_execution_tools(),
            *create_search_tools()
        ],
        name="automation_agent"
    )

    workflow = f"""
自动化数据处理工作流：

任务清单：
1. 数据验证
2. 数据清洗
3. 数据分析
4. 报告生成
5. 结果发布

请按顺序执行所有任务：
1. 读取 {data_file}
2. 使用 execute_code 验证数据格式
3. 使用 execute_code 清洗数据
4. 使用 execute_code 生成分析图表
5. 将所有结果整合到 final_report.md
6. 完成后显示任务完成情况

每完成一个任务就标记为完成。
    """

    result = await agent.run(workflow)
    return result
```

## 配置选项

### 基本配置

```python
agent = create_deep_agent(
    tools=[...],                    # 自定义工具列表
    name="agent_name",              # 智能体名称
    description="agent description" # 智能体描述
)
```

### 高级配置

```python
from myagent.agent import create_deep_agent

agent = create_deep_agent(
    tools=[...],
    name="advanced_agent",
    description="高级智能体",
    system_prompt="""你是一个专业的项目管理助手。
    在处理任务时：
    1. 始终先创建任务清单
    2. 将所有重要信息保存到文件
    3. 定期更新任务进度
    4. 遇到复杂任务时使用子智能体"""
)

# 设置最大步数
agent.max_steps = 50

# 设置 LLM 配置
agent.llm_config = {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4096
}
```

## 调试和监控

### 查看执行统计

```python
result = await agent.run("执行任务...")

print(f"执行步数：{agent.current_step}/{agent.max_steps}")
print(f"消息数量：{len(agent.memory.messages)}")
```

### 使用追踪系统

```python
from myagent.trace import get_trace_manager, trace_agent

@trace_agent
async def traced_execution():
    agent = create_deep_agent(name="traced_agent")
    result = await agent.run("任务...")
    return result

# 执行后查看追踪
trace_manager = get_trace_manager()
# 分析执行历史
```

### 查看工作空间状态

```python
await agent.run("列出所有文件和当前任务状态")
```

## 常见问题

### Q1: Deep Agent 和普通 Agent 的性能差异？

**A:** Deep Agent 额外包含 8 个工具（3 个规划 + 4 个文件系统 + 1 个子智能体），会增加提示长度，但对性能影响很小。如果不需要这些能力，可以使用普通 `create_toolcall_agent()`。

### Q2: 文件系统的大小限制？

**A:** 没有硬性限制，但建议：
- 单个文件 < 10 MB
- 总文件数 < 1000 个
- 定期清理不需要的文件

### Q3: 子智能体可以嵌套吗？

**A:** 可以。子智能体也是 Deep Agent，可以创建自己的子智能体。但建议不超过 3 层嵌套，避免过度复杂。

### Q4: 如何在多次运行间保持状态？

**A:** 文件系统会自动持久化到 `workspace/` 目录。重启程序后，文件会自动加载。但任务清单（TODO）是会话级的，不会持久化。

### Q5: 如何限制工具使用？

**A:** 在系统提示中明确说明：

```python
agent = create_deep_agent(
    tools=[...],
    system_prompt="""
    工具使用规则：
    - 只在必要时使用文件系统
    - 不要创建子智能体处理简单任务
    - 优先使用已有文件而不是重新创建
    """
)
```

## 总结

Deep Agent 提供了企业级的智能体能力：

✅ **任务管理** - 自动创建和追踪任务
✅ **文件系统** - 持久化存储和管理
✅ **子智能体** - 任务委托和协作
✅ **工具集成** - 无缝集成自定义工具
✅ **工作流** - 支持复杂的多步骤流程

适合以下场景：
- 项目管理和规划
- 研究和分析任务
- 数据处理流水线
- 文档生成和管理
- 复杂的多步骤工作流

## 下一步

- **[研究智能体指南](research-agent-guide_zh.md)** - 了解完整的研究系统
- **[工具 API 文档](../api/tools_zh.md)** - 详细的工具参考
- **[工作流程文档](../RESEARCH_AGENT_WORKFLOW.md)** - 完整流程说明

---

开始使用 Deep Agent 构建您的智能应用！
