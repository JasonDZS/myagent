# Trace System Architecture

MyAgent框架的trace系统提供了完整的执行追踪和调试能力，采用扁平化架构设计，消除信息冗余，提供清晰的执行流程记录。

## 📊 系统架构概览

### 整体层次结构

```
Trace (执行会话)
└── Agent Step (代理步骤)
    ├── Think (推理阶段)
    ├── Tool_1, Tool_2, ..., Tool_N (工具执行)
    └── Summary (总结阶段) [可选]
```

### 核心设计原则

- **扁平化结构**: 移除冗余的Act层，建立Think→Tools的直接关系
- **信息完整性**: 保留完整的Message对象和工具执行详情
- **层次清晰**: 明确的父子关系，便于追踪和调试
- **存储高效**: 消除重复信息，优化存储空间

## 🏗️ 详细结构说明

### 1. Trace Level (顶层会话)

记录整个对话会话的元信息和执行时间。

```json
{
  "id": "trace-uuid",
  "name": "{agent_name}_execution", 
  "start_time": "2025-09-24T12:00:00.000Z",
  "end_time": "2025-09-24T12:00:10.000Z",
  "request": "用户的原始请求",
  "response": "代理的最终响应",
  "metadata": {
    "agent_name": "mysql_agent",
    "agent_description": "MySQL数据库查询代理",
    "max_steps": 10
  },
  "runs": [...]  // 包含所有子级runs
}
```

**字段说明**:
- `id`: 全局唯一的trace标识符
- `name`: trace名称，通常为"{agent_name}_execution"格式
- `request`: 用户的原始请求内容
- `response`: 代理执行完成后的最终响应
- `metadata`: 包含代理配置和执行参数
- `runs`: 所有子级run的集合

### 2. Agent Step Level (步骤级别)

记录每个ReAct循环步骤的上下文和结果。

```json
{
  "id": "step-uuid",
  "name": "step_N",
  "run_type": "agent", 
  "parent_run_id": null,  // 顶级run
  "status": "success",
  "start_time": "2025-09-24T12:00:01.000Z",
  "end_time": "2025-09-24T12:00:05.000Z",
  "inputs": {
    "step_number": 1,
    "max_steps": 10,
    "agent_state": "RUNNING",
    "memory_size": 5,
    "all_messages": [...],
    "system_prompt": "You are an agent...",
    "next_step_prompt": "If you want to stop..."
  },
  "outputs": {
    "result": "步骤执行结果汇总"
  },
  "latency_ms": 4000.5
}
```

**字段说明**:
- `run_type`: 固定为"agent"
- `parent_run_id`: null表示顶级run
- `inputs`: 包含步骤执行的上下文信息
- `outputs`: 包含步骤执行的结果汇总
- `latency_ms`: 步骤执行耗时（毫秒）

### 3. Think Level (推理阶段)

记录LLM的完整推理过程和工具选择决策。

```json
{
  "id": "think-uuid",
  "name": "think_step_N",
  "run_type": "think",
  "parent_run_id": "step-uuid",  // 直接属于Step
  "status": "success", 
  "start_time": "2025-09-24T12:00:01.000Z",
  "end_time": "2025-09-24T12:00:03.000Z",
  "inputs": {
    "role": "user",
    "content": "Question: 显示用户表的10条数据\n\nGuide: Call mysql_schema for structure...",
    // Message对象的完整结构
  },
  "outputs": {
    "role": "assistant",
    "content": "I'll help you display 10 user records. Let me first check the schema...",
    "tool_calls": [
      {
        "id": "call_xxx",
        "type": "function",
        "function": {
          "name": "mysql_schema", 
          "arguments": "{}"
        }
      }
    ]
    // Message对象的完整结构
  },
  "latency_ms": 2000.3
}
```

**字段说明**:
- `run_type`: 固定为"think"
- `parent_run_id`: 指向对应的Step run
- `inputs`: 完整的用户Message对象（合并了原始请求和指导提示）
- `outputs`: 完整的助手Message对象（包含推理内容和工具调用决策）

### 4. Tool Level (工具执行)

记录每个工具的具体执行参数和结果。

