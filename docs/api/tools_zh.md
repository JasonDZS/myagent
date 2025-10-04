# 工具系统 API 参考

本文档提供 MyAgent 工具系统的完整 API 参考，包括基础类、内置工具和工具管理。

## 核心类

### BaseTool

所有工具的抽象基类。所有自定义工具必须继承此类。

```python
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult

class BaseTool(ABC):
    name: str
    description: str
    user_confirm: bool = False
    enable_tracing: bool = True
```

#### 必需属性

- `name`: 工具的唯一标识符（LLM 和智能体使用）
- `description`: 工具功能的人类可读描述

#### 可选属性

- `user_confirm`: 如果为 True，执行前需要用户确认
- `enable_tracing`: 如果为 True，工具执行会被追踪（默认：True）

#### 抽象方法

##### execute()
```python
@abstractmethod
async def execute(self, **kwargs) -> ToolResult:
    """使用给定参数执行工具"""
    pass
```

**参数：** 基于工具需求的可变关键字参数

**返回：** `ToolResult` 实例

**必须实现** 由所有具体工具类实现。

#### 实现示例

```python
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult
import httpx

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "获取指定位置的当前天气信息"
    user_confirm = False

    async def execute(self, location: str) -> ToolResult:
        """获取某个位置的天气"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.weather.com/{location}")
                weather_data = response.json()

            return ToolResult(
                output=f"{location} 的天气：{weather_data['description']}，{weather_data['temperature']}°F"
            )
        except Exception as e:
            return ToolResult(error=f"获取天气失败：{str(e)}")
```

### ToolResult

所有工具执行的标准化结果格式。

```python
from pydantic import BaseModel, Field
from typing import Any, Optional

class ToolResult(BaseModel):
    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
```

#### 字段

- `output`: 成功的工具执行结果（任何类型）
- `error`: 工具执行失败时的错误消息
- `base64_image`: 可选的 base64 编码图片数据

#### 使用示例

```python
# 成功执行
return ToolResult(output="任务成功完成")

# 错误结果
return ToolResult(error="提供的输入无效")

# 带图片的结果
return ToolResult(
    output="生成图表",
    base64_image="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
)

# 混合结果
return ToolResult(
    output="分析完成但有警告",
    error="某些数据点缺失"
)
```

### ToolCollection

管理工具集合并提供访问方法。

```python
class ToolCollection:
    def __init__(self, *tools: BaseTool):
        """使用工具初始化"""

    def add_tool(self, tool: BaseTool) -> None:
        """添加工具到集合"""

    def remove_tool(self, name: str) -> None:
        """通过名称移除工具"""

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """通过名称获取工具"""

    def list_tools(self) -> list[str]:
        """列出所有工具名称"""

    async def execute(self, *, name: str, tool_input: dict) -> ToolResult:
        """通过名称执行工具"""
```

#### 构造函数

```python
def __init__(self, *tools: BaseTool)
```

使用初始工具创建集合。

**参数：**
- `*tools`: 可变数量的 BaseTool 实例

**示例：**
```python
collection = ToolCollection(
    WeatherTool(),
    CalculatorTool(),
    SearchTool()
)
```

#### 方法

##### add_tool()
```python
def add_tool(self, tool: BaseTool) -> None
```

添加工具到集合。

**参数：**
- `tool`: 要添加的 BaseTool 实例

**抛出：**
- `ValueError`: 如果工具名称已存在

**示例：**
```python
collection.add_tool(WeatherTool())
```

##### remove_tool()
```python
def remove_tool(self, name: str) -> None
```

通过名称移除工具。

**参数：**
- `name`: 要移除的工具名称

**抛出：**
- `KeyError`: 如果工具名称不存在

**示例：**
```python
collection.remove_tool("weather")
```

##### get_tool()
```python
def get_tool(self, name: str) -> Optional[BaseTool]
```

通过名称检索工具。

**参数：**
- `name`: 要检索的工具名称

**返回：** 工具实例或 None（如果未找到）

**示例：**
```python
weather_tool = collection.get_tool("weather")
if weather_tool:
    result = await weather_tool.execute(location="北京")
```

##### list_tools()
```python
def list_tools(self) -> list[str]
```

获取所有工具名称列表。

**返回：** 工具名称字符串列表

**示例：**
```python
tool_names = collection.list_tools()
print(f"可用工具：{', '.join(tool_names)}")
```

##### execute()
```python
async def execute(self, *, name: str, tool_input: dict) -> ToolResult
```

通过名称和参数执行工具。

**参数：**
- `name`: 要执行的工具名称
- `tool_input`: 传递给工具的参数字典

