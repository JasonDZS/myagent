"""Plan and Solve Agent Example for myagent.

This example demonstrates the Plan and Solve pattern, which is an improved
reasoning approach that:
1. First creates a detailed plan to solve the problem
2. Then executes the plan step by step
3. Uses the planning tool to track progress

The Plan and Solve pattern is particularly effective for complex, multi-step
problems that require careful planning and systematic execution.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any, ClassVar

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult
from myagent.tool.planning import PlanningTool


class CalculatorTool(BaseTool):
    """Simple calculator tool for mathematical operations."""

    name: str = "calculator"
    description: str = "Perform basic mathematical calculations. Supports +, -, *, /, ** (power), and parentheses."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * (5 + 3)')",
            }
        },
        "required": ["expression"],
    }

    async def execute(self, expression: str) -> ToolResult:
        """Execute a mathematical calculation."""
        try:
            # Simple safety check - only allow basic math operators and decimal point
            allowed_chars = set("0123456789+-*/().** ")
            if not all(c in allowed_chars for c in expression):
                return ToolResult(
                    error=f"Invalid characters in expression. Only numbers and operators (+, -, *, /, **, parentheses) are allowed."
                )

            # Evaluate the expression in a safe namespace
            import math
            safe_namespace = {
                "__builtins__": {},
                "pi": math.pi,
                "e": math.e,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
            }
            result = eval(expression, safe_namespace)

            return ToolResult(
                output=f"Result: {result}",
                system=f"Calculation completed: {expression} = {result}"
            )
        except Exception as e:
            return ToolResult(error=f"Calculation failed: {e}")


class KnowledgeBaseTool(BaseTool):
    """Simulated knowledge base tool for retrieving information."""

    name: str = "knowledge_lookup"
    description: str = "Look up factual information from a knowledge base. Useful for retrieving constants, formulas, or known facts."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The information to look up (e.g., 'speed of light', 'pi value', 'earth radius')",
            }
        },
        "required": ["query"],
    }

    # Simulated knowledge base
    _knowledge_base: ClassVar[dict[str, str]] = {
        "speed of light": "299,792,458 meters per second",
        "pi": "3.14159265359",
        "earth radius": "6,371 kilometers",
        "gravity": "9.8 m/s²",
        "avogadro number": "6.02214076 × 10²³",
        "planck constant": "6.62607015 × 10⁻³⁴ J⋅s",
        "electron mass": "9.10938356 × 10⁻³¹ kg",
        "golden ratio": "1.618033988749",
    }

    async def execute(self, query: str) -> ToolResult:
        """Look up information from the knowledge base."""
        query_lower = query.lower().strip()

        # Search for matching entries
        for key, value in self._knowledge_base.items():
            if key in query_lower or query_lower in key:
                return ToolResult(
                    output=f"{key.title()}: {value}",
                    system=f"Found knowledge: {key}"
                )

        return ToolResult(
            output=f"No information found for '{query}'. Available topics: {', '.join(self._knowledge_base.keys())}",
            system=f"Knowledge lookup failed for: {query}"
        )


class PlanValidatorTool(BaseTool):
    """Tool to validate and provide feedback on plans."""

    name: str = "validate_plan"
    description: str = "Validate a plan and provide feedback on its completeness and correctness."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "plan_steps": {
                "type": "array",
                "description": "List of plan steps to validate",
                "items": {"type": "string"}
            }
        },
        "required": ["plan_steps"],
    }

    async def execute(self, plan_steps: list[str]) -> ToolResult:
        """Validate a plan."""
        if not plan_steps:
            return ToolResult(error="Plan is empty. Please provide at least one step.")

        feedback = []
        feedback.append(f"✓ Plan contains {len(plan_steps)} steps")

        # Check for common plan quality indicators
        has_data_collection = any("lookup" in step.lower() or "gather" in step.lower() or "find" in step.lower() for step in plan_steps)
        has_calculation = any("calculate" in step.lower() or "compute" in step.lower() for step in plan_steps)
        has_final_answer = any("answer" in step.lower() or "result" in step.lower() or "conclude" in step.lower() for step in plan_steps)

        if has_data_collection:
            feedback.append("✓ Plan includes data collection/lookup")
        else:
            feedback.append("⚠ Consider adding a data collection step if needed")

        if has_calculation:
            feedback.append("✓ Plan includes calculation steps")

        if has_final_answer:
            feedback.append("✓ Plan includes final answer step")
        else:
            feedback.append("⚠ Consider adding a step to formulate the final answer")

        # Check step quality
        if len(plan_steps) < 2:
            feedback.append("⚠ Plan seems too simple. Consider breaking it into more detailed steps.")
        elif len(plan_steps) > 10:
            feedback.append("⚠ Plan is very detailed. Consider if all steps are necessary.")

        validation_result = "\n".join(feedback)

        return ToolResult(
            output=validation_result,
            system=f"Plan validation completed with {len(feedback)} feedback items"
        )


# Create Plan and Solve agent with planning tool
agent = create_react_agent(
    name="plan_solve_agent",
    tools=[
        PlanningTool(),  # Add planning tool for task management
        CalculatorTool(),
        KnowledgeBaseTool(),
        PlanValidatorTool(),
    ],
    system_prompt=(
        "You are an expert problem solver that uses the Plan and Solve strategy.\n\n"
        "**Plan and Solve Strategy:**\n"
        "1. PLAN: First, create a detailed plan to solve the problem\n"
        "   - Break down the problem into clear, logical steps\n"
        "   - Identify what information you need\n"
        "   - Determine which tools to use for each step\n"
        "   - Use the write_todos tool to create your plan\n"
        "   - Optionally validate your plan with the validate_plan tool\n\n"
        "2. SOLVE: Execute the plan step by step\n"
        "   - Follow your plan systematically\n"
        "   - Update todo status as you progress (mark as in_progress, then completed)\n"
        "   - Use available tools (calculator, knowledge_lookup) as needed\n"
        "   - Be flexible - adjust the plan if needed based on intermediate results\n\n"
        "3. VERIFY: Check your work\n"
        "   - Verify calculations are correct\n"
        "   - Ensure all steps were completed\n"
        "   - Provide a clear final answer\n\n"
        "**Available Tools:**\n"
        "- write_todos: Create and track your plan\n"
        "- validate_plan: Validate your plan before execution\n"
        "- calculator: Perform mathematical calculations\n"
        "- knowledge_lookup: Look up facts and constants\n"
        "- terminate: End the task when complete\n\n"
        "Always start by creating a plan before solving!"
    ),
    next_step_prompt=(
        "Follow the Plan and Solve strategy:\n"
        "1. If you haven't created a plan yet, use write_todos to create one\n"
        "2. If you have a plan, execute the next pending step\n"
        "3. Update todo status as you progress\n"
        "4. When all steps are done, use terminate tool"
    ),
    max_steps=25,
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan and Solve Agent - Demonstrates systematic problem solving with planning"
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="If a car travels at 60 km/h for 2.5 hours, then at 80 km/h for 1.5 hours, what is the total distance traveled and average speed?",
        help="Problem to solve using Plan and Solve strategy",
    )
    args = parser.parse_args()

    print(f"Question: {args.question}\n")
    print("=" * 80)
    print("Starting Plan and Solve Agent...")
    print("=" * 80)
    print()

    result = await agent.run(args.question)

    print("\n" + "=" * 80)
    print("✅ Agent execution completed")
    print("=" * 80)
    print("\n📋 Execution Summary:")
    print(result)

    print("\n" + "=" * 80)
    print("📊 Final Answer:")
    print("=" * 80)
    print(agent.final_response)


if __name__ == "__main__":
    asyncio.run(main())
