# MyAgent

MyAgent is a lightweight toolkit for building tool-aware LLM agents with comprehensive tracing capabilities. It provides a ReAct-style agent framework with WebSocket server support and detailed execution tracing.

## Features

- **ReAct Agent Framework**: Implements reasoning and acting patterns for intelligent decision-making
- **Tool System**: Extensible tool architecture with async execution support
- **Comprehensive Tracing**: Detailed execution tracing with SQLite persistence and web-based viewer
- **WebSocket Server**: Real-time agent communication with session management
- **Built-in Tools**: Web search, SQL operations, and user confirmation workflows
- **CLI Interface**: Easy deployment and management via command-line tools

## Quick Start

1. Install dependencies and create virtual environment:

   ```bash
   uv sync
   ```

2. Copy example environment file and configure:

   ```bash
   cp .env.example .env
   # Edit .env to add your OPENAI_API_KEY and other parameters
   ```

   Or export environment variables directly:

   ```bash
   export OPENAI_API_KEY="your-key"
   export OPENAI_API_BASE="https://api.openai.com/v1"  # optional
   ```

3. Run examples:

   ```bash
   # Web search agent
   uv run python examples/web_search.py
   
   # WebSocket weather agent
   uv run python examples/ws_weather_agent.py
   
   # MySQL Text-to-SQL agent
   uv run python examples/mysql_text2sql.py
   ```

## WebSocket Server

Start a WebSocket server with an agent:

```bash
# Basic usage
uv run python -m myagent.cli.server server <agent_file.py> --host <host> --port <port>

# Example with weather agent
uv run python -m myagent.cli.server server examples/ws_weather_agent.py --port 8889
```

## Architecture

### Core Components

- **Agent Framework**: Base agents, ReAct implementation, and factory functions
- **Tool System**: Extensible tool interface with built-in implementations
- **Tracing System**: Flat architecture with Think and Tool records
- **WebSocket Server**: Real-time communication with structured events
- **CLI Tools**: Server deployment and management utilities

### Example Tools

The framework includes several example tools:

- **DuckDuckGoSearchTool**: Web search using DuckDuckGo API
- **WeatherTool**: Weather information retrieval  
- **MySQLTool**: Database operations with text-to-SQL conversion
- **TerminateTool**: Standard agent termination

### Tracing and Analysis

MyAgent provides comprehensive execution tracing:

```bash
# Start trace viewer server
python trace_server.py

# View traces in browser at http://localhost:8000
```

## Development

### Creating Custom Tools

```python
from myagent.tool import BaseTool, ToolResult

class CustomTool(BaseTool):
    name: str = "custom_tool"
    description: str = "Description of what this tool does"
    user_confirm: bool = False  # Set True for dangerous operations
    
    async def execute(self, **kwargs) -> ToolResult:
        # Your tool implementation
        return ToolResult(
            success=True,
            result="Tool output",
            metadata={"key": "value"}
        )
```

### Creating Agents

```python
from myagent import create_react_agent

# Create agent with custom tools
agent = create_react_agent(
    tools=[CustomTool()],
    llm_config={
        "model": "gpt-4",
        "api_key": "your-api-key"
    }
)

# Run agent
result = await agent.run("Your query here")
```

## Configuration

Configure the framework through environment variables or `.env` file:

```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional
OPENAI_API_BASE=https://api.openai.com/v1
DUCKDUCKGO_PROXY=your-proxy-url
DUCKDUCKGO_REGION=us-en
```

## License

MIT License - see LICENSE file for details.
