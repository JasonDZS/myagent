# Tool System API Reference

This document provides comprehensive API reference for MyAgent's tool system, including base classes, built-in tools, and tool management.

## Core Classes

### BaseTool

Abstract base class for all tools. All custom tools must inherit from this class.

```python
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult

class BaseTool(ABC):
    name: str
    description: str
    user_confirm: bool = False
    enable_tracing: bool = True
```

#### Required Attributes

- `name`: Unique identifier for the tool (used by LLM and agent)
- `description`: Human-readable description of what the tool does

#### Optional Attributes

- `user_confirm`: If True, requires user confirmation before execution
- `enable_tracing`: If True, tool execution is traced (default: True)

#### Abstract Methods

##### execute()
```python
@abstractmethod
async def execute(self, **kwargs) -> ToolResult:
    """Execute the tool with given parameters"""
    pass
```

**Parameters:** Variable keyword arguments based on tool requirements

**Returns:** `ToolResult` instance

**Must be implemented** by all concrete tool classes.

#### Example Implementation

```python
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult
import httpx

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather information for a specified location"
    user_confirm = False
    
    async def execute(self, location: str) -> ToolResult:
        """Get weather for a location"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.weather.com/{location}")
                weather_data = response.json()
                
            return ToolResult(
                output=f"Weather in {location}: {weather_data['description']}, {weather_data['temperature']}°F"
            )
        except Exception as e:
            return ToolResult(error=f"Failed to get weather: {str(e)}")
```

### ToolResult

Standardized result format for all tool executions.

```python
from pydantic import BaseModel, Field
from typing import Any, Optional

class ToolResult(BaseModel):
    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)
```

#### Fields

- `output`: Successful tool execution result (any type)
- `error`: Error message if tool execution failed
- `base64_image`: Optional base64-encoded image data

#### Usage Examples

```python
# Successful execution
return ToolResult(output="Task completed successfully")

# Error result
return ToolResult(error="Invalid input provided")

# Result with image
return ToolResult(
    output="Generated chart",
    base64_image="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
)

# Mixed result
return ToolResult(
    output="Analysis complete with warnings",
    error="Some data points were missing"
)
```

### ToolCollection

Manages a collection of tools and provides access methods.

```python
class ToolCollection:
    def __init__(self, *tools: BaseTool):
        """Initialize with tools"""
        
    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the collection"""
        
    def remove_tool(self, name: str) -> None:
        """Remove a tool by name"""
        
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        
    def list_tools(self) -> list[str]:
        """List all tool names"""
        
    async def execute(self, *, name: str, tool_input: dict) -> ToolResult:
        """Execute a tool by name"""
```

#### Constructor

```python
def __init__(self, *tools: BaseTool)
```

Create a collection with initial tools.

**Parameters:**
- `*tools`: Variable number of BaseTool instances

**Example:**
```python
collection = ToolCollection(
    WeatherTool(),
    CalculatorTool(),
    SearchTool()
)
```

#### Methods

##### add_tool()
```python
def add_tool(self, tool: BaseTool) -> None
```

Add a tool to the collection.

**Parameters:**
- `tool`: BaseTool instance to add

**Raises:**
- `ValueError`: If tool name already exists

**Example:**
```python
collection.add_tool(WeatherTool())
```

##### remove_tool()
```python
def remove_tool(self, name: str) -> None
```

Remove a tool by name.

**Parameters:**
- `name`: Name of tool to remove

**Raises:**
- `KeyError`: If tool name doesn't exist

**Example:**
```python
collection.remove_tool("weather")
```

##### get_tool()
```python
def get_tool(self, name: str) -> Optional[BaseTool]
```

Retrieve a tool by name.

**Parameters:**
- `name`: Tool name to retrieve

**Returns:** Tool instance or None if not found

**Example:**
```python
weather_tool = collection.get_tool("weather")
if weather_tool:
    result = await weather_tool.execute(location="New York")
```

##### list_tools()
```python
def list_tools(self) -> list[str]
```

Get list of all tool names.

