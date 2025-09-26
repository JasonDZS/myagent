# Trace系统使用指南

本指南详细介绍如何在MyAgent框架中使用trace系统进行调试、监控和分析。

## 🚀 快速开始

### 启用Trace功能

```python
from myagent import create_react_agent
from myagent.tool import Terminate

# 创建支持trace的代理
agent = create_react_agent(
    name="demo_agent",
    tools=[Terminate()],
    enable_tracing=True  # 启用trace功能
)

# 执行任务，自动记录trace
result = await agent.run("你的请求")
```

### 导出Trace数据

```python
from myagent.trace import TraceQueryEngine, TraceExporter, get_trace_manager

async def export_traces():
    # 获取trace管理器
    trace_manager = get_trace_manager()
    query_engine = TraceQueryEngine(trace_manager.storage)
    exporter = TraceExporter(query_engine)

    # 导出为JSON格式
    json_data = await exporter.export_traces_to_json()

    # 保存到文件
    with open("traces/my_trace.json", "w", encoding="utf-8") as f:
        f.write(json_data)

    # 导出统计报告
    summary = await exporter.export_trace_summary()
    print(summary)
```

## 📊 Trace数据分析

### 基础数据结构分析

```python
import json

def analyze_trace_structure(trace_file):
    """分析trace文件的基础结构"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        trace_data = json.load(f)

    # 提取所有runs
    runs = []
    for trace in trace_data.get('traces', []):
        runs.extend(trace.get('runs', []))

    # 按类型分组
    runs_by_type = {}
    for run in runs:
        run_type = run.get('run_type')
        if run_type not in runs_by_type:
            runs_by_type[run_type] = []
        runs_by_type[run_type].append(run)

    # 打印统计信息
    print("=== Trace Structure Analysis ===")
    for run_type, run_list in runs_by_type.items():
        print(f"{run_type.upper()} runs: {len(run_list)}")

    return runs_by_type

# 使用示例
runs_by_type = analyze_trace_structure("traces/my_trace.json")
```

### 推理过程分析

```python
def analyze_thinking_process(runs_by_type):
    """分析Agent的推理过程"""
    think_runs = runs_by_type.get('think', [])

    print("\\n=== Thinking Process Analysis ===")
    for i, run in enumerate(think_runs, 1):
        print(f"\\n--- Step {i} Think ---")

        # 输入分析
        inputs = run.get('inputs', {})
        user_content = inputs.get('content', '')
        print(f"User Input: {user_content[:100]}...")

        # 输出分析
        outputs = run.get('outputs', {})
        assistant_content = outputs.get('content', '')
        tool_calls = outputs.get('tool_calls', [])

        print(f"Assistant Response: {assistant_content[:100]}...")
        print(f"Tools Planned: {[call['function']['name'] for call in tool_calls]}")
        print(f"Think Time: {run.get('latency_ms', 0):.2f}ms")

# 使用示例
analyze_thinking_process(runs_by_type)
```

### 工具使用分析

```python
def analyze_tool_usage(runs_by_type):
    """分析工具使用情况"""
    tool_runs = runs_by_type.get('tool', [])

    # 工具使用频率统计
    tool_frequency = {}
    tool_performance = {}

    for run in tool_runs:
        tool_name = run.get('name')
        latency = run.get('latency_ms', 0)
        status = run.get('status', 'unknown')

        # 频率统计
        if tool_name not in tool_frequency:
            tool_frequency[tool_name] = {'success': 0, 'error': 0, 'total': 0}

        tool_frequency[tool_name]['total'] += 1
        if status == 'success':
            tool_frequency[tool_name]['success'] += 1
        else:
            tool_frequency[tool_name]['error'] += 1

        # 性能统计
        if tool_name not in tool_performance:
            tool_performance[tool_name] = []
        tool_performance[tool_name].append(latency)

    print("\\n=== Tool Usage Analysis ===")
    for tool_name, freq in tool_frequency.items():
        success_rate = freq['success'] / freq['total'] * 100
        avg_latency = sum(tool_performance[tool_name]) / len(tool_performance[tool_name])

        print(f"\\n{tool_name}:")
        print(f"  Total Calls: {freq['total']}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Average Latency: {avg_latency:.2f}ms")

# 使用示例
analyze_tool_usage(runs_by_type)
```

### 性能分析

