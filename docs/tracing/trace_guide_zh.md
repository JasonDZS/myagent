# 追踪系统使用指南

MyAgent 的追踪系统提供完整的执行记录、性能监控和调试能力。本指南详细介绍如何使用追踪系统进行调试、监控和分析。

## 目录

- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [基础使用](#基础使用)
- [数据分析](#数据分析)
- [调试场景](#调试场景)
- [监控和告警](#监控和告警)
- [最佳实践](#最佳实践)

## 快速开始

### 启用追踪功能

追踪功能在所有智能体中默认启用：

```python
from myagent import create_toolcall_agent
from myagent.tool import BaseTool, ToolResult

class MyTool(BaseTool):
    name = "my_tool"
    description = "我的工具"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(output="完成")

# 创建智能体（追踪自动启用）
agent = create_toolcall_agent(
    tools=[MyTool()],
    name="my_agent"
)

# 执行任务，自动记录追踪
result = await agent.run("执行任务")
```

### 查看追踪数据

```python
from myagent.trace import get_trace_manager, TraceQueryEngine, TraceExporter

async def view_traces():
    # 获取追踪管理器
    trace_manager = get_trace_manager()

    # 创建查询引擎
    query_engine = TraceQueryEngine(trace_manager.storage)

    # 创建导出器
    exporter = TraceExporter(query_engine)

    # 导出为 JSON
    json_data = await exporter.export_traces_to_json()

    # 保存到文件
    with open("traces/my_trace.json", "w", encoding="utf-8") as f:
        f.write(json_data)

    print("追踪数据已保存到 traces/my_trace.json")

# 运行
await view_traces()
```

## 核心概念

### 追踪层次结构

MyAgent 使用**扁平化追踪架构**：

```
Trace (追踪会话)
├── Think Record (推理记录)
│   ├── 用户输入
│   ├── 智能体推理
│   ├── 工具调用决策
│   └── 性能指标
│
└── Tool Records (工具记录)
    ├── 工具名称
    ├── 输入参数
    ├── 执行结果
    └── 性能指标
```

**关键设计：**
- Think 和 Tool 直接关联，无中间层
- 简化的数据结构，易于分析
- 完整的性能指标记录

### 核心组件

#### 1. TraceManager (追踪管理器)
**模块：** `myagent/trace/manager.py`

**功能：**
- 管理追踪会话生命周期
- 协调 Think 和 Tool 记录
- 提供统一的追踪接口

```python
from myagent.trace import get_trace_manager

# 获取全局追踪管理器
manager = get_trace_manager()

# 手动控制追踪
manager.start_trace(agent_name="my_agent")
manager.end_trace()
```

#### 2. TraceModels (追踪模型)
**模块：** `myagent/trace/models.py`

**数据模型：**

```python
# Think 记录
class ThinkRecord:
    id: str              # 唯一 ID
    trace_id: str        # 所属追踪会话 ID
    timestamp: datetime  # 时间戳
    inputs: dict         # 输入（用户消息）
    outputs: dict        # 输出（助手响应 + 工具调用）
    latency_ms: float    # 延迟（毫秒）
    status: str          # 状态
    error: str           # 错误信息

# Tool 记录
class ToolRecord:
    id: str              # 唯一 ID
    trace_id: str        # 所属追踪会话 ID
    think_id: str        # 关联的 Think ID
    name: str            # 工具名称
    inputs: dict         # 输入参数
    outputs: dict        # 输出结果
    latency_ms: float    # 延迟（毫秒）
    status: str          # 状态
    error: str           # 错误信息
```

#### 3. Storage (存储)
**模块：** `myagent/trace/storage.py`

**功能：**
- SQLite 数据库持久化
- 高效的查询接口
- 自动数据清理

```python
from myagent.trace.storage import TraceStorage

# 创建存储（默认使用 SQLite）
storage = TraceStorage(db_path="traces.db")

# 保存记录
await storage.save_think_record(think_record)
await storage.save_tool_record(tool_record)

# 查询记录
all_traces = await storage.get_all_traces()
```

#### 4. QueryEngine (查询引擎)
**模块：** `myagent/trace/query.py`

**功能：**
- 灵活的查询和过滤
- 复杂的聚合分析
- 性能统计

```python
from myagent.trace import TraceQueryEngine

query_engine = TraceQueryEngine(storage)

# 查询特定追踪
trace = await query_engine.get_trace(trace_id)

# 查询所有追踪
all_traces = await query_engine.get_all_traces()

# 过滤查询
recent_traces = await query_engine.filter_traces(
    start_time=datetime.now() - timedelta(hours=1),
    status="success"
)
```

#### 5. Decorators (装饰器)
**模块：** `myagent/trace/decorators.py`

**功能：**
- `@trace_agent` 自动追踪装饰器
- 无侵入式追踪集成

```python
from myagent.trace import trace_agent

@trace_agent
async def run_agent_task():
    agent = create_toolcall_agent(tools=[...])
    result = await agent.run("任务")
    return result

# 自动追踪整个执行过程
result = await run_agent_task()
```

#### 6. Exporter (导出器)
**模块：** `myagent/trace/exporter.py`

**功能：**
- 导出为 JSON 格式
- 生成统计摘要
- 支持自定义导出格式

```python
from myagent.trace import TraceExporter

exporter = TraceExporter(query_engine)

# 导出 JSON
json_data = await exporter.export_traces_to_json()

# 导出摘要
summary = await exporter.export_trace_summary()
print(summary)
```

## 基础使用

### 1. 使用装饰器自动追踪

```python
from myagent.trace import trace_agent
from myagent import create_toolcall_agent

@trace_agent
async def my_agent_task(query: str):
    """自动追踪的智能体任务"""
    agent = create_toolcall_agent(
        tools=[...],
        name="my_agent"
    )

    result = await agent.run(query)
    return result

# 执行任务（自动追踪）
result = await my_agent_task("分析这些数据")
```

### 2. 手动控制追踪

```python
from myagent.trace import get_trace_manager

async def manual_trace_control():
    manager = get_trace_manager()

    # 开始追踪
    trace_id = manager.start_trace(
        agent_name="manual_agent",
        metadata={"environment": "production"}
    )

    try:
        # 执行任务
        agent = create_toolcall_agent(tools=[...])
        result = await agent.run("任务")

        # 结束追踪
        manager.end_trace()

    except Exception as e:
        # 记录错误
        manager.end_trace(error=str(e))
        raise

    return result
```

### 3. 导出和保存追踪数据

```python
from myagent.trace import get_trace_manager, TraceQueryEngine, TraceExporter
import json

async def export_traces():
    # 获取追踪管理器
    manager = get_trace_manager()

    # 创建查询引擎和导出器
    query_engine = TraceQueryEngine(manager.storage)
    exporter = TraceExporter(query_engine)

    # 导出 JSON
    json_data = await exporter.export_traces_to_json()

    # 保存到文件
    with open("traces/export.json", "w", encoding="utf-8") as f:
        f.write(json_data)

    # 解析并查看
    data = json.loads(json_data)
    print(f"导出了 {len(data['traces'])} 个追踪会话")

    return data
```

### 4. 查看统计摘要

```python
from myagent.trace import get_trace_manager, TraceQueryEngine, TraceExporter

async def view_summary():
    manager = get_trace_manager()
    query_engine = TraceQueryEngine(manager.storage)
    exporter = TraceExporter(query_engine)

    # 获取摘要
    summary = await exporter.export_trace_summary()

    print("=== 追踪摘要 ===")
    print(summary)

# 输出示例：
# === 追踪摘要 ===
# 总追踪数：5
# 总 Think 记录：15
# 总 Tool 记录：23
# 平均延迟：245.3ms
# 成功率：95.6%
```

## 数据分析

### 基础结构分析

```python
import json

def analyze_trace_structure(trace_file):
    """分析追踪文件的基础结构"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== 追踪结构分析 ===\n")

    for trace in data.get('traces', []):
        trace_id = trace.get('id')
        agent_name = trace.get('agent_name')

        print(f"追踪 ID：{trace_id}")
        print(f"智能体：{agent_name}")
        print(f"开始时间：{trace.get('start_time')}")
        print(f"结束时间：{trace.get('end_time')}")

        # Think 记录统计
        thinks = trace.get('thinks', [])
        print(f"Think 记录数：{len(thinks)}")

        # Tool 记录统计
        tools = trace.get('tools', [])
        print(f"Tool 记录数：{len(tools)}")

        # 工具使用分组
        tool_counts = {}
        for tool in tools:
            name = tool.get('name')
            tool_counts[name] = tool_counts.get(name, 0) + 1

        print("\n工具使用统计：")
        for name, count in tool_counts.items():
            print(f"  {name}: {count} 次")

        print("-" * 50)

# 使用
analyze_trace_structure("traces/export.json")
```

### 推理过程分析

```python
def analyze_thinking_process(trace_file):
    """分析智能体的推理过程"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== 推理过程分析 ===\n")

    for trace in data.get('traces', []):
        thinks = trace.get('thinks', [])

        for i, think in enumerate(thinks, 1):
            print(f"\n--- 推理步骤 {i} ---")

            # 输入分析
            inputs = think.get('inputs', {})
            user_msg = inputs.get('content', '')
            print(f"用户输入：{user_msg[:100]}...")

            # 输出分析
            outputs = think.get('outputs', {})
            assistant_msg = outputs.get('content', '')
            tool_calls = outputs.get('tool_calls', [])

            print(f"助手响应：{assistant_msg[:100]}...")

            if tool_calls:
                tool_names = [tc.get('function', {}).get('name') for tc in tool_calls]
                print(f"计划使用工具：{tool_names}")

            # 性能
            latency = think.get('latency_ms', 0)
            print(f"推理时间：{latency:.2f}ms")

            # 状态
            status = think.get('status', 'unknown')
            print(f"状态：{status}")

            if think.get('error'):
                print(f"❌ 错误：{think.get('error')}")

# 使用
analyze_thinking_process("traces/export.json")
```

### 工具使用分析

```python
def analyze_tool_usage(trace_file):
    """分析工具使用情况"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 收集所有工具记录
    all_tools = []
    for trace in data.get('traces', []):
        all_tools.extend(trace.get('tools', []))

    # 统计
    tool_stats = {}
    for tool in all_tools:
        name = tool.get('name')
        if name not in tool_stats:
            tool_stats[name] = {
                'total': 0,
                'success': 0,
                'error': 0,
                'latencies': []
            }

        tool_stats[name]['total'] += 1

        if tool.get('status') == 'success':
            tool_stats[name]['success'] += 1
        else:
            tool_stats[name]['error'] += 1

        tool_stats[name]['latencies'].append(tool.get('latency_ms', 0))

    # 输出报告
    print("=== 工具使用分析 ===\n")

    for name, stats in tool_stats.items():
        success_rate = stats['success'] / stats['total'] * 100
        avg_latency = sum(stats['latencies']) / len(stats['latencies'])
        max_latency = max(stats['latencies'])

        print(f"工具：{name}")
        print(f"  调用次数：{stats['total']}")
        print(f"  成功率：{success_rate:.1f}%")
        print(f"  平均延迟：{avg_latency:.2f}ms")
        print(f"  最大延迟：{max_latency:.2f}ms")
        print()

# 使用
analyze_tool_usage("traces/export.json")
```

### 性能分析

```python
def analyze_performance(trace_file):
    """分析执行性能"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== 性能分析 ===\n")

    for trace in data.get('traces', []):
        # Think 性能
        thinks = trace.get('thinks', [])
        if thinks:
            think_times = [t.get('latency_ms', 0) for t in thinks]
            print(f"推理性能：")
            print(f"  总推理时间：{sum(think_times):.2f}ms")
            print(f"  平均推理时间：{sum(think_times)/len(think_times):.2f}ms")
            print(f"  最慢推理：{max(think_times):.2f}ms")
            print()

        # Tool 性能
        tools = trace.get('tools', [])
        if tools:
            tool_times = [t.get('latency_ms', 0) for t in tools]
            print(f"工具执行性能：")
            print(f"  总执行时间：{sum(tool_times):.2f}ms")
            print(f"  平均执行时间：{sum(tool_times)/len(tool_times):.2f}ms")
            print(f"  最慢工具：{max(tool_times):.2f}ms")

            # 找出最慢的工具
            slowest = max(tools, key=lambda t: t.get('latency_ms', 0))
            print(f"  最慢工具名称：{slowest.get('name')}")
            print()

        # 总体性能
        total_time = sum([t.get('latency_ms', 0) for t in thinks + tools])
        print(f"总执行时间：{total_time:.2f}ms")

# 使用
analyze_performance("traces/export.json")
```

## 调试场景

### 查找推理错误

```python
def debug_thinking_errors(trace_file):
    """调试推理错误"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== 推理错误调试 ===\n")

    for trace in data.get('traces', []):
        thinks = trace.get('thinks', [])

        for i, think in enumerate(thinks, 1):
            # 检查错误
            if think.get('status') != 'success':
                print(f"❌ 推理步骤 {i} 失败：")
                print(f"  错误：{think.get('error')}")
                print(f"  输入：{think.get('inputs', {}).get('content', '')[:100]}...")
                print()

            # 检查性能问题
            latency = think.get('latency_ms', 0)
            if latency > 10000:  # 超过 10 秒
                print(f"⚠️  推理步骤 {i} 性能慢：")
                print(f"  延迟：{latency:.2f}ms")
                print()

            # 检查无工具调用
            outputs = think.get('outputs', {})
            tool_calls = outputs.get('tool_calls', [])
            content = outputs.get('content', '').lower()

            if not tool_calls and 'terminate' not in content:
                print(f"🤔 推理步骤 {i} 无工具调用：")
                print(f"  响应：{outputs.get('content', '')[:150]}...")
                print()

# 使用
debug_thinking_errors("traces/export.json")
```

### 查找工具错误

```python
def debug_tool_errors(trace_file):
    """调试工具执行错误"""
    with open(trace_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("=== 工具错误调试 ===\n")

    for trace in data.get('traces', []):
        tools = trace.get('tools', [])

        error_count = 0
        for tool in tools:
            if tool.get('status') != 'success':
                error_count += 1
                print(f"❌ 工具错误 #{error_count}：")
                print(f"  工具：{tool.get('name')}")
                print(f"  错误：{tool.get('error')}")
                print(f"  输入：{tool.get('inputs', {})}")
                print(f"  Think ID：{tool.get('think_id')}")
                print()

        # 查找慢工具
        slow_tools = [(t.get('name'), t.get('latency_ms', 0))
                     for t in tools if t.get('latency_ms', 0) > 5000]

        if slow_tools:
            print("⚠️  慢工具：")
            for name, latency in sorted(slow_tools, key=lambda x: x[1], reverse=True):
                print(f"  {name}: {latency:.2f}ms")
            print()

# 使用
debug_tool_errors("traces/export.json")
```

## 监控和告警

### 实时监控

```python
from myagent.trace import get_trace_manager, TraceQueryEngine, TraceExporter
import json

class TraceMonitor:
    """追踪监控类"""

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or {
            'max_think_time': 10000,   # 最大推理时间 10 秒
            'max_tool_time': 5000,     # 最大工具时间 5 秒
            'min_success_rate': 0.95   # 最小成功率 95%
        }

    async def check_alerts(self, trace_data):
        """检查告警"""
        alerts = []

        # 收集所有记录
        all_thinks = []
        all_tools = []
        for trace in trace_data.get('traces', []):
            all_thinks.extend(trace.get('thinks', []))
            all_tools.extend(trace.get('tools', []))

        # 检查推理时间
        for think in all_thinks:
            latency = think.get('latency_ms', 0)
            if latency > self.thresholds['max_think_time']:
                alerts.append({
                    'type': 'SLOW_THINKING',
                    'latency': latency,
                    'threshold': self.thresholds['max_think_time'],
                    'think_id': think.get('id')
                })

        # 检查工具性能和成功率
        tool_stats = {}
        for tool in all_tools:
            name = tool.get('name')
            if name not in tool_stats:
                tool_stats[name] = {'total': 0, 'success': 0, 'latencies': []}

            tool_stats[name]['total'] += 1
            if tool.get('status') == 'success':
                tool_stats[name]['success'] += 1
            tool_stats[name]['latencies'].append(tool.get('latency_ms', 0))

        # 生成工具告警
        for name, stats in tool_stats.items():
            # 成功率告警
            success_rate = stats['success'] / stats['total']
            if success_rate < self.thresholds['min_success_rate']:
                alerts.append({
                    'type': 'LOW_SUCCESS_RATE',
                    'tool': name,
                    'success_rate': success_rate,
                    'threshold': self.thresholds['min_success_rate']
                })

            # 性能告警
            avg_latency = sum(stats['latencies']) / len(stats['latencies'])
            if avg_latency > self.thresholds['max_tool_time']:
                alerts.append({
                    'type': 'SLOW_TOOL',
                    'tool': name,
                    'avg_latency': avg_latency,
                    'threshold': self.thresholds['max_tool_time']
                })

        return alerts

    def format_alerts(self, alerts):
        """格式化告警"""
        if not alerts:
            return "✅ 无告警 - 所有指标正常"

        result = f"🚨 检测到 {len(alerts)} 个告警：\n\n"

        for alert in alerts:
            if alert['type'] == 'SLOW_THINKING':
                result += f"⚠️  推理慢：{alert['latency']:.0f}ms (阈值: {alert['threshold']}ms)\n"
            elif alert['type'] == 'LOW_SUCCESS_RATE':
                result += f"❌ 成功率低：{alert['tool']} = {alert['success_rate']:.1%} (阈值: {alert['threshold']:.1%})\n"
            elif alert['type'] == 'SLOW_TOOL':
                result += f"🐌 工具慢：{alert['tool']} = {alert['avg_latency']:.0f}ms (阈值: {alert['threshold']}ms)\n"

        return result

# 使用示例
async def run_monitoring():
    # 导出追踪数据
    manager = get_trace_manager()
    query_engine = TraceQueryEngine(manager.storage)
    exporter = TraceExporter(query_engine)

    json_data = await exporter.export_traces_to_json()
    trace_data = json.loads(json_data)

    # 监控并生成告警
    monitor = TraceMonitor()
    alerts = await monitor.check_alerts(trace_data)

    # 输出告警
    print(monitor.format_alerts(alerts))

# 运行
await run_monitoring()
```

## 自定义工具的追踪支持

### 基础工具追踪

```python
from myagent.tool import BaseTool, ToolResult

class DatabaseQueryTool(BaseTool):
    name = "db_query"
    description = "执行数据库查询"

    async def execute(self, sql: str, limit: int = 100) -> ToolResult:
        """
        执行数据库查询

        所有参数和返回值自动记录到追踪：
        - inputs: {"sql": "SELECT...", "limit": 100}
        - outputs: {"output": "结果", "error": None}
        """
        try:
            # 模拟查询
            result = f"查询执行：{sql[:50]}... (限制: {limit})"
            return ToolResult(output=result)

        except Exception as e:
            # 错误也会记录
            return ToolResult(error=str(e))
```

### 禁用特定工具的追踪

```python
class SensitiveTool(BaseTool):
    name = "sensitive_operation"
    description = "执行敏感操作"
    enable_tracing = False  # 禁用追踪

    async def execute(self, secret_data: str) -> ToolResult:
        # 敏感操作不会记录到追踪
        return ToolResult(output="操作完成")
```

### 添加自定义元数据

```python
class AdvancedTool(BaseTool):
    name = "advanced_tool"
    description = "带自定义元数据的工具"

    async def execute(self, data: dict) -> ToolResult:
        # 处理数据
        processed_count = len(data)
        result = {"processed": processed_count}

        # 添加系统信息（会记录到追踪）
        return ToolResult(
            output=result,
            system=f"处理了 {processed_count} 项数据"
        )
```

## 最佳实践

### 1. 追踪数据管理

```python
import os
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_old_traces(trace_dir="traces", days_to_keep=7):
    """清理旧的追踪文件"""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    trace_path = Path(trace_dir)

    if not trace_path.exists():
        return

    deleted_count = 0
    for file in trace_path.glob("*.json"):
        file_time = datetime.fromtimestamp(file.stat().st_mtime)

        if file_time < cutoff_date:
            file.unlink()
            deleted_count += 1
            print(f"已删除旧追踪：{file.name}")

    print(f"清理完成，删除了 {deleted_count} 个文件")

# 定期运行
cleanup_old_traces(days_to_keep=7)
```

### 2. 生产环境配置

```python
from myagent import create_toolcall_agent

# 生产环境追踪配置
agent = create_toolcall_agent(
    tools=[...],
    name="production_agent"
    # 追踪默认启用，无需额外配置
)

# 定期导出和分析追踪数据
async def monitor_production():
    # 每小时导出一次
    trace_data = await export_traces()

    # 检查告警
    monitor = TraceMonitor()
    alerts = await monitor.check_alerts(trace_data)

    if alerts:
        # 发送告警通知
        send_alert_notification(alerts)
```

### 3. 开发环境调试

```python
from myagent import create_toolcall_agent
from myagent.trace import trace_agent

# 开发环境详细调试
@trace_agent
async def debug_task(query: str):
    agent = create_toolcall_agent(
        tools=[...],
        name="debug_agent"
    )

    # 限制步数便于调试
    agent.max_steps = 5

    result = await agent.run(query)

    # 执行后立即分析
    await analyze_latest_trace()

    return result

async def analyze_latest_trace():
    """分析最新的追踪"""
    data = await export_traces()

    # 详细分析
    analyze_trace_structure("traces/latest.json")
    analyze_thinking_process("traces/latest.json")
    analyze_tool_usage("traces/latest.json")
    analyze_performance("traces/latest.json")
```

### 4. 追踪文件组织

```bash
# 推荐的追踪目录结构
traces/
├── production/          # 生产环境
│   ├── 2024-01-01/
│   ├── 2024-01-02/
│   └── ...
├── development/         # 开发环境
│   └── debug_*.json
└── archived/           # 归档
    └── 2023/
```

## 常见问题

### Q1: 追踪会影响性能吗？

**A:** 影响很小（< 5%）。追踪是异步的，不会阻塞主流程。

### Q2: 追踪数据存储在哪里？

**A:** 默认使用 SQLite 数据库，存储在 `traces.db` 文件中。可以通过配置更改存储位置。

### Q3: 如何查看特定时间段的追踪？

**A:** 使用 QueryEngine 的过滤功能：

```python
from datetime import datetime, timedelta

recent_traces = await query_engine.filter_traces(
    start_time=datetime.now() - timedelta(hours=1)
)
```

### Q4: 敏感数据会被追踪吗？

**A:** 可以通过设置 `enable_tracing = False` 禁用特定工具的追踪。

### Q5: 如何集成到监控系统？

**A:** 可以定期导出追踪数据并发送到监控系统（如 Prometheus、Grafana）：

```python
async def export_to_monitoring():
    data = await export_traces()
    # 解析并发送到监控系统
    send_metrics_to_prometheus(data)
```

## 总结

MyAgent 的追踪系统提供：

✅ **完整记录** - Think 和 Tool 完整执行历史
✅ **性能监控** - 延迟、成功率等关键指标
✅ **灵活分析** - 查询、过滤、聚合分析
✅ **调试支持** - 错误定位、性能瓶颈分析
✅ **易于集成** - 装饰器自动追踪，无侵入

适合：
- 开发调试
- 生产监控
- 性能优化
- 问题排查

## 相关文档

- **[追踪系统架构](trace_architecture_zh.md)** - 详细架构设计
- **[研究智能体指南](../guides/research-agent-guide_zh.md)** - 实际应用
- **[系统架构](../architecture/system_architecture.md)** - 整体架构

---

开始使用追踪系统优化您的智能体应用！
