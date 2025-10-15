from __future__ import annotations

import os
from typing import Any

from myagent.agent import create_plan_solver

from .agents import TemplatePlanAgent, TemplateSectionSolver, compile_report


def _get_int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
        return value if value > 0 else default
    except Exception:
        return default


def build_pipeline(*, name: str = "template_report_pipeline", **kwargs: Any):
    """Create a Plan & Solve pipeline for template-based report generation.

    Environment variables:
    - TEMPLATE_WS_CONCURRENCY: max concurrent section solvers (default 5)
    """
    concurrency = _get_int_env("TEMPLATE_WS_CONCURRENCY", 5)
    return create_plan_solver(
        name=name,
        planner=TemplatePlanAgent(),
        solver=TemplateSectionSolver(),
        concurrency=concurrency,
        aggregator=compile_report,
        **kwargs,
    )

