from __future__ import annotations

import argparse
import asyncio
import os

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]

if load_dotenv:
    try:
        from pathlib import Path

        here = Path(__file__).resolve().parent
        load_dotenv(here.parent / ".env", override=False)
        load_dotenv(here / ".env", override=False)
    except Exception:
        pass

try:
    from myagent.agent.plan_solver import create_plan_solver_session_agent
    from myagent.ws import AgentWebSocketServer
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from myagent.agent.plan_solver import create_plan_solver_session_agent
    from myagent.ws import AgentWebSocketServer

try:
    from src.pipeline import build_pipeline
except Exception:  # pragma: no cover
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.pipeline import build_pipeline


def _get_bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    lowered = val.strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    return default


def _get_int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
        return value if value >= 0 else default
    except Exception:
        return default


def agent_factory():
    pipeline = build_pipeline()
    return create_plan_solver_session_agent(
        pipeline,
        name="template_agent_ws",
        broadcast_tasks=_get_bool_env("TEMPLATE_WS_BROADCAST_TASKS", True),
        max_retry_attempts=_get_int_env("TEMPLATE_WS_MAX_RETRY", 1),
        retry_delay_seconds=float(os.environ.get("TEMPLATE_WS_RETRY_DELAY", "3.0")),
        require_plan_confirmation=_get_bool_env("TEMPLATE_WS_REQUIRE_CONFIRM", True),
        plan_confirmation_timeout=_get_int_env("TEMPLATE_WS_CONFIRM_TIMEOUT", 600),
    )


async def main(host: str, port: int) -> None:
    server = AgentWebSocketServer(agent_factory, host=host, port=port)
    await server.start_server()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run template_agent Plan & Solve pipeline as a WebSocket service."
    )
    parser.add_argument("--host", default="127.0.0.1", help="WebSocket server host")
    parser.add_argument("--port", type=int, default=8081, help="WebSocket server port")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print("\nServer stopped by user.")

