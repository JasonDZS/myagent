# Agent Classes API Reference

This document provides detailed API reference for MyAgent's agent classes and factory functions.

## Factory Functions

### create_toolcall_agent()

Creates a tool-aware agent that implements the ReAct pattern.

```python
def create_toolcall_agent(
    *,
    name: str = "toolcall-agent",
    llm: LLM | None = None,
    tools: Sequence[BaseTool] | ToolCollection | None = None,
    system_prompt: str | None = None,
    next_step_prompt: str | None = None,
    tool_choice: ToolChoice | TOOL_CHOICE_TYPE | None = ToolChoice.AUTO,
    max_steps: int | None = None,
    max_observe: int | None = None,
    **extra_fields
) -> ToolCallAgent
```

**Parameters:**
- `name`: Agent identifier for tracing and logging
- `llm`: LLM instance to use. If None, creates default LLM
- `tools`: Tools available to the agent. Terminate tool is automatically added
- `system_prompt`: System message injected on every turn
- `next_step_prompt`: Hint appended before each thinking cycle
- `tool_choice`: Strategy for tool selection (`auto`, `none`, `required`)
- `max_steps`: Maximum number of reasoning/action cycles
- `max_observe`: Maximum length of tool observation text
- `**extra_fields`: Additional ToolCallAgent fields

**Returns:** `ToolCallAgent` instance

**Example:**
```python
from myagent import create_toolcall_agent
from myagent.tool import BaseTool

agent = create_toolcall_agent(
    name="weather-agent",
    tools=[WeatherTool()],
    system_prompt="You are a weather assistant",
    max_steps=5
)
```

### create_react_agent()

**Deprecated:** Use `create_toolcall_agent()` instead. Maintained for backward compatibility.

```python
def create_react_agent(...) -> ToolCallAgent
```

## Agent Classes

### BaseAgent

Abstract base class for all agents. Defines the core agent interface.

```python
class BaseAgent(ABC):
    name: str
    llm: LLM
    enable_tracing: bool = True
    
    @abstractmethod
    async def run(self, input_text: str) -> str:
        """Process input and return response"""
        pass
```

**Abstract Methods:**
- `run(input_text: str) -> str`: Process user input and return response

**Properties:**
- `name`: Agent identifier
- `llm`: Language model instance
- `enable_tracing`: Whether to trace execution

### ToolCallAgent

Primary agent implementation that supports tool calling and ReAct pattern.

```python
class ToolCallAgent(BaseAgent):
    available_tools: ToolCollection
    system_prompt: str | None = None
    next_step_prompt: str | None = None
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO.value
    max_steps: int = 10
    max_observe: int = 2000
    memory: Memory
    state: AgentState = AgentState.IDLE
```

#### Constructor Parameters

- `name`: Agent identifier
- `llm`: LLM instance
- `available_tools`: ToolCollection containing available tools
- `system_prompt`: Optional system message
- `next_step_prompt`: Optional prompt for thinking steps
- `tool_choices`: Tool selection strategy
- `max_steps`: Maximum reasoning/action cycles
- `max_observe`: Maximum observation text length
- `enable_tracing`: Enable execution tracing

#### Methods

##### run()
```python
async def run(self, input_text: str) -> str:
```
Process user input and return agent response.

**Parameters:**
- `input_text`: User input to process

**Returns:** Agent's response as string

**Raises:**
- `RuntimeError`: If agent is already running
- `ValueError`: If input is invalid

**Example:**
```python
response = await agent.run("What's the weather in New York?")
print(response)
```

##### reset()
```python
def reset(self) -> None:
```
Reset agent state and clear memory.

**Example:**
```python
agent.reset()  # Clear conversation history
```

##### add_tool()
```python
def add_tool(self, tool: BaseTool) -> None:
```
Add a tool to the agent's available tools.

**Parameters:**
- `tool`: BaseTool instance to add

**Example:**
```python
agent.add_tool(CalculatorTool())
```

##### remove_tool()
```python
def remove_tool(self, tool_name: str) -> None:
```
Remove a tool by name.

**Parameters:**
- `tool_name`: Name of tool to remove

**Example:**
```python
agent.remove_tool("calculator")
```

##### get_memory()
```python
def get_memory(self) -> Memory:
```
Get current conversation memory.

**Returns:** Memory instance containing conversation history

##### set_system_prompt()
```python
def set_system_prompt(self, prompt: str) -> None:
```
Update the system prompt.

**Parameters:**
- `prompt`: New system prompt

#### Properties

##### state
Current agent execution state.

```python
from myagent.schema import AgentState

print(agent.state)  # AgentState.IDLE, RUNNING, FINISHED, or ERROR
```

