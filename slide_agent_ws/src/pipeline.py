from __future__ import annotations

import os
from typing import Any

from myagent.agent import create_plan_solver

from .agents import Data2PPTPlanAgent, Data2PPTSlideSolver, compile_presentation


def _get_int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
        return value if value > 0 else default
    except Exception:
        return default


def build_pipeline(*, name: str = "plan_solve_data2ppt", **kwargs: Any):
    """Create a fresh pipeline instance for DB→PPT slide generation.

    Respects the following optional environment variables:
    - SLIDE_WS_CONCURRENCY: max concurrent slide solvers (default 5)
    """
    concurrency = _get_int_env("SLIDE_WS_CONCURRENCY", 5)
    return create_plan_solver(
        name=name,
        planner=Data2PPTPlanAgent(),
        solver=Data2PPTSlideSolver(),
        concurrency=concurrency,
        aggregator=compile_presentation,
        **kwargs,
    )