```python
def analyze_performance(runs_by_type):
    """分析执行性能"""
    agent_runs = runs_by_type.get('agent', [])
    think_runs = runs_by_type.get('think', [])
    tool_runs = runs_by_type.get('tool', [])

    print("\\n=== Performance Analysis ===")

    # Agent步骤分析
    if agent_runs:
        step_times = [run.get('latency_ms', 0) for run in agent_runs]
        print(f"\\nAgent Steps:")
        print(f"  Total Steps: {len(step_times)}")
        print(f"  Total Time: {sum(step_times):.2f}ms")
        print(f"  Average Step Time: {sum(step_times)/len(step_times):.2f}ms")

    # 推理时间分析
    if think_runs:
        think_times = [run.get('latency_ms', 0) for run in think_runs]
        print(f"\\nThinking Performance:")
        print(f"  Total Think Time: {sum(think_times):.2f}ms")
        print(f"  Average Think Time: {sum(think_times)/len(think_times):.2f}ms")
        print(f"  Min/Max Think Time: {min(think_times):.2f}ms / {max(think_times):.2f}ms")

    # 工具执行时间分析
    if tool_runs:
        tool_times = [run.get('latency_ms', 0) for run in tool_runs]
        print(f"\\nTool Execution Performance:")
        print(f"  Total Tool Time: {sum(tool_times):.2f}ms")
        print(f"  Average Tool Time: {sum(tool_times)/len(tool_times):.2f}ms")

        # 最慢的工具
        slowest_tool = max(tool_runs, key=lambda x: x.get('latency_ms', 0))
        print(f"  Slowest Tool: {slowest_tool.get('name')} ({slowest_tool.get('latency_ms', 0):.2f}ms)")

# 使用示例
analyze_performance(runs_by_type)
```

## 🐛 调试场景

### 查找推理错误

```python
def debug_thinking_issues(runs_by_type):
    """调试推理相关问题"""
    think_runs = runs_by_type.get('think', [])

    print("\\n=== Thinking Issues Debug ===")

    for i, run in enumerate(think_runs, 1):
        # 检查是否有错误
        if run.get('status') != 'success':
            print(f"\\n❌ Think Step {i} Error:")
            print(f"  Error: {run.get('error')}")
            print(f"  Error Type: {run.get('error_type')}")

        # 检查异常长的推理时间
        latency = run.get('latency_ms', 0)
        if latency > 10000:  # 超过10秒
            print(f"\\n⚠️  Think Step {i} Slow Performance:")
            print(f"  Latency: {latency:.2f}ms")
            print(f"  Input Length: {len(run.get('inputs', {}).get('content', ''))}")

        # 检查无工具调用的情况
        outputs = run.get('outputs', {})
        tool_calls = outputs.get('tool_calls', [])
        if not tool_calls and 'terminate' not in outputs.get('content', '').lower():
            print(f"\\n🤔 Think Step {i} No Tool Calls:")
            print(f"  Response: {outputs.get('content', '')[:200]}...")

# 使用示例
debug_thinking_issues(runs_by_type)
```

### 查找工具执行错误

```python
def debug_tool_issues(runs_by_type):
    """调试工具执行问题"""
    tool_runs = runs_by_type.get('tool', [])

    print("\\n=== Tool Issues Debug ===")

    error_count = 0
    for run in tool_runs:
        if run.get('status') != 'success':
            error_count += 1
            print(f"\\n❌ Tool Error #{error_count}:")
            print(f"  Tool: {run.get('name')}")
            print(f"  Error: {run.get('error')}")
            print(f"  Inputs: {run.get('inputs', {})}")

            # 查看相关的Think决策
            parent_id = run.get('parent_run_id')
            print(f"  Parent Step ID: {parent_id}")

    # 查找执行时间异常的工具
    slow_tools = []
    for run in tool_runs:
        latency = run.get('latency_ms', 0)
        if latency > 5000:  # 超过5秒
            slow_tools.append((run.get('name'), latency))

    if slow_tools:
        print(f"\\n⚠️  Slow Tools:")
        for tool_name, latency in sorted(slow_tools, key=lambda x: x[1], reverse=True):
            print(f"  {tool_name}: {latency:.2f}ms")

# 使用示例
debug_tool_issues(runs_by_type)
```

## 📈 监控和告警

### 实时监控指标

