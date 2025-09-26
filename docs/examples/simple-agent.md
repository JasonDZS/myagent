# Simple Agent Example

This example demonstrates how to create a basic MyAgent with custom tools. We'll build a calculator agent that can perform mathematical operations.

## Complete Example

```python
import asyncio
from myagent import create_toolcall_agent
from myagent.tool import BaseTool
from myagent.tool.base_tool import ToolResult

class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Perform basic arithmetic calculations (addition, subtraction, multiplication, division)"
    
    async def execute(self, expression: str) -> ToolResult:
        """
        Safely evaluate mathematical expressions.
        
        Args:
            expression: Mathematical expression to evaluate (e.g., "2 + 3 * 4")
            
        Returns:
            ToolResult with calculation result or error message
        """
        try:
            # Simple validation - only allow safe mathematical characters
            allowed_chars = set('0123456789+-*/()., ')
            if not all(c in allowed_chars for c in expression):
                return ToolResult(error="Invalid characters in expression. Only numbers and +, -, *, /, (, ) are allowed.")
            
            # Evaluate the expression
            result = eval(expression)
            
            return ToolResult(output=f"Result: {result}")
            
        except ZeroDivisionError:
            return ToolResult(error="Cannot divide by zero")
        except SyntaxError:
            return ToolResult(error="Invalid mathematical expression")
        except Exception as e:
            return ToolResult(error=f"Calculation error: {str(e)}")

async def main():
    # Create the calculator agent
    agent = create_toolcall_agent(
        name="calculator-agent",
        tools=[CalculatorTool()],
        system_prompt="""You are a helpful calculator assistant. 
        Use the calculator tool to perform mathematical calculations.
        Always show your work and explain the steps when solving complex problems.
        If the user asks for something that's not math-related, politely redirect them to mathematical questions."""
    )
    
    # Example interactions
    test_queries = [
        "What is 15 * 7 + 23?",
        "Calculate the area of a circle with radius 5 (use π ≈ 3.14159)",
        "What's 100 divided by 3?",
        "Solve: (5 + 3) * 2 - 4",
        "What's the square root of 144?",  # This will show agent limitations
    ]
    
    print("🧮 Calculator Agent Demo")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[Query {i}] {query}")
        print("-" * 30)
        
        try:
            response = await agent.run(query)
            print(f"[Response] {response}")
        except Exception as e:
            print(f"[Error] {e}")
        
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

## Step-by-Step Breakdown

### 1. Tool Definition

```python
class CalculatorTool(BaseTool):
    name = "calculator"  # Unique identifier
    description = "Perform basic arithmetic calculations"  # Description for LLM
```

**Key Points:**
- `name`: Must be unique and descriptive
- `description`: Helps the LLM understand when to use the tool
- Inherit from `BaseTool` and implement `execute` method

### 2. Input Validation

```python
# Validate allowed characters
allowed_chars = set('0123456789+-*/()., ')
if not all(c in allowed_chars for c in expression):
    return ToolResult(error="Invalid characters...")
```

**Why validate?**
- Security: Prevent code injection
- User experience: Clear error messages
- Reliability: Avoid unexpected crashes

### 3. Error Handling

```python
try:
    result = eval(expression)
    return ToolResult(output=f"Result: {result}")
except ZeroDivisionError:
    return ToolResult(error="Cannot divide by zero")
except SyntaxError:
    return ToolResult(error="Invalid mathematical expression")
```

**Best Practices:**
- Catch specific exceptions
- Return meaningful error messages
- Never let tools crash silently

### 4. Agent Creation

```python
agent = create_toolcall_agent(
    name="calculator-agent",
    tools=[CalculatorTool()],
    system_prompt="You are a helpful calculator assistant..."
)
```

**Configuration Options:**
- `name`: Agent identifier for tracing
- `tools`: List of available tools
- `system_prompt`: Instructions for the agent's behavior

### 5. Running the Agent

```python
response = await agent.run("What is 15 * 7 + 23?")
```

The agent will:
1. Analyze the user input
2. Decide to use the calculator tool
3. Execute: `calculator(expression="15 * 7 + 23")`
4. Format and return the response

## Expected Output

```
🧮 Calculator Agent Demo
==================================================

[Query 1] What is 15 * 7 + 23?
------------------------------
[Response] I'll calculate that for you.

Let me compute 15 * 7 + 23:
- First: 15 * 7 = 105  
- Then: 105 + 23 = 128

The result is 128.

[Query 2] Calculate the area of a circle with radius 5 (use π ≈ 3.14159)
------------------------------
[Response] I'll calculate the area of a circle with radius 5.

The formula for the area of a circle is A = π * r²

Let me compute this step by step:
- r = 5
- r² = 5 * 5 = 25
- A = π * r² = 3.14159 * 25

The area is approximately 78.54 square units.
```

## Variations and Extensions

### Enhanced Calculator with More Functions

```python
import math