**Returns:** List of tool name strings

**Example:**
```python
tool_names = collection.list_tools()
print(f"Available tools: {', '.join(tool_names)}")
```

##### execute()
```python
async def execute(self, *, name: str, tool_input: dict) -> ToolResult
```

Execute a tool by name with parameters.

**Parameters:**
- `name`: Name of tool to execute
- `tool_input`: Dictionary of parameters to pass to tool

**Returns:** ToolResult from tool execution

**Raises:**
- `KeyError`: If tool name doesn't exist
- `Exception`: Any exception from tool execution

**Example:**
```python
result = await collection.execute(
    name="weather",
    tool_input={"location": "San Francisco"}
)
```

#### Properties

##### tool_names
```python
@property
def tool_names(self) -> list[str]:
```

Get list of all tool names (alias for `list_tools()`).

##### tool_map
```python
@property  
def tool_map(self) -> dict[str, BaseTool]:
```

Get dictionary mapping tool names to tool instances.

## Built-in Tools

### System Tools

#### Terminate

Special tool that allows agents to signal task completion.

```python
from myagent.tool import Terminate

class Terminate(BaseTool):
    name = "terminate"
    description = "Signal that the task is complete"
    user_confirm = False
```

**Automatically added** to all agents created via factory functions.

**Usage:**

The agent uses this tool when it determines the conversation is complete:

```python
# Agent will use terminate tool when task is done
response = await agent.run("What is 2 + 2?")
# Agent calculates, provides answer, then calls terminate
```

**Custom Terminate Behavior:**

```python
class CustomTerminate(BaseTool):
    name = "finish_task"
    description = "Mark the current task as finished with summary"

    async def execute(self, summary: str = "") -> ToolResult:
        return ToolResult(output=f"Task completed: {summary}")

# Use in agent
agent = create_toolcall_agent(tools=[CustomTerminate()])
```

### Deep Agent Tools

These tools are automatically included when using `create_deep_agent()`.

#### Planning Tools

**Module:** `myagent.tool.planning`

##### write_todos

Create or update task list with TODOs.

```python
from myagent.tool.planning import WriteTodosTool

class WriteTodosTool(BaseTool):
    name = "write_todos"
    description = "Create or update a list of tasks to accomplish"
```

**Parameters:**
- `todos` (list): List of task descriptions to create

**Returns:** Confirmation message with task count

**Example:**
```python
result = await write_todos_tool.execute(
    todos=["Research LLM agents", "Write report", "Create presentation"]
)
# Output: "✅ Created 3 TODOs"
```

##### read_todos

Read current task list.

```python
from myagent.tool.planning import ReadTodosTool

class ReadTodosTool(BaseTool):
    name = "read_todos"
    description = "Read the current list of tasks"
```

**Returns:** Formatted list of tasks with status indicators

**Example:**
```python
result = await read_todos_tool.execute()
# Output:
# 📋 Current Tasks:
# ⏳ 1. Research LLM agents
# ⏳ 2. Write report
# ⏳ 3. Create presentation
```

##### complete_todo

Mark a task as completed.

```python
from myagent.tool.planning import CompleteTodoTool

class CompleteTodoTool(BaseTool):
    name = "complete_todo"
    description = "Mark a task as completed"
```

**Parameters:**
- `task_index` (int): Index of task to complete (1-based)

**Returns:** Confirmation message

**Example:**
```python
result = await complete_todo_tool.execute(task_index=1)
# Output: "✅ Completed task 1: Research LLM agents"
```

**Factory Function:**
```python
from myagent.tool.planning import create_planning_tools

tools = create_planning_tools()
# Returns: [WriteTodosTool(), ReadTodosTool(), CompleteTodoTool()]
```

#### FileSystem Tools

**Module:** `myagent.tool.filesystem`

These tools provide a virtual file system with disk persistence.

##### ls

List files in the workspace.

```python
from myagent.tool.filesystem import ListFilesTool

class ListFilesTool(BaseTool):
    name = "ls"
    description = "List all files in the virtual file system with their sizes"
```

