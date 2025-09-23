# Agent Execution Trace System

这是一个类似LangSmith的Agent执行过程追踪系统，用于监控、调试和评估Agent的执行流程。

## 核心概念

### Trace（追踪）
- 表示一个完整的用户请求执行过程
- 包含多个Run（运行步骤）
- 记录开始时间、结束时间、总耗时、成本等信息

### Run（运行）
- 表示执行过程中的单个操作步骤
- 可以是Agent步骤、工具调用、LLM调用等
- 支持嵌套结构（父子关系）
- 记录输入、输出、错误信息等

### RunType（运行类型）
- `AGENT`: Agent执行步骤
- `TOOL`: 工具调用
- `LLM`: 语言模型调用
- `RETRIEVAL`: 文档检索
- `PREPROCESSING`: 数据预处理
- `POSTPROCESSING`: 数据后处理
- `CHAIN`: 操作链
- `CUSTOM`: 自定义操作

## 主要功能

### 1. 自动追踪
继承自`BaseAgent`和`BaseTool`的类会自动启用追踪功能：

```python
from myagent.agent.base import BaseAgent
from myagent.tool.base_tool import BaseTool

class MyAgent(BaseAgent):
    # 默认启用追踪
    enable_tracing: bool = True

class MyTool(BaseTool):
    # 默认启用追踪
    enable_tracing: bool = True
```

### 2. 手动追踪
使用上下文管理器手动创建追踪：

```python
from myagent.trace import TraceManager, RunType

trace_manager = TraceManager()

async with trace_manager.trace("my_operation", "User request") as trace:
    async with trace_manager.run("step1", RunType.PREPROCESSING) as run:
        # 执行预处理
        result = preprocess_data()
        run.outputs["result"] = result
    
    async with trace_manager.run("step2", RunType.LLM) as run:
        # LLM调用
        response = await llm_call()
        run.outputs["response"] = response
```

### 3. 装饰器追踪
使用装饰器自动追踪函数执行：

```python
from myagent.trace.decorators import trace_run, trace_tool_call

@trace_run(run_type=RunType.CUSTOM)
async def my_function(param1, param2):
    # 函数逻辑
    return result

@trace_tool_call()
async def tool_execute(self, **kwargs):
    # 工具执行逻辑
    return tool_result
```

### 4. 数据查询和分析
使用查询引擎分析追踪数据：

```python
from myagent.trace import TraceQueryEngine, TraceFilter, RunFilter

query_engine = TraceQueryEngine(storage)

# 查询追踪
traces = await query_engine.query_traces(
    filters=TraceFilter(
        start_time=datetime.now() - timedelta(hours=1),
        has_errors=False,
        user_id="user123"
    )
)

# 查询运行
runs = await query_engine.query_runs(
    filters=RunFilter(
        run_type=RunType.TOOL,
        status=RunStatus.SUCCESS
    )
)

# 获取统计信息
stats = await query_engine.get_trace_statistics()
```

### 5. 数据导出
支持多种格式的数据导出：

```python
from myagent.trace import TraceExporter

exporter = TraceExporter(query_engine)

# 导出为JSON
json_data = await exporter.export_traces_to_json()

# 导出为CSV
csv_data = await exporter.export_traces_to_csv()

# 生成摘要报告
summary = await exporter.export_trace_summary()

# 生成追踪树状图
tree = exporter.export_trace_tree(trace)
```

## 使用示例

### 基本使用

```python
import asyncio
from myagent.agent.base import BaseAgent
from myagent.trace import TraceMetadata

class SimpleAgent(BaseAgent):
    async def step(self) -> str:
        # Agent逻辑
        return "Step completed"

async def main():
    # 创建Agent并设置追踪元数据
    metadata = TraceMetadata(
        user_id="user123",
        session_id="session456", 
        tags=["demo", "test"],
        environment="development"
    )
    
    agent = SimpleAgent(
        name="SimpleAgent",
        trace_metadata=metadata
    )
    
    # 运行Agent（自动创建追踪）
    result = await agent.run("Process this request")
    print(f"Result: {result}")

asyncio.run(main())
```

### 工具追踪

```python
from myagent.tool.base_tool import BaseTool, ToolResult

class CalculatorTool(BaseTool):
    name: str = "calculator"
    description: str = "Performs calculations"
    
    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        # 工具逻辑（自动追踪）
        if operation == "add":
            result = a + b
        else:
            raise ValueError("Unsupported operation")
        
        return ToolResult(output=f"Result: {result}")

# 使用工具
tool = CalculatorTool()
result = await tool(operation="add", a=5, b=3)
```

### 查询和分析

```python
from myagent.trace import get_trace_manager, TraceQueryEngine

# 获取追踪管理器
trace_manager = get_trace_manager()
query_engine = TraceQueryEngine(trace_manager.storage)

# 查询最近的追踪
recent_traces = await query_engine.query_traces(
    filters=TraceFilter(
        start_time=datetime.now() - timedelta(hours=24)
    )
)

# 分析错误
error_traces = await query_engine.query_traces(
    filters=TraceFilter(has_errors=True)
)

print(f"Found {error_traces.total_count} traces with errors")

# 获取统计信息
stats = await query_engine.get_trace_statistics()
print(f"Average duration: {stats['avg_duration_ms']:.2f}ms")
print(f"Error rate: {stats['error_rate']:.2%}")
```

## 存储后端

### 内存存储（默认）
```python
from myagent.trace import InMemoryTraceStorage, TraceManager

storage = InMemoryTraceStorage()
manager = TraceManager(storage)
```

### 自定义存储
实现`TraceStorage`接口来支持其他存储后端：

```python
from myagent.trace import TraceStorage

class CustomTraceStorage(TraceStorage):
    async def save_trace(self, trace: Trace) -> None:
        # 实现保存逻辑
        pass
    
    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        # 实现获取逻辑
        pass
    
    # 实现其他必需方法...
```

## 配置

### 全局配置
```python
from myagent.trace import set_trace_manager, TraceManager

# 设置全局追踪管理器
custom_manager = TraceManager(storage=custom_storage)
set_trace_manager(custom_manager)
```

### Agent级别配置
```python
class MyAgent(BaseAgent):
    enable_tracing: bool = True  # 启用/禁用追踪
    trace_metadata: TraceMetadata = TraceMetadata(
        tags=["production"],
        environment="prod"
    )
```

### 工具级别配置
```python
class MyTool(BaseTool):
    enable_tracing: bool = True  # 启用/禁用追踪
```

## 性能考虑

1. **异步操作**: 所有追踪操作都是异步的，不会阻塞主执行流程
2. **内存使用**: 默认使用内存存储，适合开发和测试环境
3. **批量保存**: 支持自动保存，可以关闭以提高性能
4. **过滤查询**: 使用过滤器减少查询数据量

## 最佳实践

1. **合理设置追踪级别**: 在生产环境中可以选择性禁用某些追踪
2. **使用标签和元数据**: 便于后续查询和分析
3. **定期清理数据**: 避免追踪数据过度累积
4. **监控性能影响**: 在高负载场景下监控追踪对性能的影响
5. **错误处理**: 确保追踪失败不影响主要业务逻辑

## 测试

运行测试验证功能：

```bash
# 基本功能测试
python test_trace.py

# 完整演示
python examples/trace_demo.py
```

这个追踪系统为Agent开发和调试提供了强大的可观测性支持，帮助开发者理解Agent的执行流程，识别性能瓶颈和错误模式。