class AdvancedCalculatorTool(BaseTool):
    name = "advanced_calculator"
    description = "Advanced calculator with trigonometric, logarithmic, and other mathematical functions"
    
    async def execute(self, operation: str, *args) -> ToolResult:
        """
        Execute advanced mathematical operations.
        
        Args:
            operation: Function name (sin, cos, log, sqrt, etc.)
            args: Function arguments
        """
        try:
            if operation == "sqrt":
                result = math.sqrt(float(args[0]))
            elif operation == "sin":
                result = math.sin(math.radians(float(args[0])))
            elif operation == "cos":
                result = math.cos(math.radians(float(args[0])))
            elif operation == "log":
                result = math.log(float(args[0]))
            elif operation == "log10":
                result = math.log10(float(args[0]))
            elif operation == "pow":
                result = math.pow(float(args[0]), float(args[1]))
            else:
                return ToolResult(error=f"Unknown operation: {operation}")
            
            return ToolResult(output=f"{operation}({', '.join(map(str, args))}) = {result}")
            
        except ValueError as e:
            return ToolResult(error=f"Invalid arguments: {e}")
        except Exception as e:
            return ToolResult(error=f"Calculation error: {e}")
```

### Multi-Tool Agent

```python
class ConversionTool(BaseTool):
    name = "unit_converter"
    description = "Convert between different units (temperature, length, weight)"
    
    async def execute(self, value: float, from_unit: str, to_unit: str) -> ToolResult:
        # Temperature conversions
        if from_unit == "celsius" and to_unit == "fahrenheit":
            result = (value * 9/5) + 32
            return ToolResult(output=f"{value}°C = {result}°F")
        elif from_unit == "fahrenheit" and to_unit == "celsius":
            result = (value - 32) * 5/9
            return ToolResult(output=f"{value}°F = {result}°C")
        
        # Add more conversions...
        return ToolResult(error=f"Conversion from {from_unit} to {to_unit} not supported")

# Create multi-tool agent
agent = create_toolcall_agent(
    name="math-assistant",
    tools=[
        CalculatorTool(),
        AdvancedCalculatorTool(), 
        ConversionTool()
    ],
    system_prompt="""You are a comprehensive math assistant. You can:
    1. Perform basic arithmetic calculations
    2. Execute advanced mathematical functions
    3. Convert between different units
    
    Always explain your work and use the most appropriate tool for each task."""
)
```

### Memory and Context

```python
from myagent.schema import Memory

# Agent with custom memory settings
agent = create_toolcall_agent(
    name="calculator-agent",
    tools=[CalculatorTool()],
    system_prompt="You are a calculator that remembers previous calculations.",
    # Custom memory configuration
    memory=Memory(max_messages=20)  # Keep last 20 messages
)

# The agent will remember previous calculations
await agent.run("What is 15 * 7?")  # Result: 105
await agent.run("Add 23 to the previous result")  # Will use 105 + 23
```

## Common Patterns

### 1. Input Preprocessing

```python
async def execute(self, expression: str) -> ToolResult:
    # Clean and normalize input
    expression = expression.strip().lower()
    expression = expression.replace("x", "*")  # Allow 'x' for multiplication
    expression = expression.replace("^", "**")  # Allow '^' for exponentiation
    
    # Continue with calculation...
```

### 2. Result Formatting

```python
async def execute(self, expression: str) -> ToolResult:
    result = eval(expression)
    
    # Format result based on type
    if isinstance(result, float):
        if result.is_integer():
            formatted = str(int(result))
        else:
            formatted = f"{result:.6f}".rstrip('0').rstrip('.')
    else:
        formatted = str(result)
    
    return ToolResult(output=f"{expression} = {formatted}")
```

### 3. Tool Chaining

```python
class StatsTool(BaseTool):
    name = "statistics"
    description = "Calculate statistics for a list of numbers"
    
    async def execute(self, numbers: list[float], stat_type: str) -> ToolResult:
        if stat_type == "mean":
            result = sum(numbers) / len(numbers)
        elif stat_type == "median":
            sorted_nums = sorted(numbers)
            n = len(sorted_nums)
            result = sorted_nums[n//2] if n % 2 else (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2
        # ... more statistics
        
        return ToolResult(output=f"{stat_type} of {numbers} = {result}")
```

## Testing Your Agent

```python
import pytest

@pytest.mark.asyncio
async def test_calculator_tool():
    tool = CalculatorTool()
    
    # Test successful calculation
    result = await tool.execute("2 + 2")
    assert result.error is None
    assert "4" in result.output
    
    # Test error handling
    result = await tool.execute("2 / 0")
    assert result.error is not None
    assert "divide by zero" in result.error.lower()

@pytest.mark.asyncio 
async def test_agent_interaction():
    agent = create_toolcall_agent(tools=[CalculatorTool()])
    response = await agent.run("What is 5 * 6?")
    assert "30" in response
```

## Next Steps

This simple example demonstrates the core concepts. To build more sophisticated agents:

1. **[Custom Tools Guide](../guides/custom-tools.md)** - Advanced tool development
2. **[Web Search Agent](web-search.md)** - Agent with external API integration  
3. **[WebSocket Agent](websocket-agent.md)** - Real-time interactive agents
4. **[API Reference](../api/)** - Detailed API documentation

## Tips for Success

1. **Start Simple**: Begin with basic tools and gradually add complexity
2. **Test Early**: Write tests for both tools and agent interactions
3. **Handle Errors**: Always provide meaningful error messages
4. **Clear Descriptions**: Help the LLM understand when to use each tool
5. **Validate Input**: Sanitize and validate all tool inputs
6. **Monitor Performance**: Use tracing to understand agent behavior