##### available_tools
ToolCollection containing all available tools.

```python
print(agent.available_tools.tool_names)  # List of tool names
```

##### memory
Conversation memory instance.

```python
messages = agent.memory.messages
print(f"Conversation has {len(messages)} messages")
```

### ReActAgent

**Deprecated:** Legacy class name. Use `ToolCallAgent` instead.

## Agent Configuration

### Tool Choice Strategies

Control how the agent selects tools:

```python
from myagent.schema import ToolChoice

# Let agent decide when to use tools (default)
agent = create_toolcall_agent(tool_choice=ToolChoice.AUTO)

# Never use tools
agent = create_toolcall_agent(tool_choice=ToolChoice.NONE)

# Always use at least one tool
agent = create_toolcall_agent(tool_choice=ToolChoice.REQUIRED)
```

### Step Limiting

Control agent reasoning cycles:

```python
# Maximum 5 think/act cycles
agent = create_toolcall_agent(max_steps=5)

# Unlimited steps (be careful!)
agent = create_toolcall_agent(max_steps=None)
```

### Observation Limiting

Control tool output length:

```python
# Limit tool output to 1000 characters
agent = create_toolcall_agent(max_observe=1000)

# No limit (default: 2000)
agent = create_toolcall_agent(max_observe=None)
```

## Error Handling

### Common Exceptions

#### RuntimeError
Raised when agent is in invalid state:
```python
try:
    # This will fail if agent is already running
    await agent.run("Hello")
except RuntimeError as e:
    print(f"Agent state error: {e}")
```

#### ValueError
Raised for invalid inputs:
```python
try:
    await agent.run("")  # Empty input
except ValueError as e:
    print(f"Invalid input: {e}")
```

#### ToolExecutionError
Raised when tool execution fails:
```python
from myagent.exceptions import ToolExecutionError

try:
    await agent.run("Calculate 1/0")
except ToolExecutionError as e:
    print(f"Tool error: {e}")
```

### Error Recovery

Agents can recover from tool errors:
```python
# Tool errors are reported to the LLM
# Agent can try alternative approaches or ask for clarification
response = await agent.run("Do something impossible")
# Agent will explain why it couldn't complete the task
```

## Performance Considerations

### Memory Management
```python
# Limit conversation history
agent = create_toolcall_agent(
    tools=[...],
    # Memory will keep only last 50 messages
    memory=Memory(max_messages=50)
)
```

### Concurrent Execution
```python
import asyncio

# Run multiple agents concurrently
agents = [create_toolcall_agent() for _ in range(3)]
queries = ["Query 1", "Query 2", "Query 3"]

results = await asyncio.gather(*[
    agent.run(query) for agent, query in zip(agents, queries)
])
```

### Tool Performance
```python
# Use async tools for better performance
class AsyncTool(BaseTool):
    async def execute(self, **kwargs):
        # Async operations don't block other tools
        result = await some_async_operation()
        return ToolResult(output=result)
```

## Tracing Integration

Agents automatically integrate with the tracing system:

```python
from myagent.trace import get_trace_manager

# Get trace manager
trace_manager = get_trace_manager()

# Run agent (automatically traced)
response = await agent.run("Hello")

# Query traces
traces = trace_manager.get_traces_by_agent(agent.name)
```

## Advanced Usage

### Custom Agent Subclassing

For advanced use cases, create custom agent classes:

```python
class CustomAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Custom initialization
    
    async def run(self, input_text: str) -> str:
        # Custom logic
        # Can still use tools, tracing, etc.
        return "Custom response"

# Usage
custom_agent = CustomAgent(
    name="custom",
    llm=LLM()
)
```

### Multi-Agent Coordination

```python
class CoordinatorAgent(ToolCallAgent):
    def __init__(self, sub_agents: list[BaseAgent], **kwargs):
        self.sub_agents = sub_agents
        super().__init__(**kwargs)
    
    async def delegate_task(self, task: str, agent_name: str) -> str:
        agent = next(a for a in self.sub_agents if a.name == agent_name)
        return await agent.run(task)
```

## Migration Guide

### From v1.x to v2.x

```python
# Old (v1.x)
from myagent import create_react_agent
agent = create_react_agent(tools=tools)

# New (v2.x) - Recommended
from myagent import create_toolcall_agent
agent = create_toolcall_agent(tools=tools)
```

The API is backward compatible, but `create_toolcall_agent` is preferred for new code.

## See Also

- **[Tool System API](tools.md)** - Tool development reference
- **[Schema Types API](schema.md)** - Data type reference
- **[LLM Integration API](llm.md)** - LLM configuration reference
- **[Creating Agents Guide](../guides/creating-agents.md)** - Step-by-step guide