```python
class TraceMonitor:
    """Trace监控类"""

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or {
            'max_think_time': 10000,  # 10秒
            'max_tool_time': 5000,    # 5秒
            'max_step_time': 30000,   # 30秒
            'min_success_rate': 0.95  # 95%
        }

    async def monitor_trace(self, trace_data):
        """监控trace数据并生成告警"""
        alerts = []

        runs = []
        for trace in trace_data.get('traces', []):
            runs.extend(trace.get('runs', []))

        # 按类型分组
        runs_by_type = {}
        for run in runs:
            run_type = run.get('run_type')
            if run_type not in runs_by_type:
                runs_by_type[run_type] = []
            runs_by_type[run_type].append(run)

        # 检查推理时间
        think_runs = runs_by_type.get('think', [])
        for run in think_runs:
            if run.get('latency_ms', 0) > self.thresholds['max_think_time']:
                alerts.append({
                    'type': 'SLOW_THINKING',
                    'run_id': run.get('id'),
                    'latency': run.get('latency_ms'),
                    'threshold': self.thresholds['max_think_time']
                })

        # 检查工具执行时间和成功率
        tool_runs = runs_by_type.get('tool', [])
        tool_stats = {}

        for run in tool_runs:
            tool_name = run.get('name')
            if tool_name not in tool_stats:
                tool_stats[tool_name] = {'total': 0, 'success': 0, 'latencies': []}

            tool_stats[tool_name]['total'] += 1
            if run.get('status') == 'success':
                tool_stats[tool_name]['success'] += 1
            tool_stats[tool_name]['latencies'].append(run.get('latency_ms', 0))

        # 生成工具相关告警
        for tool_name, stats in tool_stats.items():
            # 成功率告警
            success_rate = stats['success'] / stats['total']
            if success_rate < self.thresholds['min_success_rate']:
                alerts.append({
                    'type': 'LOW_SUCCESS_RATE',
                    'tool': tool_name,
                    'success_rate': success_rate,
                    'threshold': self.thresholds['min_success_rate']
                })

            # 性能告警
            avg_latency = sum(stats['latencies']) / len(stats['latencies'])
            if avg_latency > self.thresholds['max_tool_time']:
                alerts.append({
                    'type': 'SLOW_TOOL',
                    'tool': tool_name,
                    'avg_latency': avg_latency,
                    'threshold': self.thresholds['max_tool_time']
                })

        return alerts

    def format_alerts(self, alerts):
        """格式化告警信息"""
        if not alerts:
            return "✅ No alerts - all metrics within thresholds"

        result = f"🚨 {len(alerts)} Alert(s) Generated:\\n\\n"

        for alert in alerts:
            if alert['type'] == 'SLOW_THINKING':
                result += f"⚠️  Slow Thinking: {alert['latency']:.0f}ms (>{alert['threshold']}ms)\\n"
            elif alert['type'] == 'LOW_SUCCESS_RATE':
                result += f"❌ Low Success Rate: {alert['tool']} = {alert['success_rate']:.1%} (<{alert['threshold']:.1%})\\n"
            elif alert['type'] == 'SLOW_TOOL':
                result += f"🐌 Slow Tool: {alert['tool']} = {alert['avg_latency']:.0f}ms (>{alert['threshold']}ms)\\n"

        return result

# 使用示例
async def run_monitoring():
    # 导出最新trace数据
    trace_manager = get_trace_manager()
    query_engine = TraceQueryEngine(trace_manager.storage)
    exporter = TraceExporter(query_engine)

    json_data = await exporter.export_traces_to_json()
    trace_data = json.loads(json_data)

    # 监控并生成告警
    monitor = TraceMonitor()
    alerts = await monitor.monitor_trace(trace_data)

    # 输出告警信息
    print(monitor.format_alerts(alerts))
```

## 🔧 自定义工具的Trace支持

### 基础工具Trace

```python
from myagent.tool import BaseTool, ToolResult

class DatabaseQueryTool(BaseTool):
    name = "db_query"
    description = "Execute database queries"
    parameters = {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "SQL query to execute"},
            "limit": {"type": "integer", "description": "Result limit", "default": 100}
        },
        "required": ["sql"]
    }

    async def execute(self, sql: str, limit: int = 100) -> ToolResult:
        """执行数据库查询

        注意：所有参数和返回值都会自动记录到trace中
        - inputs: {"sql": "SELECT...", "limit": 100}
        - outputs: {"output": "查询结果", "error": null}
        """
        try:
            # 模拟数据库查询
            result = f"Query executed: {sql[:50]}... (limit: {limit})"
            return ToolResult(output=result)

        except Exception as e:
            return ToolResult(error=str(e))
```

### 禁用特定工具的Trace

```python
class SensitiveTool(BaseTool):
    name = "sensitive_operation"
    description = "Perform sensitive operations"
    enable_tracing = False  # 禁用trace记录

    async def execute(self, secret_param: str) -> str:
        # 敏感操作，不会记录到trace中
        return "Operation completed"
```

### 自定义Trace元数据

```python
class AdvancedTool(BaseTool):
    name = "advanced_tool"
    description = "Tool with custom trace metadata"

    async def execute(self, data: dict) -> ToolResult:
        # 工具执行逻辑
        result = {"processed": len(data)}

        # 返回结果时可以添加系统信息
        return ToolResult(
            output=result,
            system=f"Processed {len(data)} items"  # 会记录到trace中
        )
```

## 📋 最佳实践

### 1. Trace存储管理

```python
# 定期清理旧的trace数据
import os
from datetime import datetime, timedelta

def cleanup_old_traces(trace_dir="workdir/traces", days_to_keep=7):
    """清理指定天数之前的trace文件"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    for filename in os.listdir(trace_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(trace_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

            if file_time < cutoff_date:
                os.remove(file_path)
                print(f"Deleted old trace: {filename}")
```

### 2. 生产环境配置

```python
# 生产环境建议配置
agent = create_react_agent(
    name="production_agent",
    tools=tools,
    enable_tracing=True,  # 保持开启以便监控
    trace_metadata=TraceMetadata(
        environment="production",
        version="1.0.0",
        custom_fields={
            "user_id": "user123",
            "session_id": "session456"
        }
    )
)
```

### 3. 开发环境调试

```python
# 开发环境详细调试配置
agent = create_react_agent(
    name="debug_agent",
    tools=tools,
    enable_tracing=True,
    max_steps=5,  # 限制步骤数便于调试
    trace_metadata=TraceMetadata(
        environment="development",
        debug_mode=True
    )
)

# 执行后立即分析
result = await agent.run("测试请求")
trace_data = await export_and_analyze_traces()
```

通过这些工具和方法，你可以充分利用MyAgent的trace系统来监控、调试和优化你的AI代理应用。
