# Tracing System Overview

MyAgent includes a comprehensive tracing system for monitoring, debugging, and analyzing agent execution. This system provides detailed insights into agent reasoning, tool usage, and performance metrics.

## What is Tracing?

Tracing captures detailed execution information during agent runs, including:
- **Reasoning steps** - How the agent thinks and plans
- **Tool executions** - What tools are used and their results
- **Performance metrics** - Timing, token usage, and resource consumption
- **Error information** - Failures and recovery attempts

## Architecture

MyAgent uses a **flat tracing architecture** that eliminates redundancy while maintaining complete information:

```
Trace
├── Think Records (Reasoning phases)
│   ├── User input + system prompts
│   ├── LLM response with reasoning
│   ├── Tool selection decisions
│   └── Metadata (tokens, timing)
└── Tool Records (Tool executions) 
    ├── Tool name and parameters
    ├── Execution results
    ├── Performance metrics
    └── Error information (if any)
```

### Key Design Principles

1. **Flat Structure**: Direct Think → Tools relationship eliminates redundant Act layer
2. **Complete Information**: Think records contain full reasoning context
3. **Efficient Storage**: Minimized data duplication and optimized queries
4. **Real-time Access**: Live trace data during execution

## Core Components

### 1. Trace Records

#### Think Record
Captures agent reasoning phases:
```python
Think Record:
  - trace_id: "trace_123"
  - agent_name: "weather-agent"
  - input: "What's the weather in NYC?"
  - system_prompts: ["You are a weather assistant..."]
  - llm_response: "I'll check the weather for you..."
  - tokens_used: 150
  - duration: 1.2s
```

#### Tool Record  
Captures tool execution details:
```python
Tool Record:
  - trace_id: "trace_123"
  - tool_name: "get_weather"
  - input_params: {"location": "NYC"}
  - output: "Sunny, 72°F"
  - duration: 0.5s
  - success: true
```

### 2. Trace Manager

Central coordinator for all tracing operations:
```python
from myagent.trace import get_trace_manager

trace_manager = get_trace_manager()

# Access current traces
traces = trace_manager.get_all_traces()

# Query specific traces  
recent_traces = trace_manager.get_traces_by_time_range(
    start_time=datetime.now() - timedelta(hours=1)
)
```

### 3. Storage Backends

#### In-Memory Storage (Default)
```python
from myagent.trace import InMemoryTraceStorage

storage = InMemoryTraceStorage()
# Fast access, lost on restart
```

#### SQLite Storage (Persistent)
```python
from myagent.trace.storage import SQLiteTraceStorage

storage = SQLiteTraceStorage("traces.db")
# Persistent, queryable, good for development
```

#### Custom Storage
```python
from myagent.trace import TraceStorage

class CustomStorage(TraceStorage):
    async def store_trace(self, trace):
        # Custom storage implementation
        pass
```

## Automatic Tracing

### Agent-Level Tracing

All agents created via factory functions are automatically traced:
```python
from myagent import create_toolcall_agent

# Tracing enabled by default
agent = create_toolcall_agent(
    name="my-agent",
    tools=[WeatherTool()],
    enable_tracing=True  # Default
)

# Run agent (automatically traced)
response = await agent.run("What's the weather?")

# Access traces
traces = get_trace_manager().get_traces_by_agent("my-agent")
```

### Tool-Level Tracing  

Individual tools are automatically traced:
```python
from myagent.tool import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "Example tool"
    enable_tracing = True  # Default
    
    async def execute(self, **kwargs):
        # Execution automatically traced
        return ToolResult(output="result")
```

### Decorator-Based Tracing

For custom functions:
```python
from myagent.trace import trace_run

@trace_run
async def custom_function(data: str) -> str:
    # Function execution will be traced
    result = process_data(data)
    return result
```

## Manual Tracing

### Custom Trace Points

Add custom trace points in your code:
```python
from myagent.trace import get_trace_manager

async def complex_workflow(input_data):
    trace_manager = get_trace_manager()
    
    # Start custom trace
    trace_id = trace_manager.start_trace(
        agent_name="workflow",
        input_data=input_data
    )
    
    try:
        # Process data
        result = await process_data(input_data)
        
        # Record step
        trace_manager.add_step(
            trace_id=trace_id,
            step_name="data_processing", 
            result=result
        )
        
        return result
    finally:
        # End trace
        trace_manager.end_trace(trace_id)
```