```json
{
  "id": "tool-uuid", 
  "name": "mysql_schema",
  "run_type": "tool",
  "parent_run_id": "step-uuid",  // 直接属于Step
  "status": "success",
  "start_time": "2025-09-24T12:00:03.100Z", 
  "end_time": "2025-09-24T12:00:03.200Z",
  "inputs": {
    "table": "users"  // 工具的实际输入参数
  },
  "outputs": {
    "result": "Schema information: id(int), name(varchar)..."
    // 或使用ToolResult格式: "output": "...", "error": null
  },
  "metadata": {
    "tool_description": "Get MySQL database schema information",
    "tool_parameters": {
      "type": "object", 
      "properties": {
        "table": {
          "type": "string",
          "description": "Optional table name"
        }
      }
    }
  },
  "latency_ms": 100.5
}
```

**字段说明**:
- `run_type`: 固定为"tool"
- `parent_run_id`: 指向对应的Step run（**注意：不是Think run**）
- `inputs`: 工具的实际输入参数
- `outputs`: 工具的执行结果
- `metadata`: 工具的描述和参数定义

### 5. Summary Level (总结阶段)

记录特殊工具执行后的自动总结生成过程。当代理执行完特殊工具（如`terminate`）后，系统会自动生成对话和任务执行的综合总结。

```json
{
  "id": "summary-uuid",
  "name": "final_summary_generation",
  "run_type": "summary",
  "parent_run_id": "step-uuid",  // 直接属于Step
  "status": "success",
  "start_time": "2025-09-24T12:00:05.100Z",
  "end_time": "2025-09-24T12:00:06.200Z",
  "inputs": {
    "summary_prompt": "Please provide a comprehensive summary of the entire conversation...",
    "conversation_messages": [...],  // 清理后的对话历史
    "trigger": "special_tool_execution",
    "special_tool_name": "terminate"
  },
  "outputs": {
    "role": "assistant",
    "content": "## Task Summary\n\n**Original Request**: 显示用户表的10条数据\n\n**Key Steps**:\n1. 检查数据库表结构\n2. 执行查询获取用户数据\n3. 返回查询结果\n\n**Results**: 成功获取并显示了用户表的10条记录...",
    "summary_added_to_memory": true
  },
  "metadata": {
    "summary_type": "automatic_final_summary",
    "message_cleaning_applied": true,
    "original_message_count": 15,
    "cleaned_message_count": 12
  },
  "latency_ms": 1100.0
}
```

**字段说明**:
- `run_type`: 固定为"summary"
- `parent_run_id`: 指向触发总结的Step run
- `inputs`: 包含总结提示词和清理后的对话历史
- `outputs`: 生成的总结内容（完整的助手Message对象）
- `metadata`: 总结生成的元信息，包括消息清理统计

## 🔄 完整执行流程示例

以MySQL查询任务为例，展示完整的trace结构：

```
用户请求: "显示用户表的10条数据"

📋 Trace: mysql_agent_execution
├── 🎯 Step 1 (agent)
│   ├── 🧠 Think (think_step_1)
│   │   ├── Input: "Question: 显示用户表的10条数据\n\nGuide: Call mysql_schema..."
│   │   └── Output: "Let me check the schema first" + [mysql_schema_call]
│   └── 🛠️ mysql_schema (tool)
│       ├── Input: {}
│       └── Output: "Available tables: users, products..."
│       
├── 🎯 Step 2 (agent)
│   ├── 🧠 Think (think_step_2)
│   │   ├── Input: "Call mysql_schema for structure..."
│   │   └── Output: "Now I'll query the users table" + [mysql_query_call]
│   └── 🛠️ mysql_query (tool)
│       ├── Input: {"sql": "SELECT * FROM users LIMIT 10"}
│       └── Output: "Query results: [user_data...]"
│       
└── 🎯 Step 3 (agent)
    ├── 🧠 Think (think_step_3)  
    │   ├── Input: "Call mysql_query for data..."
    │   └── Output: "Task completed" + [terminate_call]
    ├── 🛠️ terminate (tool)
    │   ├── Input: {"status": "success"}
    │   └── Output: "Interaction completed"
    └── 📝 final_summary_generation (summary)
        ├── Input: summary_prompt + cleaned_messages
        └── Output: "## Task Summary\n\n**Original Request**: 显示用户表的10条数据..."
```

## 📈 关键特性

### ✅ 消除信息冗余

**之前的问题**:
- Act层重复了Think的工具调用信息
- Act层重复了Tool的执行结果
- 存储空间浪费，信息查找困难

**现在的解决方案**:
- Think记录推理决策，Tool记录执行结果
- 没有中间的Act层重复包装
- 每层信息独立且完整

### ✅ 扁平化层次结构

```
Step (代理步骤)
├── Think (推理阶段) - 直接子级
├── Tool (工具执行) - 直接子级
└── Summary (总结阶段) - 直接子级 [可选]
```

