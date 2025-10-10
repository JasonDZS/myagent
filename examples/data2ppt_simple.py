"""Simple Data to PPT example for myagent.
Generates PPT slides in JSON format with demo data or from user input.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, ClassVar

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult


class GeneratePPTTool(BaseTool):
    name: str = "generate_ppt"
    description: str = """Generate PPT slides in JSON format based on analysis insights.
    Each slide must have: id (integer), title (string), text (string).
    Optional: charts array with data points (name, value), chart type (bar/line/pie/area), and layout (single/double)."""

    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "slides": {
                "type": "array",
                "description": "Array of slide objects to generate PPT presentation.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "Unique slide identifier (starting from 1)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Slide title",
                        },
                        "text": {
                            "type": "string",
                            "description": "Slide content text",
                        },
                        "charts": {
                            "type": "array",
                            "description": "Optional charts array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["bar", "line", "pie", "area"],
                                        "description": "Chart type (default: bar)",
                                    },
                                    "title": {
                                        "type": "string",
                                        "description": "Chart title",
                                    },
                                    "data": {
                                        "type": "array",
                                        "description": "Chart data points",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "value": {"type": "number"},
                                            },
                                            "required": ["name", "value"],
                                        },
                                    },
                                    "horizontal": {
                                        "type": "boolean",
                                        "description": "For bar charts, whether to display horizontally",
                                    },
                                },
                                "required": ["data"],
                            },
                        },
                        "layout": {
                            "type": "string",
                            "enum": ["single", "double"],
                            "description": "Chart layout: single (1 chart) or double (2 charts side-by-side)",
                        },
                    },
                    "required": ["id", "title", "text"],
                },
            }
        },
        "required": ["slides"],
    }

    async def execute(self, slides: list[dict[str, Any]]) -> ToolResult:
        try:
            # Validate slide structure
            for slide in slides:
                if "id" not in slide or "title" not in slide or "text" not in slide:
                    return ToolResult(
                        error=f"Invalid slide structure. Each slide must have id, title, and text fields."
                    )

                if "charts" in slide:
                    for chart in slide["charts"]:
                        if "data" not in chart:
                            return ToolResult(
                                error=f"Invalid chart in slide {slide['id']}. Each chart must have a 'data' field."
                            )
                        for data_point in chart["data"]:
                            if "name" not in data_point or "value" not in data_point:
                                return ToolResult(
                                    error=f"Invalid chart data in slide {slide['id']}. Each data point must have 'name' and 'value'."
                                )

            # Generate JSON output
            ppt_json = json.dumps(slides, ensure_ascii=False, indent=2)

            # Save to file
            os.makedirs("./workdir/ppt", exist_ok=True)
            output_file = "./workdir/ppt/presentation.json"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(ppt_json)

            return ToolResult(
                output=f"✅ PPT JSON generated successfully!\n\n📁 File saved to: {output_file}\n📊 Slide count: {len(slides)}\n\n📄 JSON Preview:\n{ppt_json}",
                system=f"PPT generation completed with {len(slides)} slides",
            )
        except Exception as exc:
            return ToolResult(error=f"PPT generation failed: {exc}")


# Initialize tool
ppt_tool = GeneratePPTTool()

# Create agent
agent = create_react_agent(
    name="data2ppt",
    tools=[ppt_tool],
    system_prompt=(
        "You are a professional presentation creator that generates well-structured PPT slides in JSON format.\n\n"
        "PPT Format Guidelines:\n"
        "- Each slide MUST have: id (integer starting from 1), title (string), text (string)\n"
        "- Optional charts array with data points [{name: string, value: number}]\n"
        "- Chart types: 'bar', 'line', 'pie', 'area' (default: bar if not specified)\n"
        "- Layout: 'single' (1 chart) or 'double' (2 charts side-by-side)\n"
        "- For bar charts, use 'horizontal: true' for horizontal orientation\n\n"
        "Example slide structures:\n\n"
        "1. Text-only slide:\n"
        "{\n"
        '  "id": 1,\n'
        '  "title": "Introduction",\n'
        '  "text": "Welcome to the presentation..."\n'
        "}\n\n"
        "2. Slide with single chart:\n"
        "{\n"
        '  "id": 2,\n'
        '  "title": "Sales Analysis",\n'
        '  "text": "Q1 sales show strong growth...",\n'
        '  "charts": [{\n'
        '    "type": "bar",\n'
        '    "title": "Quarterly Sales",\n'
        '    "data": [{"name": "Q1", "value": 1200}, {"name": "Q2", "value": 1500}]\n'
        '  }],\n'
        '  "layout": "single"\n'
        "}\n\n"
        "3. Slide with double charts:\n"
        "{\n"
        '  "id": 3,\n'
        '  "title": "Revenue vs Expenses",\n'
        '  "text": "Financial comparison...",\n'
        '  "charts": [\n'
        '    {"type": "pie", "title": "Revenue", "data": [...]},\n'
        '    {"type": "pie", "title": "Expenses", "data": [...]}\n'
        '  ],\n'
        '  "layout": "double"\n'
        "}\n\n"
        "When user requests a presentation, create appropriate slides with meaningful data and visualizations."
    ),
    next_step_prompt=(
        "Use the generate_ppt tool to create professional PPT slides based on the user's request. "
        "Include appropriate charts and data visualizations. "
        "When you have completed the PPT generation, use the terminate tool to end the task."
    ),
    max_steps=10,
    enable_tracing=False,
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Data to PPT generator - creates professional PPT slides in JSON format"
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default="创建一个关于公司季度业绩的PPT报告，包含3-5页幻灯片",
        help="Topic or description for PPT generation",
    )
    args = parser.parse_args()

    print(f"🎯 Topic: {args.topic}\n")
    print("🤖 Generating PPT presentation...\n")

    result = await agent.run(args.topic)

    print("\n" + "="*60)
    print("✅ Agent execution completed")
    print("="*60)

    print("\n📊 Final response:")
    print(agent.final_response)

    print(
        "\n💡 Tip: Check ./workdir/ppt/presentation.json for the generated PPT slides"
    )


if __name__ == "__main__":
    asyncio.run(main())
