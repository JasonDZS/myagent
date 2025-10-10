# Plan and Solve Agent Example

This example demonstrates the **Plan and Solve** pattern, an advanced reasoning strategy that improves problem-solving accuracy by separating planning from execution.

## What is Plan and Solve?

Plan and Solve is an enhanced reasoning pattern inspired by research on improving LLM reasoning. Unlike simple ReAct (Reason + Act) agents that interleave thinking and acting, Plan and Solve follows a more structured approach:

1. **PLAN**: Create a detailed, step-by-step plan before starting
2. **SOLVE**: Execute the plan systematically, tracking progress
3. **VERIFY**: Check results and ensure all steps are completed

## Why Use Plan and Solve?

### Advantages over Standard ReAct:

- **Better Planning**: Forces the agent to think through the entire problem before acting
- **Reduced Errors**: Systematic execution reduces the chance of missing steps
- **Progress Tracking**: Built-in task management provides visibility into execution
- **Adaptability**: Plans can be adjusted based on intermediate results
- **Reproducibility**: Clear plans make it easier to understand and debug agent behavior

### When to Use:

- ✅ Complex, multi-step problems
- ✅ Tasks requiring sequential dependencies
- ✅ Problems where planning ahead improves accuracy
- ✅ Scenarios needing progress tracking
- ❌ Simple, single-step queries
- ❌ Tasks requiring heavy exploration/search

## Architecture

### Key Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Plan and Solve Agent                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Planning   │  │   Domain     │  │  Validation  │      │
│  │    Tools     │  │   Tools      │  │    Tools     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│        │                  │                  │               │
│        └──────────────────┴──────────────────┘               │
│                           │                                   │
│                  ┌────────▼────────┐                         │
│                  │  Agent Core     │                         │
│                  │  (ToolCallAgent)│                         │
│                  └─────────────────┘                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Tools Used

1. **write_todos** (from PlanningMiddleware)
   - Creates and manages task plans
   - Tracks execution progress
   - Supports status updates (pending → in_progress → completed)

2. **calculator** (Domain Tool)
   - Performs mathematical calculations
   - Supports basic arithmetic and expressions

3. **knowledge_lookup** (Domain Tool)
   - Retrieves facts and constants
   - Simulates a knowledge base

4. **validate_plan** (Validation Tool)
   - Validates plan completeness
   - Provides quality feedback

## Usage

### Basic Usage

```bash
# Run with default question
uv run python examples/plan_and_solve.py

# Run with custom question
uv run python examples/plan_and_solve.py "Calculate the area of a circle with radius 5"
```

### Example Questions

```bash
# Math problem with multiple steps
uv run python examples/plan_and_solve.py "If a car travels at 60 km/h for 2.5 hours, then at 80 km/h for 1.5 hours, what is the total distance and average speed?"

# Knowledge + calculation
uv run python examples/plan_and_solve.py "What is the circumference of Earth at the equator?"

# Multi-step reasoning
uv run python examples/plan_and_solve.py "If I have 100 dollars and spend 1/4 on food, then 30% of the remainder on transport, how much money do I have left?"
```

## Execution Flow

### Phase 1: Planning

```
User Question → Agent creates plan → write_todos tool → Plan stored
                      ↓
              Optional: validate_plan
```

Example plan for a math problem:
```
📋 Task Planning Overview

⏳ Pending Tasks:
  1. 🟡 Look up required constants or formulas
  2. 🟡 Calculate distance for first segment (60 km/h × 2.5 hours)
  3. 🟡 Calculate distance for second segment (80 km/h × 1.5 hours)
  4. 🟡 Calculate total distance
  5. 🟡 Calculate average speed
  6. 🟡 Formulate final answer
```

### Phase 2: Solving

```
For each pending task:
  1. Mark task as in_progress
  2. Execute using appropriate tool
  3. Mark task as completed
  4. Move to next task
```

Example execution:
```
🔄 Currently Working On:
  🟡 Looking up required constants

[knowledge_lookup executed]

✅ Completed:
  ✓ Look up required constants

🔄 Currently Working On:
  🟡 Calculating distance for first segment

[calculator executed: 60 * 2.5]

✅ Completed:
  ✓ Calculate distance for first segment (60 km/h × 2.5 hours)

... (continues for remaining steps)
```

### Phase 3: Verification

```
All tasks completed → Verify results → terminate tool → Final answer
```

## System Prompt Strategy

The agent uses a specialized system prompt that emphasizes:

1. **Plan-first approach**: Must create plan before solving
2. **Tool usage guidance**: Clear instructions on when to use each tool
3. **Progress tracking**: Explicit instructions to update todo status
4. **Verification**: Emphasis on checking work before completion