### WebSocket Session Tracing

WebSocket sessions are automatically traced:
```python
from myagent.ws.server import AgentWebSocketServer

server = AgentWebSocketServer(create_agent)

@server.on_message  
async def handle_message(session_id, message):
    # Message handling automatically traced
    # Accessible via session_id
    pass

# Query session traces
session_traces = get_trace_manager().get_traces_by_session(session_id)
```

## Querying Traces

### Basic Queries

```python
from myagent.trace import TraceQueryEngine
from datetime import datetime, timedelta

engine = TraceQueryEngine()

# Get all traces
all_traces = engine.get_all_traces()

# Get traces by agent
agent_traces = engine.get_traces_by_agent("weather-agent")

# Get traces by time range
recent_traces = engine.get_traces_by_time_range(
    start_time=datetime.now() - timedelta(hours=1)
)

# Get traces with errors
error_traces = engine.get_traces_with_errors()
```

### Advanced Filtering

```python
from myagent.trace import TraceFilter

# Create filter
trace_filter = TraceFilter(
    agent_names=["weather-agent", "calculator-agent"],
    start_time=datetime.now() - timedelta(days=1),
    end_time=datetime.now(),
    has_errors=False,
    min_duration=1.0,  # Minimum execution time in seconds
    tools_used=["get_weather"]
)

# Apply filter
filtered_traces = engine.query_traces(trace_filter)
```

### Tool-Specific Queries

```python
from myagent.trace import RunFilter

# Find tool executions
tool_filter = RunFilter(
    tool_names=["get_weather"],
    min_duration=0.5,
    success_only=True
)

tool_runs = engine.query_tool_runs(tool_filter)

# Analyze tool performance
avg_duration = sum(run.duration for run in tool_runs) / len(tool_runs)
success_rate = sum(1 for run in tool_runs if run.success) / len(tool_runs)
```

## Analysis and Visualization

### Performance Analysis

```python
from myagent.trace import TraceAnalyzer

analyzer = TraceAnalyzer()

# Analyze agent performance
stats = analyzer.analyze_agent_performance("weather-agent")
print(f"Average response time: {stats.avg_response_time}s")
print(f"Success rate: {stats.success_rate}%")
print(f"Most used tool: {stats.most_used_tool}")

# Tool usage statistics
tool_stats = analyzer.analyze_tool_usage()
for tool_name, usage in tool_stats.items():
    print(f"{tool_name}: {usage.call_count} calls, {usage.avg_duration}s avg")
```

### Export Capabilities

```python
from myagent.trace import TraceExporter

exporter = TraceExporter()

# Export to JSON
traces_json = exporter.to_json(traces)

# Export to CSV for analysis
exporter.to_csv(traces, "agent_traces.csv")

# Export to pandas DataFrame
df = exporter.to_dataframe(traces)
```

## Web-Based Trace Viewer

MyAgent includes a web-based trace viewer for visual analysis:

### Starting the Trace Viewer

```bash
# Start trace viewer server
python trace_server.py

# Or programmatically
from myagent.trace.viewer import start_trace_viewer
await start_trace_viewer(port=8080)
```

### Features

- **Real-time trace monitoring** - See traces as they happen
- **Interactive timeline** - Visual representation of execution flow  
- **Performance charts** - Response time and success rate graphs
- **Error analysis** - Detailed error information and stack traces
- **Tool usage patterns** - Visual tool usage statistics
- **Search and filtering** - Find specific traces quickly

### Accessing the Viewer

Open `http://localhost:8080` in your browser to access:
- Trace list with filtering options
- Individual trace details
- Performance dashboards  
- Tool usage analytics

## Configuration

### Environment Variables

```env
# Enable/disable tracing globally
TRACE_ENABLED=true

# Storage backend configuration
TRACE_STORAGE=sqlite  # or 'memory'
TRACE_DATABASE_URL=sqlite:///traces.db

# Trace retention
TRACE_MAX_AGE_DAYS=30
TRACE_MAX_COUNT=10000

# Performance settings
TRACE_BUFFER_SIZE=1000
TRACE_FLUSH_INTERVAL=60
```

### Programmatic Configuration

