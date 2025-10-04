# 研究智能体快速入门指南

本指南将帮助您快速上手 MyAgent 的研究智能体系统，从基础使用到高级功能。

## 概述

研究智能体是基于 Deep Agents 架构的全功能智能体，集成了：

- 🌐 **网络搜索**：SERPER API 实时搜索
- 📚 **学术搜索**：arXiv、PubMed 论文检索
- 📊 **数据分析**：pandas、numpy 统计分析
- 🌍 **网页抓取**：BeautifulSoup 内容提取
- 💻 **代码执行**：Python 代码运行 + matplotlib 图表自动保存
- 📝 **文件系统**：虚拟文件系统 + 磁盘持久化
- ✅ **任务规划**：TODO 管理和追踪

## 环境配置

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 2. 配置 API 密钥

创建 `.env` 文件：

```env
# OpenAI API（必需）
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1  # 可选

# SERPER API（网络搜索）
SERPER_API_KEY=your_serper_api_key

# 其他可选配置
# SERPAPI_KEY=your_serpapi_key
# BRAVE_API_KEY=your_brave_api_key
```

### 3. 获取 API 密钥

- **OpenAI**: https://platform.openai.com/api-keys
- **SERPER**: https://serper.dev/api-key

## 快速开始

### 基础示例：简单研究

```python
import asyncio
from myagent.middleware.deep_agent import create_deep_agent
from myagent.tool.web_search import create_search_tools
from myagent.tool.filesystem import get_filesystem_tools

async def simple_research():
    # 创建工具集合
    tools = []
    tools.extend(create_search_tools())      # 网络搜索
    tools.extend(get_filesystem_tools())     # 文件系统

    # 创建 Deep Agent
    agent = create_deep_agent(
        tools=tools,
        name="simple_researcher",
        description="简单的研究助手"
    )

    # 执行研究任务
    result = await agent.run("""
    请搜索"人工智能 2024 年发展趋势"，
    将搜索结果保存到 research_results.md 文件中。
    """)

    print(result)

if __name__ == "__main__":
    asyncio.run(simple_research())
```

### 运行示例

```bash
uv run python simple_research.py
```

**预期输出：**
- 智能体搜索网络
- 保存结果到 `workspace/research_results.md`
- 返回研究摘要

## 完整研究智能体

使用所有可用工具创建全功能研究智能体：

```python
import asyncio
from myagent.middleware.deep_agent import create_deep_agent
from myagent.tool.web_search import create_search_tools
from myagent.tool.academic_search import create_academic_tools
from myagent.tool.data_analysis import create_data_analysis_tools
from myagent.tool.web_content import create_web_content_tools
from myagent.tool.code_execution import create_code_execution_tools

async def create_full_research_agent():
    """创建完整的研究智能体"""
    tools = []

    # 加载所有研究工具
    tools.extend(create_search_tools())          # 网络搜索
    tools.extend(create_academic_tools())        # 学术搜索
    tools.extend(create_data_analysis_tools())   # 数据分析
    tools.extend(create_web_content_tools())     # 网页抓取
    tools.extend(create_code_execution_tools())  # 代码执行

    # Deep Agent 工具自动包含：
    # - 规划工具 (write_todos, read_todos, complete_todo)
    # - 文件系统 (ls, read_file, write_file, edit_file)
    # - 子智能体 (create_subagent)

    agent = create_deep_agent(
        tools=tools,
        name="research_agent",
        description="全功能研究智能体"
    )

    agent.max_steps = 50  # 设置足够的步数

    return agent

async def run_research(topic: str):
    """执行研究任务"""
    agent = await create_full_research_agent()

    research_task = f"""
请对"{topic}"进行全面研究，要求：

## 研究任务

1. **信息收集**
   - 使用 web_search 搜索最新信息
   - 使用 arxiv_search 搜索相关学术论文
   - 使用 fetch_content 抓取重要网页内容

2. **数据分析**
   - 使用 analyze_data 分析趋势数据
   - 使用 execute_code 生成可视化图表

3. **报告生成**
   - 使用 write_file 保存所有中间结果到 data/ 目录
   - 使用 write_file 生成最终报告 final_report.md
   - 在报告中引用生成的图表

## 输出要求

必须创建以下文件：
- data/web_search_results.md
- data/academic_papers.md
- data/analysis_results.md
- final_report.md

请开始执行研究任务。
    """

    result = await agent.run(research_task)
    return result

if __name__ == "__main__":
    topic = "大语言模型智能体的发展历程"
    asyncio.run(run_research(topic))
```

### 运行完整研究

```bash
uv run python full_research.py
```

## 核心工具详解

### 1. 网络搜索工具

```python
from myagent.tool.web_search import WebSearchTool

# 使用示例
search_tool = WebSearchTool()
result = await search_tool.execute(
    query="LLM agents 2024",
    max_results=10
)
```

