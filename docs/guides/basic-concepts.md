# Basic Concepts

This guide introduces the core concepts and terminology used in MyAgent. Understanding these concepts will help you build more effective agents and make the most of the framework's capabilities.

## Architecture Overview

MyAgent follows a modular architecture with several key components:

```
┌─────────────────┐
│     Agent       │  ← Orchestrates the conversation flow
├─────────────────┤
│   Tool System   │  ← Provides capabilities to the agent
├─────────────────┤
│  LLM Integration│  ← Handles communication with language models
├─────────────────┤
│ Tracing System  │  ← Monitors and debugs execution
└─────────────────┘
```

## Core Components

### 1. Agents

Agents are the main orchestrators that manage conversations and coordinate tool usage.

#### BaseAgent
The abstract base class that defines the agent interface:
```python
from myagent.agent import BaseAgent

class MyCustomAgent(BaseAgent):
    async def run(self, input_text: str) -> str:
        # Custom agent logic
        pass
```

#### ToolCallAgent
The primary agent implementation that supports tool calling:
```python
from myagent import create_toolcall_agent

agent = create_toolcall_agent(
    name="my-agent",
    tools=[...],
    system_prompt="You are a helpful assistant."
)
```

**Key Features:**
- ReAct pattern implementation (Reason + Act)
- Automatic tool selection and execution
- Conversation memory management
- Error handling and recovery

### 2. Tools

Tools extend agent capabilities by providing specific functions.

#### BaseTool
The foundation for all tools:
```python
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather for a location"
    user_confirm = False  # Set True for dangerous operations
    
    async def execute(self, location: str) -> ToolResult:
        # Tool implementation
        weather_data = fetch_weather(location)
        return ToolResult(output=weather_data)
```

**Tool Properties:**
- `name`: Unique identifier for the tool
- `description`: Description for the LLM to understand the tool's purpose
- `user_confirm`: Whether to require user confirmation before execution

#### ToolCollection
Manages multiple tools:
```python
from myagent.tool import ToolCollection

collection = ToolCollection(
    WeatherTool(),
    CalculatorTool(),
    SearchTool()
)

agent = create_toolcall_agent(tools=collection)
```

#### Built-in Tools
- **Terminate**: Allows agents to signal completion
- More built-in tools available in `myagent.tool`

### 3. LLM Integration

MyAgent provides a unified interface for different language models:

```python
from myagent.llm import LLM

# Default configuration (uses environment variables)
llm = LLM()

# Custom configuration
llm = LLM(
    model="gpt-4",
    api_key="your-key",
    base_url="https://api.openai.com/v1",
    temperature=0.7
)
```

**Supported Providers:**
- OpenAI (GPT-3.5, GPT-4, etc.)
- Custom OpenAI-compatible APIs
- Configurable through environment variables

### 4. Schema Types

MyAgent uses Pydantic models for type safety and validation:

#### Message
Represents conversation messages:
```python
from myagent.schema import Message, Role

# User message
msg = Message.user_message("Hello, how are you?")

# System message  
msg = Message.system_message("You are a helpful assistant")

# Assistant message with tool calls
msg = Message.from_tool_calls(tool_calls, content="I'll help you with that")
```

#### ToolCall and ToolResult
Represent tool interactions:
```python
from myagent.tool.base_tool import ToolResult

# Tool execution result
result = ToolResult(
    output="The weather is sunny, 72°F",
    error=None,
    base64_image=None  # Optional image data
)
```

## The ReAct Pattern

MyAgent implements the **ReAct** (Reasoning and Acting) pattern:

```
User Input → Think → Act → Observe → Think → Act → ... → Final Response
```

### 1. Think (Reasoning Phase)
The agent analyzes the input and plans its actions:
- Understand the user's request
- Determine which tools might be helpful
- Plan the sequence of actions

### 2. Act (Action Phase)
The agent executes tools to gather information or perform tasks:
- Select appropriate tools
- Execute tools with correct parameters
- Handle tool errors gracefully

### 3. Observe (Observation Phase)
The agent processes tool results:
- Analyze tool outputs
- Determine if more actions are needed
- Prepare for the next reasoning cycle

### Example ReAct Flow
```
User: "What's the weather like in New York and should I bring an umbrella?"

Think: I need to get the weather information for New York first, then 
       analyze if it's likely to rain to advise on the umbrella.

Act: Use weather_tool(location="New York")

Observe: Weather shows cloudy conditions with 80% chance of rain.

Think: Based on the high chance of rain, I should recommend bringing 
       an umbrella.

Final Response: The weather in New York is cloudy with an 80% chance 
                of rain. I'd definitely recommend bringing an umbrella!
```