**返回：** 工具执行的 ToolResult

**抛出：**
- `KeyError`: 如果工具名称不存在
- `Exception`: 工具执行中的任何异常

**示例：**
```python
result = await collection.execute(
    name="weather",
    tool_input={"location": "上海"}
)
```

#### 属性

##### tool_names
```python
@property
def tool_names(self) -> list[str]:
```

获取所有工具名称列表（`list_tools()` 的别名）。

##### tool_map
```python
@property
def tool_map(self) -> dict[str, BaseTool]:
```

获取工具名称到工具实例的字典映射。

## 内置工具

### 系统工具

#### Terminate

特殊工具，允许智能体发出任务完成信号。

```python
from myagent.tool import Terminate

class Terminate(BaseTool):
    name = "terminate"
    description = "标记任务已完成"
    user_confirm = False
```

**自动添加** 到通过工厂函数创建的所有智能体。

**用法：**

智能体在确定对话完成时使用此工具：

```python
# 智能体完成任务后会使用 terminate 工具
response = await agent.run("2 + 2 等于多少？")
# 智能体计算，提供答案，然后调用 terminate
```

**自定义终止行为：**

```python
class CustomTerminate(BaseTool):
    name = "finish_task"
    description = "标记当前任务已完成并提供摘要"

    async def execute(self, summary: str = "") -> ToolResult:
        return ToolResult(output=f"任务已完成：{summary}")

# 在智能体中使用
agent = create_toolcall_agent(tools=[CustomTerminate()])
```

### Deep Agent 工具

使用 `create_deep_agent()` 时会自动包含这些工具。

#### 规划工具

**模块：** `myagent.tool.planning`

##### write_todos

创建或更新任务清单。

```python
from myagent.tool.planning import WriteTodosTool

class WriteTodosTool(BaseTool):
    name = "write_todos"
    description = "创建或更新要完成的任务列表"
```

**参数：**
- `todos` (list): 要创建的任务描述列表

**返回：** 带任务数量的确认消息

**示例：**
```python
result = await write_todos_tool.execute(
    todos=["研究 LLM 智能体", "撰写报告", "制作演示文稿"]
)
# 输出："✅ 已创建 3 个待办事项"
```

##### read_todos

读取当前任务列表。

```python
from myagent.tool.planning import ReadTodosTool

class ReadTodosTool(BaseTool):
    name = "read_todos"
    description = "读取当前任务列表"
```

**返回：** 带状态指示器的格式化任务列表

**示例：**
```python
result = await read_todos_tool.execute()
# 输出：
# 📋 当前任务：
# ⏳ 1. 研究 LLM 智能体
# ⏳ 2. 撰写报告
# ⏳ 3. 制作演示文稿
```

##### complete_todo

标记任务为已完成。

```python
from myagent.tool.planning import CompleteTodoTool

class CompleteTodoTool(BaseTool):
    name = "complete_todo"
    description = "标记任务为已完成"
```

**参数：**
- `task_index` (int): 要完成的任务索引（从 1 开始）

**返回：** 确认消息

**示例：**
```python
result = await complete_todo_tool.execute(task_index=1)
# 输出："✅ 已完成任务 1：研究 LLM 智能体"
```

**工厂函数：**
```python
from myagent.tool.planning import create_planning_tools

tools = create_planning_tools()
# 返回：[WriteTodosTool(), ReadTodosTool(), CompleteTodoTool()]
```

#### 文件系统工具

**模块：** `myagent.tool.filesystem`

这些工具提供带磁盘持久化的虚拟文件系统。

##### ls

列出工作空间中的文件。

```python
from myagent.tool.filesystem import ListFilesTool

class ListFilesTool(BaseTool):
    name = "ls"
    description = "列出虚拟文件系统中的所有文件及其大小"
```

**返回：** 带大小的格式化文件列表

**示例：**
```python
result = await ls_tool.execute()
# 输出：
# 📁 虚拟文件系统内容：
# 📄 report.md (2.5 KB)
# 📄 data/results.json (15.3 KB)
# 📊 总计：2 个文件
```

##### read_file

读取带行号的文件内容。

```python
from myagent.tool.filesystem import ReadFileTool

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "从虚拟文件系统读取文件内容"
```

**参数：**
- `file_path` (str): 文件路径
- `line_offset` (int, 可选): 起始行（从 0 开始）
- `limit` (int, 可选): 最大读取行数

**返回：** 带行号的文件内容

**示例：**
```python
result = await read_file_tool.execute(file_path="report.md")
# 输出：
# 📄 文件：report.md
#    1  # 研究报告
#    2
#    3  ## 引言
#    4  本报告涵盖...
```