**Returns:** Formatted file listing with sizes

**Example:**
```python
result = await ls_tool.execute()
# Output:
# 📁 Virtual File System Contents:
# 📄 report.md (2.5 KB)
# 📄 data/results.json (15.3 KB)
# 📊 Total: 2 file(s)
```

##### read_file

Read file contents with line numbers.

```python
from myagent.tool.filesystem import ReadFileTool

class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read content from a file in the virtual file system"
```

**Parameters:**
- `file_path` (str): Path to file
- `line_offset` (int, optional): Starting line (0-based)
- `limit` (int, optional): Maximum lines to read

**Returns:** File content with line numbers

**Example:**
```python
result = await read_file_tool.execute(file_path="report.md")
# Output:
# 📄 File: report.md
#    1  # Research Report
#    2
#    3  ## Introduction
#    4  This report covers...
```

##### write_file

Write content to a file (persists to disk).

```python
from myagent.tool.filesystem import WriteFileTool

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file (overwrites existing)"
```

**Parameters:**
- `file_path` (str): Path to file
- `content` (str): Content to write

**Returns:** Confirmation with file size

**Example:**
```python
result = await write_file_tool.execute(
    file_path="report.md",
    content="# Research Report\n\n## Introduction\n..."
)
# Output: "✅ Created file: report.md (1.2 KB)"
# File is automatically saved to workspace/report.md
```

##### edit_file

Edit file by replacing text.

```python
from myagent.tool.filesystem import EditFileTool

class EditFileTool(BaseTool):
    name = "edit_file"
    description = "Edit a file by replacing specific text content"
```

**Parameters:**
- `file_path` (str): Path to file
- `old_string` (str): Text to find
- `new_string` (str): Replacement text
- `replace_all` (bool, optional): Replace all occurrences

**Returns:** Confirmation with change summary

**Example:**
```python
result = await edit_file_tool.execute(
    file_path="report.md",
    old_string="## Introduction",
    new_string="## Executive Summary"
)
# Output: "✅ File Edit Successful: report.md"
```

**Factory Function:**
```python
from myagent.tool.filesystem import get_filesystem_tools

tools = get_filesystem_tools()
# Returns: [ListFilesTool(), ReadFileTool(), WriteFileTool(), EditFileTool()]
```

**Persistence:**
- All files automatically saved to `workspace/` directory
- Supports subdirectories (e.g., `data/results.md`)
- Files loaded on startup from disk
- Changes immediately persisted

#### SubAgent Tools

**Module:** `myagent.tool.subagent`

##### create_subagent

Create and run a sub-agent for delegated tasks.

```python
from myagent.tool.subagent import CreateSubAgentTool

class CreateSubAgentTool(BaseTool):
    name = "create_subagent"
    description = "Create a sub-agent to handle a specific subtask"
```

**Parameters:**
- `task` (str): Task description for sub-agent
- `tools` (list[str], optional): Tool names to provide to sub-agent

**Returns:** Sub-agent execution result

**Example:**
```python
result = await create_subagent_tool.execute(
    task="Analyze the data in results.csv and summarize key findings",
    tools=["read_file", "analyze_data"]
)
# Sub-agent runs independently and returns results
```

**Factory Function:**
```python
from myagent.tool.subagent import create_subagent_tools

tools = create_subagent_tools(parent_agent)
# Returns: [CreateSubAgentTool(parent_agent)]
```

### Research Tools

Advanced tools for information gathering and analysis.

#### Web Search Tools

**Module:** `myagent.tool.web_search`

##### web_search

Search the web using SERPER API.

```python
from myagent.tool.web_search import WebSearchTool

class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information"
```

**Parameters:**
- `query` (str): Search query
- `max_results` (int, optional): Maximum results (default: 10)

**Returns:** Formatted search results with titles, URLs, and snippets

**Requirements:**
- `SERPER_API_KEY` environment variable