```python
from myagent.trace import set_trace_manager, TraceManager
from myagent.trace.storage import SQLiteTraceStorage

# Custom trace manager
storage = SQLiteTraceStorage("custom_traces.db")
trace_manager = TraceManager(storage=storage)
set_trace_manager(trace_manager)

# Configure trace settings
trace_manager.configure(
    max_trace_age=timedelta(days=7),
    max_trace_count=5000,
    auto_cleanup=True
)
```

## Performance Impact

### Overhead Measurements

Tracing has minimal performance impact:
- **Memory**: ~1-2MB per 1000 traces
- **CPU**: <1% overhead for typical workloads  
- **Storage**: ~1KB per trace record
- **Latency**: <1ms additional latency per traced call

### Optimization Tips

1. **Selective Tracing**: Disable for non-critical tools
```python
class HighFrequencyTool(BaseTool):
    enable_tracing = False  # Skip tracing for performance
```

2. **Async Storage**: Use background storage writes
```python
trace_manager.configure(async_storage=True)
```

3. **Batch Processing**: Group trace writes
```python
trace_manager.configure(batch_size=100)
```

4. **Cleanup Policies**: Automatic old trace removal
```python
trace_manager.configure(
    cleanup_interval=timedelta(hours=1),
    max_age=timedelta(days=7)
)
```

## Best Practices

### 1. Trace Management

- **Set appropriate retention policies** to prevent unlimited growth
- **Use meaningful agent and tool names** for easier filtering
- **Clean up traces regularly** in production environments
- **Monitor trace storage size** and performance impact

### 2. Development Workflow

- **Enable tracing in development** for debugging
- **Use trace viewer** to understand agent behavior
- **Analyze failed traces** to improve error handling
- **Monitor performance trends** over time

### 3. Production Deployment

- **Configure persistent storage** for trace data
- **Set up automated cleanup** to manage storage
- **Monitor trace system health** alongside application metrics
- **Use sampling** for high-volume applications

### 4. Security Considerations

- **Sanitize sensitive data** before tracing
- **Secure trace storage** access
- **Consider data retention policies** for compliance
- **Monitor trace access** patterns

## Integration Examples

### With Logging Systems

```python
import logging
from myagent.trace import get_trace_manager

class TraceHandler(logging.Handler):
    def emit(self, record):
        trace_manager = get_trace_manager()
        if trace_manager.current_trace:
            trace_manager.add_log_entry(
                level=record.levelname,
                message=record.getMessage()
            )

# Add trace handler to logger
logging.getLogger().addHandler(TraceHandler())
```

### With Monitoring Systems

```python
from myagent.trace import TraceManager
import prometheus_client

# Prometheus metrics
trace_duration = prometheus_client.Histogram('agent_trace_duration_seconds')
trace_errors = prometheus_client.Counter('agent_trace_errors_total')

class MonitoringTraceManager(TraceManager):
    def end_trace(self, trace_id):
        trace = super().end_trace(trace_id)
        
        # Record metrics
        trace_duration.observe(trace.total_duration)
        if trace.has_errors:
            trace_errors.inc()
        
        return trace
```

### With APM Tools

```python
import opentelemetry
from myagent.trace import trace_run

@trace_run
@opentelemetry.trace.instrument  
async def instrumented_function():
    # Function traced by both MyAgent and OpenTelemetry
    pass
```

## Troubleshooting

### Common Issues

#### High Memory Usage
```python
# Reduce trace retention
trace_manager.configure(max_trace_count=1000)

# Enable auto-cleanup
trace_manager.configure(auto_cleanup=True)
```

#### Slow Trace Queries
```python
# Add indexes to storage backend
storage.create_indexes(['agent_name', 'timestamp', 'trace_id'])

# Use time-based partitioning
storage.configure(partition_by_time=True)
```

#### Missing Traces
```python
# Check if tracing is enabled
print(f"Tracing enabled: {get_trace_manager().enabled}")

# Verify agent configuration
print(f"Agent tracing: {agent.enable_tracing}")
```

## Next Steps

- **[Trace Decorators](decorators.md)** - Using trace decorators
- **[Query & Analysis](query.md)** - Advanced trace querying
- **[Trace Viewer](viewer.md)** - Web-based trace visualization
- **[Performance Monitoring](../guides/performance.md)** - Production monitoring