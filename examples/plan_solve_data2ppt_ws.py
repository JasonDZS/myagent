"""WebSocket server example for Plan & Solve Data→PPT pipeline.

The server broadcasts pipeline progress events. Both `plan.completed` and
`solver.completed` payloads expose a `statistics` field mirroring each
agent's `get_statistics()` output so clients can track LLM usage cost for the
planning stage and for every solver task in real time.
"""

from __future__ import annotations

import argparse
import asyncio

from myagent.agent.plan_solver import create_plan_solver_session_agent
from myagent.ws import AgentWebSocketServer

# Use the implementation under slide_agent_ws for better structure and reusability
from slide_agent_ws.pipeline import build_pipeline as build_pipeline_impl


def build_pipeline():
    """Create a fresh pipeline instance for each WebSocket session."""
    return build_pipeline_impl()


def agent_factory():
    pipeline = build_pipeline()
    return create_plan_solver_session_agent(
        pipeline,
        name="plan_solve_data2ppt_ws",
        broadcast_tasks=True,
        max_retry_attempts=1,
        retry_delay_seconds=3.0,
        require_plan_confirmation=True,
        plan_confirmation_timeout=600,
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