## Memory and State Management

### Conversation Memory
Agents maintain conversation history:
```python
from myagent.schema import Memory

memory = Memory(max_messages=100)
memory.add_message(Message.user_message("Hello"))
memory.add_message(Message.assistant_message("Hi there!"))
```

### Agent State
Agents track their execution state:
```python
from myagent.schema import AgentState

# Possible states:
AgentState.IDLE      # Ready to process input
AgentState.RUNNING   # Currently processing
AgentState.FINISHED  # Completed successfully  
AgentState.ERROR     # Encountered an error
```

## Tracing System

MyAgent includes comprehensive tracing for debugging and monitoring:

### Automatic Tracing
All agent executions are automatically traced:
```python
from myagent.trace import trace_agent_step

@trace_agent_step
async def my_function():
    # This function will be traced
    pass
```

### Trace Data Structure
```
Trace
├── Think Records (reasoning phases)
│   ├── User input
│   ├── System prompts
│   ├── LLM response
│   └── Metadata
└── Tool Records (tool executions)
    ├── Tool name and input
    ├── Execution time
    ├── Tool output/error
    └── Performance metrics
```

### Querying Traces
```python
from myagent.trace import TraceQueryEngine

engine = TraceQueryEngine()
traces = engine.query_traces(
    agent_name="my-agent",
    start_time=datetime.now() - timedelta(hours=1)
)
```

## Configuration System

MyAgent uses environment variables and configuration classes:

### Environment Variables
```env
# LLM Configuration
OPENAI_API_KEY=your_key
LLM_MODEL=gpt-4
LLM_MAX_TOKENS=2048

# Tracing
TRACE_ENABLED=true
TRACE_STORAGE=sqlite

# WebSocket Server
WS_HOST=localhost
WS_PORT=8889
```

### Configuration Access
```python
from myagent.config import settings

print(f"Model: {settings.llm.model}")
print(f"Max tokens: {settings.llm.max_tokens}")
print(f"Tracing enabled: {settings.trace.enabled}")
```

## Error Handling

MyAgent provides several error handling mechanisms:

### Tool Error Handling
```python
class SafeTool(BaseTool):
    async def execute(self, **kwargs) -> ToolResult:
        try:
            result = perform_operation(kwargs)
            return ToolResult(output=result)
        except Exception as e:
            return ToolResult(error=f"Operation failed: {e}")
```

### Agent Error Recovery
Agents can recover from errors and continue execution:
- Tool execution errors are reported to the LLM
- The agent can try alternative approaches
- Fatal errors are properly propagated

## Best Practices

### 1. Tool Design
- **Single Responsibility**: Each tool should have one clear purpose
- **Clear Descriptions**: Help the LLM understand when to use the tool
- **Error Handling**: Always handle exceptions gracefully
- **Input Validation**: Validate parameters before execution

### 2. Agent Configuration
- **System Prompts**: Provide clear instructions and context
- **Tool Selection**: Only include tools that are relevant
- **Memory Management**: Configure appropriate memory limits
- **Error Handling**: Plan for failure scenarios

### 3. Performance
- **Async Operations**: Use async/await for I/O operations
- **Batching**: Batch operations when possible
- **Caching**: Cache expensive operations
- **Monitoring**: Use tracing to identify bottlenecks

### 4. Security
- **Input Sanitization**: Validate all user inputs
- **Tool Permissions**: Use `user_confirm=True` for dangerous operations
- **API Keys**: Store credentials securely
- **Error Messages**: Don't expose sensitive information

## Next Steps

Now that you understand the basic concepts:

1. **[Creating Agents](creating-agents.md)** - Learn to build custom agents
2. **[Custom Tools](custom-tools.md)** - Develop your own tools
3. **[Configuration](configuration.md)** - Advanced configuration options
4. **[WebSocket Server](../websocket/server-setup.md)** - Real-time interactions
5. **[Tracing System](../tracing/overview.md)** - Debug and monitor agents

## Glossary

- **Agent**: The main orchestrator that manages conversations and tool usage
- **Tool**: A function that extends agent capabilities
- **ReAct**: Reasoning and Acting pattern for agent behavior
- **Trace**: Execution record for debugging and monitoring
- **LLM**: Large Language Model (e.g., GPT-4)
- **Session**: A conversation instance in WebSocket mode
- **Memory**: Conversation history storage
- **ToolResult**: Standardized output format for tools