- Think、Tool和Summary都是Step的直接子级
- 没有不必要的嵌套层次
- 父子关系清晰明确
- Summary仅在特殊工具执行后自动触发

### ✅ 完整信息保存

**Think阶段**:
- 输入：完整的用户Message对象（包含合并后的请求和指导）
- 输出：完整的助手Message对象（包含推理内容和工具调用）

**Tool阶段**:
- 输入：工具的实际执行参数
- 输出：工具的执行结果
- 元数据：工具的描述和参数定义

**Summary阶段** [可选]:
- 输入：总结提示词和清理后的对话历史
- 输出：完整的总结Message对象（包含任务概览、关键步骤、结果等）
- 元数据：总结类型、消息清理统计信息

## 🛠️ 使用场景

### 1. 调试和问题排查

```python
# 查找推理问题
think_runs = find_runs_by_type(trace_data, 'think')
for run in think_runs:
    if 'error' in run.get('outputs', {}):
        print(f"Think error in step {run['name']}: {run['outputs']['error']}")

# 查找工具执行问题  
tool_runs = find_runs_by_type(trace_data, 'tool')
for run in tool_runs:
    if run.get('status') == 'error':
        print(f"Tool error: {run['name']} - {run.get('error')}")

# 查找总结生成问题
summary_runs = find_runs_by_type(trace_data, 'summary')
for run in summary_runs:
    if run.get('status') == 'error':
        print(f"Summary error: {run.get('error')}")
    else:
        print(f"Summary generated: {run['outputs']['content'][:100]}...")
```

### 2. 性能监控和分析

```python
# 分析推理时间
think_times = [run['latency_ms'] for run in think_runs]
avg_think_time = sum(think_times) / len(think_times)

# 分析工具执行时间
tool_times = {run['name']: run['latency_ms'] for run in tool_runs}
slowest_tool = max(tool_times, key=tool_times.get)

# 分析总结生成时间
summary_runs = find_runs_by_type(trace_data, 'summary')
if summary_runs:
    summary_time = summary_runs[0]['latency_ms']
    print(f"Summary generation took: {summary_time}ms")
```

### 3. 行为模式分析

```python
# 分析工具使用频率
tool_usage = {}
for run in tool_runs:
    tool_name = run['name']
    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

# 分析推理模式
for run in think_runs:
    tool_calls = run.get('outputs', {}).get('tool_calls', [])
    print(f"Step {run['name']}: {len(tool_calls)} tools called")

# 分析总结质量和内容
summary_runs = find_runs_by_type(trace_data, 'summary')
for run in summary_runs:
    summary_content = run.get('outputs', {}).get('content', '')
    metadata = run.get('metadata', {})
    print(f"Summary triggered by: {metadata.get('special_tool_name', 'unknown')}")
    print(f"Message cleaning: {metadata.get('original_message_count', 0)} -> {metadata.get('cleaned_message_count', 0)}")
    print(f"Summary length: {len(summary_content)} characters")
```

## 📝 最佳实践

### 1. 启用Trace

```python
# 创建支持trace的代理
agent = create_react_agent(
    name="my_agent",
    tools=[tool1, tool2],
    enable_tracing=True  # 启用trace
)

# 执行并自动记录trace（包括自动总结）
result = await agent.run("用户请求")

# 自动总结会在特殊工具（如terminate）执行后生成
# 可以通过agent.final_response访问最终总结
print(f"Final summary: {agent.final_response}")
```

### 2. 导出和分析Trace

```python
from myagent.trace import TraceQueryEngine, TraceExporter, get_trace_manager

# 获取trace数据
trace_manager = get_trace_manager()
query_engine = TraceQueryEngine(trace_manager.storage)
exporter = TraceExporter(query_engine)

# 导出为JSON
json_data = await exporter.export_traces_to_json()

# 导出统计报告
summary = await exporter.export_trace_summary()
```

### 3. 自定义工具的Trace支持

```python
from myagent.tool import BaseTool

class MyCustomTool(BaseTool):
    name = "my_tool"
    description = "My custom tool"
    
    async def execute(self, param1: str, param2: int) -> str:
        # 工具逻辑
        result = f"Processing {param1} with {param2}"
        return result
        
# Trace会自动记录inputs: {"param1": "...", "param2": 123}
# 和outputs: {"result": "Processing ... with 123"}
```

这种trace系统架构提供了完整、高效且易于分析的执行追踪能力，是调试、监控和优化Agent行为的强大工具。