**特点：**
- 实时网络搜索（SERPER API）
- 返回标题、URL、摘要
- 支持结果数量控制

### 2. 学术搜索工具

```python
from myagent.tool.academic_search import ArxivSearchTool, PubMedSearchTool

# arXiv 搜索
arxiv_tool = ArxivSearchTool()
result = await arxiv_tool.execute(
    query="transformer architecture",
    max_results=5,
    category="cs.AI"
)

# PubMed 搜索
pubmed_tool = PubMedSearchTool()
result = await pubmed_tool.execute(
    query="machine learning medicine",
    max_results=5
)
```

**特点：**
- 免费学术资源
- 论文元数据（标题、作者、摘要、URL）
- 支持分类过滤

### 3. 数据分析工具

```python
from myagent.tool.data_analysis import DataAnalysisTool

analysis_tool = DataAnalysisTool()
result = await analysis_tool.execute(
    data_source="sales_data_2024",
    analysis_type="trend"
)
```

**分析类型：**
- `trend`: 趋势分析
- `correlation`: 相关性分析
- `summary`: 统计摘要

### 4. 代码执行工具（重要！）

```python
from myagent.tool.code_execution import CodeExecutionTool

code_tool = CodeExecutionTool()
result = await code_tool.execute(
    code="""
import matplotlib.pyplot as plt
import numpy as np

# 创建数据
x = np.linspace(0, 10, 100)
y = np.sin(x)

# 绘制图表
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.grid(True)
# 不需要 plt.savefig() - 自动保存！
"""
)
```

**关键特性：**
- ✅ 自动保存 matplotlib 图表到 `workspace/images/`
- ✅ 会话状态持久化（变量保留）
- ✅ 预导入 pandas、numpy、matplotlib
- ✅ 高分辨率输出（300 DPI）

**图表自动保存机制：**
```python
# 智能体执行代码后
# 输出：
# 📊 已保存图片 (1 个):
#   - workspace/images/plot_1759201785051_0.png
```

### 5. 文件系统工具

```python
from myagent.tool.filesystem import WriteFileTool, ReadFileTool

# 写入文件
write_tool = WriteFileTool()
await write_tool.execute(
    file_path="report.md",
    content="# 研究报告\n\n## 引言\n..."
)
# 文件自动保存到 workspace/report.md

# 读取文件
read_tool = ReadFileTool()
result = await read_tool.execute(file_path="report.md")
```

**持久化特性：**
- 双层存储：内存 + 磁盘
- 自动保存到 `workspace/` 目录
- 支持子目录（如 `data/results.md`）
- 启动时自动加载已有文件

### 6. 规划工具

```python
from myagent.tool.planning import WriteTodosTool, ReadTodosTool

# 创建任务清单
todos_tool = WriteTodosTool()
await todos_tool.execute(
    todos=["搜索信息", "分析数据", "生成报告"]
)

# 读取任务
read_todos_tool = ReadTodosTool()
result = await read_todos_tool.execute()
```

## 工作空间结构

执行研究任务后，`workspace/` 目录结构：

```
workspace/
├── llm_agent_research_plan.md        # 研究计划
├── data/                             # 数据目录
│   ├── web_search_results.md
│   ├── academic_papers.md
│   ├── analysis_results.md
│   └── web_content.md
├── code/                             # 代码目录
│   ├── analysis_scripts.py
│   └── results.txt
├── images/                           # 图片目录（自动创建）
│   ├── plot_1759201785051_0.png
│   ├── plot_1759201785052_0.png
│   └── ...
└── final_report.md                   # 最终报告
```

## 使用预构建的研究智能体

### 方式 1：命令行运行

```bash
# 使用默认主题
uv run python examples/research_agent_demo.py

# 指定研究主题
uv run python examples/research_agent_demo.py --topic "量子计算的最新进展"

# 仅测试工具
uv run python examples/research_agent_demo.py --test-tools
```

### 方式 2：Python 脚本

```python
from examples.research_agent_demo import create_research_agent, run_comprehensive_research
import asyncio

async def main():
    # 方式 A：直接运行研究
    await run_comprehensive_research(topic="您的研究主题")

    # 方式 B：创建智能体后自定义任务
    agent = await create_research_agent()
    result = await agent.run("您的自定义研究任务...")
    print(result)

asyncio.run(main())
```

## 高级功能

### 1. 自定义研究流程

```python
async def custom_research_workflow(topic: str):
    agent = await create_full_research_agent()

    # 第一阶段：信息收集
    await agent.run(f"搜索'{topic}'的最新信息并保存到 data/search.md")

    # 第二阶段：学术研究
    await agent.run(f"搜索'{topic}'的学术论文并保存到 data/papers.md")

    # 第三阶段：数据分析
    await agent.run("分析收集的数据并生成图表")

    # 第四阶段：报告生成
    await agent.run("整合所有信息，生成完整的研究报告 final_report.md")
```

