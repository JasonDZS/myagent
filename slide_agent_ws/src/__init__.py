"""slide_agent_ws: Database→PPT WebSocket pipeline.

This package provides a clean, well-typed implementation of a Plan→Solve
pipeline specialized for generating PPT slides from database analysis, along
with a WebSocket server entry that exposes progress events and fine-grained
controls (plan cancel/replan and per-slide cancel/restart).

Modules:
- slide_types: Shared dataclasses and helpers (e.g., SlideTask)
- tools: Orchestrator tools for plan/solve communication
- agents: Planner and per-slide solver agents, plus aggregation helpers
- pipeline: Factory to assemble the PlanSolver pipeline
- server: CLI WebSocket server using AgentWebSocketServer
"""

from .slide_types import SlideTask
from .agents import Data2PPTPlanAgent, Data2PPTSlideSolver, compile_presentation
from .pipeline import build_pipeline

__all__ = [
    "SlideTask",
    "Data2PPTPlanAgent",
    "Data2PPTSlideSolver",
    "compile_presentation",
    "build_pipeline",
]