**Example:**
```python
result = await web_search_tool.execute(
    query="LLM agents 2024",
    max_results=5
)
# Output:
# 🔍 Search Results for: "LLM agents 2024"
#
# 1. **Building LLM Agents in 2024**
#    https://example.com/llm-agents
#    Learn how to build autonomous LLM agents...
```

##### scholar_search

Academic search using Google Scholar.

```python
from myagent.tool.web_search import ScholarSearchTool

class ScholarSearchTool(BaseTool):
    name = "scholar_search"
    description = "Search academic papers and research"
```

**Parameters:**
- `query` (str): Search query
- `max_results` (int, optional): Maximum results

**Returns:** Academic search results

**Factory Function:**
```python
from myagent.tool.web_search import create_search_tools

tools = create_search_tools()
# Returns: [WebSearchTool(), ScholarSearchTool()]
```

#### Academic Search Tools

**Module:** `myagent.tool.academic_search`

##### arxiv_search

Search arXiv preprint repository.

```python
from myagent.tool.academic_search import ArxivSearchTool

class ArxivSearchTool(BaseTool):
    name = "arxiv_search"
    description = "Search arXiv for academic papers"
```

**Parameters:**
- `query` (str): Search query
- `max_results` (int, optional): Maximum results (default: 10)
- `category` (str, optional): arXiv category filter

**Returns:** Formatted paper results with titles, authors, abstracts, and URLs

**Example:**
```python
result = await arxiv_search_tool.execute(
    query="transformer architecture",
    max_results=5,
    category="cs.AI"
)
# Output:
# 📚 arXiv Search Results: "transformer architecture"
#
# 1. **Attention Is All You Need**
#    Authors: Vaswani et al.
#    Published: 2017-06-12
#    Abstract: The dominant sequence transduction models...
#    URL: https://arxiv.org/abs/1706.03762
```

##### pubmed_search

Search PubMed biomedical literature.

```python
from myagent.tool.academic_search import PubMedSearchTool

class PubMedSearchTool(BaseTool):
    name = "pubmed_search"
    description = "Search PubMed for biomedical research papers"
```

**Parameters:**
- `query` (str): Search query
- `max_results` (int, optional): Maximum results

**Returns:** PubMed article results

**Factory Function:**
```python
from myagent.tool.academic_search import create_academic_tools

tools = create_academic_tools()
# Returns: [ArxivSearchTool(), PubMedSearchTool()]
```

#### Data Analysis Tools

**Module:** `myagent.tool.data_analysis`

##### analyze_data

Perform statistical analysis on data.

```python
from myagent.tool.data_analysis import DataAnalysisTool

class DataAnalysisTool(BaseTool):
    name = "analyze_data"
    description = "Analyze data with pandas and numpy"
```

**Parameters:**
- `data_source` (str): Data description or file path
- `analysis_type` (str): Type of analysis (trend, correlation, summary)

**Returns:** Analysis results with statistics and insights

**Example:**
```python
result = await analyze_data_tool.execute(
    data_source="sales_data_2024",
    analysis_type="trend"
)
# Output:
# 📊 Data Analysis Results
#
# Trend Analysis for sales_data_2024:
# - Mean: 125.4
# - Median: 118.2
# - Std Dev: 32.1
# - Trend: ↗ Increasing (+15.3% over period)
```

**Factory Function:**
```python
from myagent.tool.data_analysis import create_data_analysis_tools

tools = create_data_analysis_tools()
# Returns: [DataAnalysisTool()]
```

#### Web Content Tools

**Module:** `myagent.tool.web_content`

##### fetch_content

Fetch and parse web page content.

```python
from myagent.tool.web_content import WebContentTool

class WebContentTool(BaseTool):
    name = "fetch_content"
    description = "Fetch and extract content from web pages"
```

**Parameters:**
- `url` (str): URL to fetch
- `extract_type` (str, optional): Content extraction type (text, links, images)

**Returns:** Extracted and formatted web content

**Example:**
```python
result = await fetch_content_tool.execute(
    url="https://example.com/article",
    extract_type="text"
)
# Output:
# 🌐 Content from: https://example.com/article
#
# Title: Understanding LLM Agents
#
# Article content extracted and cleaned...
```