### 2. 子智能体委托

```python
# Deep Agent 自动包含子智能体工具
async def use_subagent():
    agent = await create_full_research_agent()

    result = await agent.run("""
    创建一个子智能体来专门处理数据分析任务。
    任务：分析 data/results.csv 并生成统计报告。
    """)
```

### 3. 实时监控进度

```python
from myagent.trace import get_trace_manager

async def monitored_research(topic: str):
    agent = await create_full_research_agent()

    # 启动追踪
    trace_manager = get_trace_manager()

    result = await agent.run(f"研究 {topic}")

    # 查看执行统计
    print(f"执行步数：{agent.current_step}/{agent.max_steps}")
    print(f"消息数量：{len(agent.memory.messages)}")
```

## 最佳实践

### 1. 明确的任务指令

✅ **好的示例：**
```python
task = """
请对"人工智能伦理"进行研究，要求：
1. 使用 web_search 搜索最新新闻（5-10 条）
2. 使用 arxiv_search 搜索相关论文（5 篇）
3. 使用 write_file 将结果保存到 data/search.md 和 data/papers.md
4. 使用 write_file 生成综合报告 report.md
"""
```

❌ **不好的示例：**
```python
task = "研究人工智能伦理"  # 太模糊
```

### 2. 设置合理的步数限制

```python
# 简单任务
agent.max_steps = 10

# 中等复杂任务
agent.max_steps = 30

# 完整研究任务
agent.max_steps = 50
```

### 3. 明确完成标准

```python
task = """
研究任务...

完成标准：
✅ data/web_search_results.md
✅ data/academic_papers.md
✅ final_report.md

只有所有文件创建完成后才能使用 terminate 工具。
"""
```

### 4. 图表引用规范

在报告中引用自动生成的图表：

```markdown
## 数据分析

### 趋势分析

![市场增长趋势](images/plot_1759201785051_0.png)

根据上图可以看出...
```

## 常见问题

### Q1: 为什么没有保存图表？

**A:** 确保代码执行工具正确使用 matplotlib：

```python
import matplotlib.pyplot as plt

# 创建图表
plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('My Chart')
# 不需要 plt.savefig() - 自动保存！
# 不需要 plt.show() - 使用 Agg 后端
```

### Q2: 为什么文件只在内存中？

**A:** 确保使用的是更新后的文件系统工具。检查 `myagent/tool/filesystem.py` 是否包含磁盘持久化代码。

### Q3: 如何查看生成的文件？

**A:** 所有文件保存在项目根目录的 `workspace/` 文件夹中：

```bash
ls -R workspace/
```

### Q4: 研究智能体中途停止了？

**A:** 可能原因：
- `max_steps` 太小，增加到 50
- API 配额耗尽，检查 API 密钥
- 网络问题，检查连接

### Q5: 如何自定义系统提示？

**A:** 在创建智能体时指定：

```python
agent = create_deep_agent(
    tools=tools,
    name="researcher",
    description="专业研究助手",
    system_prompt="""你是一位专业的研究助手，擅长：
    - 全面的信息收集
    - 深入的数据分析
    - 清晰的报告撰写

    请始终保持客观和专业的态度。"""
)
```

## 性能优化

### 1. 并行工具调用

智能体会自动并行执行独立的工具调用，无需手动优化。

### 2. 缓存搜索结果

```python
# 避免重复搜索相同内容
task = """
1. 搜索"AI ethics"并保存到 data/search1.md
2. 读取 data/search1.md 的内容进行分析
   （而不是重新搜索）
"""
```

### 3. 合理使用子智能体

将独立的子任务委托给子智能体：

```python
task = """
创建子智能体处理以下任务：
- 子任务 1：数据收集
- 子任务 2：数据分析
- 子任务 3：报告生成
"""
```

## 下一步

现在您已经掌握了研究智能体的基础使用，可以探索：

1. **[完整工作流程文档](../RESEARCH_AGENT_WORKFLOW.md)** - 详细的流程说明
2. **[工具 API 参考](../api/tools_zh.md)** - 所有工具的详细文档
3. **[系统架构](../architecture/system_architecture.md)** - 深入理解架构
4. **[示例代码](../../examples/)** - 更多实际示例

## 参考资源

- **示例代码**: `examples/research_agent_demo.py`
- **工作流程文档**: `docs/RESEARCH_AGENT_WORKFLOW.md`
- **工具文档**: `docs/api/tools_zh.md`
- **架构文档**: `docs/architecture/system_architecture.md`

---

准备好构建您的第一个研究智能体了吗？从简单示例开始，逐步探索更高级的功能！