##### write_file

写入内容到文件（持久化到磁盘）。

```python
from myagent.tool.filesystem import WriteFileTool

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "写入内容到文件（覆盖已存在的文件）"
```

**参数：**
- `file_path` (str): 文件路径
- `content` (str): 要写入的内容

**返回：** 带文件大小的确认消息

**示例：**
```python
result = await write_file_tool.execute(
    file_path="report.md",
    content="# 研究报告\n\n## 引言\n..."
)
# 输出："✅ 已创建文件：report.md (1.2 KB)"
# 文件自动保存到 workspace/report.md
```

##### edit_file

通过替换文本编辑文件。

```python
from myagent.tool.filesystem import EditFileTool

class EditFileTool(BaseTool):
    name = "edit_file"
    description = "通过替换特定文本内容编辑文件"
```

**参数：**
- `file_path` (str): 文件路径
- `old_string` (str): 要查找的文本
- `new_string` (str): 替换文本
- `replace_all` (bool, 可选): 替换所有出现

**返回：** 带更改摘要的确认消息

**示例：**
```python
result = await edit_file_tool.execute(
    file_path="report.md",
    old_string="## 引言",
    new_string="## 执行摘要"
)
# 输出："✅ 文件编辑成功：report.md"
```

**工厂函数：**
```python
from myagent.tool.filesystem import get_filesystem_tools

tools = get_filesystem_tools()
# 返回：[ListFilesTool(), ReadFileTool(), WriteFileTool(), EditFileTool()]
```

**持久化：**
- 所有文件自动保存到 `workspace/` 目录
- 支持子目录（例如 `data/results.md`）
- 启动时从磁盘加载文件
- 更改立即持久化

#### 子智能体工具

**模块：** `myagent.tool.subagent`

##### create_subagent

创建并运行子智能体处理委托任务。

```python
from myagent.tool.subagent import CreateSubAgentTool

class CreateSubAgentTool(BaseTool):
    name = "create_subagent"
    description = "创建子智能体处理特定子任务"
```

**参数：**
- `task` (str): 子智能体的任务描述
- `tools` (list[str], 可选): 提供给子智能体的工具名称

**返回：** 子智能体执行结果

**示例：**
```python
result = await create_subagent_tool.execute(
    task="分析 results.csv 中的数据并总结关键发现",
    tools=["read_file", "analyze_data"]
)
# 子智能体独立运行并返回结果
```

**工厂函数：**
```python
from myagent.tool.subagent import create_subagent_tools

tools = create_subagent_tools(parent_agent)
# 返回：[CreateSubAgentTool(parent_agent)]
```

### 研究工具

用于信息收集和分析的高级工具。

#### 网络搜索工具

**模块：** `myagent.tool.web_search`

##### web_search

使用 SERPER API 搜索网络。

```python
from myagent.tool.web_search import WebSearchTool

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "搜索网络获取当前信息"
```

**参数：**
- `query` (str): 搜索查询
- `max_results` (int, 可选): 最大结果数（默认：10）

**返回：** 带标题、URL 和摘要的格式化搜索结果

**要求：**
- `SERPER_API_KEY` 环境变量

**示例：**
```python
result = await web_search_tool.execute(
    query="LLM 智能体 2024",
    max_results=5
)
# 输出：
# 🔍 搜索结果："LLM 智能体 2024"
#
# 1. **2024 年构建 LLM 智能体**
#    https://example.com/llm-agents
#    了解如何构建自主 LLM 智能体...
```

##### scholar_search

使用 Google Scholar 进行学术搜索。

```python
from myagent.tool.web_search import ScholarSearchTool

class ScholarSearchTool(BaseTool):
    name = "scholar_search"
    description = "搜索学术论文和研究"
```

**参数：**
- `query` (str): 搜索查询
- `max_results` (int, 可选): 最大结果数

**返回：** 学术搜索结果

**工厂函数：**
```python
from myagent.tool.web_search import create_search_tools

tools = create_search_tools()
# 返回：[WebSearchTool(), ScholarSearchTool()]
```

#### 学术搜索工具

**模块：** `myagent.tool.academic_search`

##### arxiv_search

搜索 arXiv 预印本仓库。

```python
from myagent.tool.academic_search import ArxivSearchTool

class ArxivSearchTool(BaseTool):
    name = "arxiv_search"
    description = "在 arXiv 中搜索学术论文"
```

**参数：**
- `query` (str): 搜索查询
- `max_results` (int, 可选): 最大结果数（默认：10）
- `category` (str, 可选): arXiv 类别过滤

