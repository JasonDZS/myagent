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
    from myagent.ws.events import AgentEvents, create_event
    from myagent.logger import logger
    import json
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

try:
    # For preloading remote resources & binding VFS to a session
    from src.tools import LoadRemoteResourcesTool, vfs_bind_session
except Exception:  # pragma: no cover
    LoadRemoteResourcesTool = None  # type: ignore
    vfs_bind_session = None  # type: ignore


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


class TemplateAgentWebSocketServer(AgentWebSocketServer):
    """WS server with support for structured user.message content.

    If the client sends content as an object with fields like
    { question, template_name/template_id, knowledge_base_name/database_id, api_base_url },
    we will:
    - Extract the question text and pass it to the agent
    - Persist the template/db/api hints onto the AgentSession for this session
      (tools can read them from current ws_session context)
    """

    async def _handle_user_message(
        self,
        websocket,
        connection_id: str,
        session_id: str,
        message: dict,
    ) -> None:  # type: ignore[override]
        session = self.sessions.get(session_id)
        if not session:
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session not found",
                ),
            )
            return

        # Enforce session-connection binding
        if session.connection_id != connection_id:
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Session does not belong to this connection",
                ),
            )
            return

        content = message.get("content", "")
        user_input: str
        if isinstance(content, dict):
            # Extract question and persist template/db hints on session
            question = str(content.get("question") or "").strip()
            hints = {}
            for k in ("template_name", "template_id", "knowledge_base_name", "database_id", "api_base_url"):
                v = content.get(k)
                if isinstance(v, str) and v.strip():
                    hints[k] = v.strip()
            # Attach hints to session for tools to read via ws_session context
            try:
                current_meta = getattr(session, "session_metadata", {}) or {}
                current_meta.update(hints)
                session.session_metadata = current_meta
            except Exception:
                session.session_metadata = hints

            user_input = question or json.dumps({k: v for k, v in content.items() if k != "tasks"}, ensure_ascii=False)
        else:
            user_input = str(content or "")

        if not user_input.strip():
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content="Message content cannot be empty",
                ),
            )
            return

        logger.info(
            f"Processing user message for session {session_id}: {user_input[:80]}..."
        )

        # Preload remote resources into VFS for this session prior to agent execution
        try:
            if LoadRemoteResourcesTool and vfs_bind_session:
                # Only attempt when we have at least one template and one database hint
                has_template_hint = any(
                    isinstance(getattr(session, "session_metadata", {}).get(k), str) and getattr(session, "session_metadata", {}).get(k)
                    for k in ("template_name", "template_id")
                )
                has_db_hint = any(
                    isinstance(getattr(session, "session_metadata", {}).get(k), str) and getattr(session, "session_metadata", {}).get(k)
                    for k in ("knowledge_base_name", "database_id")
                )

                if has_template_hint and has_db_hint:
                    md = getattr(session, "session_metadata", {}) or {}
                    with vfs_bind_session(session_id):
                        loader = LoadRemoteResourcesTool()
                        tr = await loader.execute(
                            template_name=md.get("template_name"),
                            template_id=md.get("template_id"),
                            knowledge_base_name=md.get("knowledge_base_name"),
                            database_id=md.get("database_id"),
                            api_base_url=md.get("api_base_url"),
                        )
                        if getattr(tr, "error", None):
                            logger.warning(f"Resource preload failed for session {session_id}: {tr.error}")
                        else:
                            logger.info(f"Resource preload complete for session {session_id}")
                else:
                    logger.info(
                        f"Skipping resource preload for session {session_id}: missing template/database hints"
                    )
        except Exception as e:
            logger.warning(f"Exception during resource preload for session {session_id}: {e!s}")

        # Execute Agent asynchronously and stream results (in separate task)
        try:
            await session.execute_streaming(user_input)
        except Exception as e:
            await self._send_event(
                websocket,
                create_event(
                    AgentEvents.ERROR,
                    session_id=session_id,
                    content=f"Agent execution error: {e!s}",
                ),
            )


async def main(host: str, port: int) -> None:
    server = TemplateAgentWebSocketServer(agent_factory, host=host, port=port)
    try:
        logger.info("TemplateAgentWebSocketServer started with structured content support")
    except Exception:
        pass
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