Key prompt sections:
```
**Plan and Solve Strategy:**
1. PLAN: Create detailed plan with write_todos
2. SOLVE: Execute step by step, update status
3. VERIFY: Check work and provide clear answer
```

## Comparison with Other Patterns

### vs. Standard ReAct

| Aspect | Standard ReAct | Plan and Solve |
|--------|---------------|----------------|
| Planning | Implicit, on-the-fly | Explicit, upfront |
| Progress Tracking | None | Built-in todos |
| Error Recovery | Harder | Easier (clear plan) |
| Complexity | Lower | Higher |
| Best For | Simple tasks | Complex tasks |

### vs. Chain of Thought (CoT)

| Aspect | Chain of Thought | Plan and Solve |
|--------|-----------------|----------------|
| Structure | Linear reasoning | Plan + Execute |
| Tool Use | Limited | Full support |
| Adaptability | Low | High |
| Verification | Implicit | Explicit |

## Customization

### Adding New Tools

```python
class MyCustomTool(BaseTool):
    name: str = "my_tool"
    description: str = "What this tool does"
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "Parameter description"}
        },
        "required": ["param"]
    }

    async def execute(self, param: str) -> ToolResult:
        # Your implementation
        return ToolResult(output="Result")

# Add to agent
agent = create_react_agent(
    name="plan_solve_agent",
    tools=[
        CalculatorTool(),
        KnowledgeBaseTool(),
        MyCustomTool(),  # Your new tool
    ],
    # ... rest of config
)
```

### Customizing the Planning Strategy

Modify the system prompt to change planning behavior:

```python
system_prompt=(
    "You are an expert that uses Plan and Solve.\n"
    "Custom instructions:\n"
    "- Always create plans with exactly 5 steps\n"
    "- Validate each step before execution\n"
    "- Include contingency steps\n"
    # ... etc
)
```

### Adjusting Max Steps

```python
agent = create_react_agent(
    name="plan_solve_agent",
    tools=[...],
    max_steps=50,  # Increase for more complex problems
)
```

## Advanced Features

### Integration with Middleware

The example uses built-in planning capabilities, but you can add custom middleware:

```python
from myagent.middleware import PlanningMiddleware, MiddlewareChain
from myagent.middleware.base import MiddlewareContext

# Create middleware chain
chain = MiddlewareChain()
chain.add_middleware(PlanningMiddleware())

# Create agent with middleware
agent = create_react_agent(...)

# Process through middleware
context = MiddlewareContext(
    agent=agent,
    tools=agent.available_tools.tools,
    system_prompt_parts=[],
    metadata={}
)
context = await chain.process(context)
```

### WebSocket Streaming Support

The agent supports real-time progress streaming via WebSocket:

```python
from myagent.ws.server import AgentWebSocketServer

def create_plan_solve_agent():
    return create_react_agent(
        name="plan_solve_agent",
        tools=[CalculatorTool(), KnowledgeBaseTool()],
        # ... rest of config
    )

server = AgentWebSocketServer(
    create_plan_solve_agent,
    host="localhost",
    port=8889
)
await server.start()
```

Frontend receives events:
- `THINKING`: Agent's reasoning
- `TOOL_EXECUTION`: Tool calls in progress
- `PARTIAL_ANSWER`: Streaming results
- `COMPLETED`: Final answer

## Troubleshooting

### Agent doesn't create a plan

**Problem**: Agent jumps straight to solving without planning

**Solution**: Strengthen the next_step_prompt:
```python
next_step_prompt=(
    "IMPORTANT: If you haven't created a plan with write_todos yet, "
    "you MUST do that first before any other action!"
)
```

### Plan too simple or too complex

**Problem**: Plans have too few or too many steps

**Solution**: Use the validate_plan tool and provide feedback in the system prompt:
```python
system_prompt=(
    # ...
    "Create plans with 3-7 steps for typical problems. "
    "Use validate_plan to check plan quality."
)
```

### Agent skips progress updates

**Problem**: Todos not updated during execution

**Solution**: Emphasize in prompts:
```python
next_step_prompt=(
    "After each step:\n"
    "1. Mark current task as in_progress BEFORE starting\n"
    "2. Execute the task\n"
    "3. Mark task as completed IMMEDIATELY after finishing\n"
    "4. Move to next pending task"
)
```

## References

- **Plan-and-Solve Prompting**: Wang et al., 2023 - [arXiv:2305.04091](https://arxiv.org/abs/2305.04091)
- **ReAct**: Yao et al., 2022 - [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- **MyAgent Documentation**: [docs/](../docs/)

## Related Examples

- `examples/data2ppt.py` - Complex data analysis with planning
- `examples/web_search.py` - Simple ReAct pattern
- `examples/research_agent.py` - Research with planning

## License

Same as MyAgent project license.