**返回：** 带标题、作者、摘要和 URL 的格式化论文结果

**示例：**
```python
result = await arxiv_search_tool.execute(
    query="transformer 架构",
    max_results=5,
    category="cs.AI"
)
# 输出：
# 📚 arXiv 搜索结果："transformer 架构"
#
# 1. **Attention Is All You Need**
#    作者：Vaswani 等
#    发表日期：2017-06-12
#    摘要：主流序列转换模型...
#    URL：https://arxiv.org/abs/1706.03762
```

##### pubmed_search

搜索 PubMed 生物医学文献。

```python
from myagent.tool.academic_search import PubMedSearchTool

class PubMedSearchTool(BaseTool):
    name = "pubmed_search"
    description = "在 PubMed 中搜索生物医学研究论文"
```

**参数：**
- `query` (str): 搜索查询
- `max_results` (int, 可选): 最大结果数

**返回：** PubMed 文章结果

**工厂函数：**
```python
from myagent.tool.academic_search import create_academic_tools

tools = create_academic_tools()
# 返回：[ArxivSearchTool(), PubMedSearchTool()]
```

#### 数据分析工具

**模块：** `myagent.tool.data_analysis`

##### analyze_data

对数据执行统计分析。

```python
from myagent.tool.data_analysis import DataAnalysisTool

class DataAnalysisTool(BaseTool):
    name = "analyze_data"
    description = "使用 pandas 和 numpy 分析数据"
```

**参数：**
- `data_source` (str): 数据描述或文件路径
- `analysis_type` (str): 分析类型（trend、correlation、summary）

**返回：** 带统计数据和洞察的分析结果

**示例：**
```python
result = await analyze_data_tool.execute(
    data_source="sales_data_2024",
    analysis_type="trend"
)
# 输出：
# 📊 数据分析结果
#
# sales_data_2024 的趋势分析：
# - 平均值：125.4
# - 中位数：118.2
# - 标准差：32.1
# - 趋势：↗ 增长（期间内 +15.3%）
```

**工厂函数：**
```python
from myagent.tool.data_analysis import create_data_analysis_tools

tools = create_data_analysis_tools()
# 返回：[DataAnalysisTool()]
```

#### 网页内容工具

**模块：** `myagent.tool.web_content`

##### fetch_content

获取并解析网页内容。

```python
from myagent.tool.web_content import WebContentTool

class WebContentTool(BaseTool):
    name = "fetch_content"
    description = "从网页获取和提取内容"
```

**参数：**
- `url` (str): 要获取的 URL
- `extract_type` (str, 可选): 内容提取类型（text、links、images）

**返回：** 提取和格式化的网页内容

**示例：**
```python
result = await fetch_content_tool.execute(
    url="https://example.com/article",
    extract_type="text"
)
# 输出：
# 🌐 内容来自：https://example.com/article
#
# 标题：理解 LLM 智能体
#
# 提取并清理的文章内容...
```

**工厂函数：**
```python
from myagent.tool.web_content import create_web_content_tools

tools = create_web_content_tools()
# 返回：[WebContentTool()]
```

#### 代码执行工具

**模块：** `myagent.tool.code_execution`

##### execute_code

执行 Python 代码并自动保存 matplotlib 图表。

```python
from myagent.tool.code_execution import CodeExecutionTool

class CodeExecutionTool(BaseTool):
    name = "execute_code"
    description = "使用数据科学库执行 Python 代码"
```

**参数：**
- `code` (str): 要执行的 Python 代码
- `timeout` (int, 可选): 执行超时（秒）（默认：30）

**返回：** 执行输出、错误和保存的图表位置

**功能：**
- 会话状态持久化（变量在执行之间保留）
- 自动保存 matplotlib 图表到 `workspace/images/`
- 预导入库：pandas、numpy、matplotlib
- 高分辨率图表输出（300 DPI）

**示例：**
```python
result = await execute_code_tool.execute(
    code="""
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('正弦波')
plt.grid(True)
# 不需要调用 plt.savefig() - 自动保存！
"""
)
# 输出：
# 📊 已保存图片 (1 个):
#   - workspace/images/plot_1759201785051_0.png
#
# 当前会话变量: x(ndarray), y(ndarray), plt(module)
```

**工厂函数：**
```python
from myagent.tool.code_execution import create_code_execution_tools

tools = create_code_execution_tools()
# 返回：[CodeExecutionTool()]
```

**重要说明：**
- matplotlib 使用 'Agg' 后端（非交互式）
- 所有打开的图形自动保存
- 图表保存到 `workspace/images/plot_<时间戳>_<索引>.png`
- 会话变量在执行之间持久化