**Factory Function:**
```python
from myagent.tool.web_content import create_web_content_tools

tools = create_web_content_tools()
# Returns: [WebContentTool()]
```

#### Code Execution Tools

**Module:** `myagent.tool.code_execution`

##### execute_code

Execute Python code with automatic matplotlib plot saving.

```python
from myagent.tool.code_execution import CodeExecutionTool

class CodeExecutionTool(BaseTool):
    name = "execute_code"
    description = "Execute Python code with data science libraries"
```

**Parameters:**
- `code` (str): Python code to execute
- `timeout` (int, optional): Execution timeout in seconds (default: 30)

**Returns:** Execution output, errors, and saved plot locations

**Features:**
- Session state persistence (variables retained between executions)
- Automatic matplotlib plot saving to `workspace/images/`
- Pre-imported libraries: pandas, numpy, matplotlib
- High-resolution plot output (300 DPI)

**Example:**
```python
result = await execute_code_tool.execute(
    code="""
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.grid(True)
# No need to call plt.savefig() - automatic!
"""
)
# Output:
# 📊 已保存图片 (1 个):
#   - workspace/images/plot_1759201785051_0.png
#
# 当前会话变量: x(ndarray), y(ndarray), plt(module)
```

**Factory Function:**
```python
from myagent.tool.code_execution import create_code_execution_tools

tools = create_code_execution_tools()
# Returns: [CodeExecutionTool()]
```

**Important Notes:**
- matplotlib uses 'Agg' backend (non-interactive)
- All open figures automatically saved
- Plots saved to `workspace/images/plot_<timestamp>_<index>.png`
- Session variables persist across executions

## Tool Development Patterns

### Input Validation

```python
from pydantic import BaseModel, validator

class CalculatorInput(BaseModel):
    expression: str
    
    @validator('expression')
    def validate_expression(cls, v):
        # Only allow safe mathematical expressions
        allowed_chars = set('0123456789+-*/(). ')
        if not set(v).issubset(allowed_chars):
            raise ValueError("Invalid characters in expression")
        return v

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Evaluate mathematical expressions safely"
    
    async def execute(self, expression: str) -> ToolResult:
        try:
            # Validate input
            validated = CalculatorInput(expression=expression)
            result = eval(validated.expression)  # Safe after validation
            return ToolResult(output=str(result))
        except ValueError as e:
            return ToolResult(error=f"Invalid expression: {e}")
        except Exception as e:
            return ToolResult(error=f"Calculation failed: {e}")
```

### Async Operations

```python
import asyncio
import httpx

class AsyncWebTool(BaseTool):
    name = "web_search"
    description = "Search the web for information"
    
    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        try:
            async with httpx.AsyncClient() as client:
                # Multiple concurrent requests
                tasks = [
                    client.get(f"https://api.search.com/search?q={query}&n={max_results}"),
                    client.get(f"https://api.news.com/search?q={query}")
                ]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                results = []
                for response in responses:
                    if isinstance(response, Exception):
                        continue
                    results.extend(response.json().get('results', []))
                
                return ToolResult(output=results)
        except Exception as e:
            return ToolResult(error=f"Search failed: {e}")
```

### User Confirmation

```python
class DangerousTool(BaseTool):
    name = "delete_files"
    description = "Delete files from the system"
    user_confirm = True  # Requires user confirmation
    
    async def execute(self, file_path: str) -> ToolResult:
        # This will only execute after user confirms
        try:
            os.remove(file_path)
            return ToolResult(output=f"Deleted {file_path}")
        except Exception as e:
            return ToolResult(error=f"Failed to delete: {e}")
```

### State Management

```python
class StatefulTool(BaseTool):
    name = "database_query"
    description = "Query database with connection pooling"
    
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
            return ToolResult(error=f"Query failed: {e}")
    
    async def cleanup(self):
        if self.connection_pool:
            await self.connection_pool.close()
```

### Error Handling Strategies

