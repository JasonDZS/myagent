# Quick Start Guide

Get up and running with MyAgent in less than 5 minutes! This guide will help you create your first agent and understand the basic concepts.

## Installation

```bash
# Install the package
pip install myagent

# Or using uv
uv add myagent
```

## Basic Setup

### 1. Environment Configuration

Create a `.env` file in your project directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1  # optional

# Other LLM providers can be configured similarly
```

### 2. Your First Agent

Create a simple agent that can perform basic calculations:

```python
import asyncio
from myagent import create_toolcall_agent
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult

# Define a custom calculator tool
class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Perform basic arithmetic calculations"
    
    async def execute(self, expression: str) -> ToolResult:
        """Safely evaluate mathematical expressions"""
        try:
            # Simple evaluation for demo (use a safer alternative in production)
            result = eval(expression)
            return ToolResult(output=f"Result: {result}")
        except Exception as e:
            return ToolResult(error=f"Calculation error: {e}")

# Create the agent
async def main():
    # Create agent with the calculator tool
    agent = create_toolcall_agent(
        name="calculator-agent",
        tools=[CalculatorTool()],
        system_prompt="You are a helpful calculator assistant. Use the calculator tool for any math operations."
    )
    
    # Run the agent
    result = await agent.run("What is 15 * 7 + 23?")
    print(f"Agent response: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Run Your Agent

```bash
python my_first_agent.py
```

Expected output:
```
Agent response: I'll calculate 15 * 7 + 23 for you.

First, let me compute this step by step:
- 15 * 7 = 105
- 105 + 23 = 128

The result is 128.
```

## Understanding the Code

Let's break down what happened:

### 1. Tool Definition
```python
class CalculatorTool(BaseTool):
    name = "calculator"  # Tool identifier
    description = "Perform basic arithmetic calculations"  # Tool description for LLM
    
    async def execute(self, expression: str) -> ToolResult:
        # Tool implementation
        pass
```

All custom tools inherit from `BaseTool` and must implement the `execute` method.

### 2. Agent Creation
```python
agent = create_toolcall_agent(
    name="calculator-agent",
    tools=[CalculatorTool()],
    system_prompt="..."  # Instructions for the agent
)
```

The `create_toolcall_agent` function creates an agent that can reason about when and how to use tools.

### 3. Agent Execution
```python
result = await agent.run("What is 15 * 7 + 23?")
```

The agent analyzes the user input, decides which tools to use, executes them, and formulates a response.

## Key Concepts

### ReAct Pattern
MyAgent implements the **ReAct** (Reasoning + Acting) pattern:
1. **Reason**: The agent analyzes the input and plans actions
2. **Act**: The agent executes tools to gather information or perform tasks
3. **Observe**: The agent processes tool results
4. **Repeat**: The cycle continues until the task is complete

### Tool System
- **Tools** are the building blocks of agent capabilities
- **ToolCollection** manages multiple tools
- **ToolResult** standardizes tool outputs
- Built-in tools like `Terminate` are automatically added

### Tracing
Every agent execution is automatically traced, providing:
- Complete execution history
- Performance metrics
- Debug information
- Tool usage analytics

## Next Steps

Now that you have a basic agent running, explore these topics:

1. **[Creating Custom Tools](custom-tools.md)** - Build more sophisticated tools
2. **[Agent Configuration](configuration.md)** - Advanced agent settings
3. **[WebSocket Server](../websocket/server-setup.md)** - Real-time agent interactions
4. **[Tracing System](../tracing/overview.md)** - Debug and monitor your agents

## Common Patterns

### Multi-Tool Agent
```python
from myagent.tool import Terminate

agent = create_toolcall_agent(
    tools=[
        CalculatorTool(),
        WeatherTool(),
        SearchTool(),
        # Terminate tool is added automatically
    ]
)
```

### Error Handling
```python
try:
    result = await agent.run("Your query")
    print(result)
except Exception as e:
    print(f"Agent error: {e}")
```

### System Prompts
```python
agent = create_toolcall_agent(
    tools=[...],
    system_prompt="""You are a helpful assistant specializing in data analysis.
    Always explain your reasoning and show your work step by step.
    If you're unsure about something, ask for clarification."""
)
```

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   Error: OpenAI API key not found
   ```
   Solution: Make sure your `.env` file contains `OPENAI_API_KEY`

2. **Tool Not Found**
   ```
   Error: No tool named 'calculator' found
   ```
   Solution: Check that your tool's `name` attribute matches what the agent expects

3. **Import Errors**
   ```
   ModuleNotFoundError: No module named 'myagent'
   ```
   Solution: Install the package with `pip install myagent`

### Getting Help

- Check the [Examples Directory](../../examples/) for working code
- Review the [API Documentation](../api/) for detailed reference
- Open an issue on [GitHub](https://github.com/yourusername/myagent/issues)

---

Ready to build more sophisticated agents? Continue with [Basic Concepts](basic-concepts.md) to deepen your understanding.