"""WebSocket server example for Plan & Solve Data→PPT pipeline."""

from __future__ import annotations

import argparse
import asyncio

from myagent.agent.plan_solver import (
    create_plan_solver,
    create_plan_solver_session_agent,
)
from myagent.ws import AgentWebSocketServer

from plan_solve_data2ppt import (
    Data2PPTPlanAgent,
    Data2PPTSlideSolver,
    compile_presentation,
)


def build_pipeline():
    """Create a fresh pipeline instance for each WebSocket session."""
    return create_plan_solver(
        name="plan_solve_data2ppt",
        planner=Data2PPTPlanAgent(),
        solver=Data2PPTSlideSolver(),
        concurrency=3,
        aggregator=compile_presentation,
    )


def agent_factory():
    pipeline = build_pipeline()
    return create_plan_solver_session_agent(
        pipeline,
        name="plan_solve_data2ppt_ws",
        broadcast_tasks=True,
    )


async def main(host: str, port: int) -> None:
    server = AgentWebSocketServer(agent_factory, host=host, port=port)
    await server.start_server()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Plan & Solve Data→PPT pipeline as a WebSocket service."
    )
    parser.add_argument("--host", default="127.0.0.1", help="WebSocket server host")
    parser.add_argument("--port", type=int, default=8080, help="WebSocket server port")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