```python
class RobustTool(BaseTool):
    name = "resilient_api"
    description = "API tool with retry logic and fallbacks"
    
    async def execute(self, endpoint: str, **params) -> ToolResult:
        # Strategy 1: Retry with exponential backoff
        for attempt in range(3):
            try:
                result = await self._api_call(endpoint, **params)
                return ToolResult(output=result)
            except httpx.TimeoutException:
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return ToolResult(error="API timeout after retries")
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    # Server error, try fallback
                    fallback_result = await self._fallback_method(endpoint, **params)
                    return ToolResult(output=fallback_result)
                else:
                    # Client error, don't retry
                    return ToolResult(error=f"API error: {e.response.status_code}")
        
        return ToolResult(error="All retry attempts failed")
```

## Advanced Tool Features

### Tool Chaining

```python
class ChainableTool(BaseTool):
    def __init__(self, next_tool: Optional[BaseTool] = None):
        super().__init__()
        self.next_tool = next_tool
    
    async def execute(self, **kwargs) -> ToolResult:
        # Process current tool
        result = await self._process(**kwargs)
        
        # Chain to next tool if available
        if self.next_tool and result.error is None:
            chained_result = await self.next_tool.execute(**result.output)
            return chained_result
        
        return result
```

### Tool Composition

```python
class CompositeTool(BaseTool):
    name = "multi_step_analysis"
    description = "Perform multi-step data analysis"
    
    def __init__(self, tools: list[BaseTool]):
        super().__init__()
        self.tools = {tool.name: tool for tool in tools}
    
    async def execute(self, data: str, steps: list[str]) -> ToolResult:
        current_data = data
        results = []
        
        for step in steps:
            if step not in self.tools:
                return ToolResult(error=f"Unknown step: {step}")
            
            tool = self.tools[step]
            result = await tool.execute(data=current_data)
            
            if result.error:
                return result
            
            results.append(result.output)
            current_data = result.output
        
        return ToolResult(output=results)
```

## Performance Optimization

### Caching

```python
from functools import lru_cache
import pickle

class CachedTool(BaseTool):
    name = "cached_computation"
    description = "Expensive computation with caching"
    
    def __init__(self):
        super().__init__()
        self.cache = {}
    
    def _cache_key(self, **kwargs) -> str:
        return pickle.dumps(sorted(kwargs.items()))
    
    async def execute(self, **kwargs) -> ToolResult:
        cache_key = self._cache_key(**kwargs)
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Expensive computation
        result = await self._compute(**kwargs)
        
        # Cache the result
        self.cache[cache_key] = result
        return result
```

### Connection Pooling

```python
import aiohttp

class PooledHTTPTool(BaseTool):
    _session: Optional[aiohttp.ClientSession] = None
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None:
            cls._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=100),
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return cls._session
    
    async def execute(self, url: str) -> ToolResult:
        session = await self.get_session()
        try:
            async with session.get(url) as response:
                data = await response.text()
                return ToolResult(output=data)
        except Exception as e:
            return ToolResult(error=str(e))
```

## Testing Tools

### Unit Testing

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
        assert "Invalid" in result.error
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_tool_in_agent():
    agent = create_toolcall_agent(tools=[CalculatorTool()])
    response = await agent.run("What is 5 * 7?")
    assert "35" in response
```

### Mock Tools

```python
class MockAPITool(BaseTool):
    name = "mock_api"
    description = "Mock API for testing"
    
    def __init__(self, responses: dict):
        super().__init__()
        self.responses = responses
    
    async def execute(self, endpoint: str) -> ToolResult:
        if endpoint in self.responses:
            return ToolResult(output=self.responses[endpoint])
        return ToolResult(error="Endpoint not found")
```

## See Also

- **[Agent Classes API](agents.md)** - Agent development reference
- **[Schema Types API](schema.md)** - Data type reference
- **[Custom Tools Guide](../guides/custom-tools.md)** - Step-by-step tool development
- **[Examples](../examples/custom-tools.md)** - Tool implementation examples