## 工具统计

### 按类型分类

| 类型 | 数量 | 工具名称 |
|------|------|---------|
| **系统工具** | 1 | terminate |
| **规划工具** | 3 | write_todos, read_todos, complete_todo |
| **文件系统** | 4 | ls, read_file, write_file, edit_file |
| **子智能体** | 1 | create_subagent |
| **网络搜索** | 2 | web_search, scholar_search |
| **学术搜索** | 2 | arxiv_search, pubmed_search |
| **数据分析** | 1 | analyze_data |
| **网页内容** | 1 | fetch_content |
| **代码执行** | 1 | execute_code |
| **总计** | **16** | |

### 外部 API 集成

| API | 用途 | 相关工具 |
|-----|------|---------|
| **OpenAI API** | LLM 推理 | 所有智能体 |
| **SERPER API** | 网络搜索 | web_search, scholar_search |
| **arXiv API** | 学术论文 | arxiv_search |
| **PubMed API** | 生物医学文献 | pubmed_search |

## 工具开发模式

### 输入验证

```python
from pydantic import BaseModel, validator

class CalculatorInput(BaseModel):
    expression: str

    @validator('expression')
    def validate_expression(cls, v):
        # 只允许安全的数学表达式
        allowed_chars = set('0123456789+-*/(). ')
        if not set(v).issubset(allowed_chars):
            raise ValueError("表达式中包含无效字符")
        return v

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "安全地计算数学表达式"

    async def execute(self, expression: str) -> ToolResult:
        try:
            # 验证输入
            validated = CalculatorInput(expression=expression)
            result = eval(validated.expression)  # 验证后安全
            return ToolResult(output=str(result))
        except ValueError as e:
            return ToolResult(error=f"无效的表达式：{e}")
        except Exception as e:
            return ToolResult(error=f"计算失败：{e}")
```

### 异步操作

```python
import asyncio
import httpx

class AsyncWebTool(BaseTool):
    name = "web_search"
    description = "在网络上搜索信息"

    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        try:
            async with httpx.AsyncClient() as client:
                # 多个并发请求
                tasks = [
                    client.get(f"https://api.search.com/search?q={query}&n={max_results}"),
                    client.get(f"https://api.news.com/search?q={query}")
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                results = []
                for response in responses:
                    if isinstance(response, Exception):
                        continue
                    results.extend(response.json().get('results', []))

                return ToolResult(output=results)
        except Exception as e:
            return ToolResult(error=f"搜索失败：{e}")
```

### 用户确认

```python
class DangerousTool(BaseTool):
    name = "delete_files"
    description = "从系统中删除文件"
    user_confirm = True  # 需要用户确认

    async def execute(self, file_path: str) -> ToolResult:
        # 只有在用户确认后才执行
        try:
            os.remove(file_path)
            return ToolResult(output=f"已删除 {file_path}")
        except Exception as e:
            return ToolResult(error=f"删除失败：{e}")
```

### 状态管理

```python
class StatefulTool(BaseTool):
    name = "database_query"
    description = "使用连接池查询数据库"

    def __init__(self):
        super().__init__()
        self.connection_pool = None

    async def _ensure_connection(self):
        if not self.connection_pool:
            self.connection_pool = await create_pool(database_url)

    async def execute(self, query: str) -> ToolResult:
        await self._ensure_connection()
        try:
            async with self.connection_pool.acquire() as conn:
                result = await conn.fetch(query)
                return ToolResult(output=result)
        except Exception as e:
            return ToolResult(error=f"查询失败：{e}")

    async def cleanup(self):
        if self.connection_pool:
            await self.connection_pool.close()
```

## 测试工具

### 单元测试

```python
import pytest
from myagent.tool.base_tool import ToolResult

class TestCalculatorTool:
    @pytest.fixture
    def calculator(self):
        return CalculatorTool()

    @pytest.mark.asyncio
    async def test_basic_calculation(self, calculator):
        result = await calculator.execute(expression="2 + 2")
        assert result.error is None
        assert result.output == "4"

    @pytest.mark.asyncio
    async def test_invalid_expression(self, calculator):
        result = await calculator.execute(expression="2 + + 2")
        assert result.error is not None
        assert "无效" in result.error
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_tool_in_agent():
    agent = create_toolcall_agent(tools=[CalculatorTool()])
    response = await agent.run("5 * 7 等于多少？")
    assert "35" in response
```

## 相关文档

- **[智能体类 API](agents.md)** - 智能体开发参考
- **[自定义工具指南](../guides/custom-tools.md)** - 分步工具开发
- **[示例](../examples/custom-tools.md)** - 工具实现示例
