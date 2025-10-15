from __future__ import annotations

import asyncio
from typing import Any

from myagent.agent import create_plan_solver

from template_agent.agents import TemplatePlanAgent, TemplateSectionSolver, compile_report


async def main() -> None:
    pipeline = create_plan_solver(
        name="template_report",
        planner=TemplatePlanAgent(),
        solver=TemplateSectionSolver(),
        concurrency=4,
        aggregator=compile_report,
    )

    question = (
        "根据模板生成报告。模板：template/常规团队例会模板.md；"
        "输入数据可参考 datasets/ 目录或 workspace/ 下的用户文件。"
    )

    result = await pipeline.run(question)
    print("Plan summary:", result.plan_summary)
    print("Sections:", [getattr(t, "title", None) for t in result.context.tasks])
    report = result.aggregate_output
    print("Report path:", (report or {}).get("report", {}).get("path"))


if __name__ == "__main__":
    asyncio.run(main())
