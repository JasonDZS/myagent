from __future__ import annotations

import argparse
import asyncio
import os

# Attempt to load .env for environment configuration
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]

if load_dotenv:
    try:
        from pathlib import Path

        here = Path(__file__).resolve().parent
        # Load .env from repo root then local; do not override existing env
        load_dotenv(here.parent / ".env", override=False)
        load_dotenv(here / ".env", override=False)
    except Exception:
        pass

# Ensure parent directory is importable when run as a script
try:
    from myagent.agent.plan_solver import create_plan_solver_session_agent
    from myagent.ws import AgentWebSocketServer
except Exception:  # pragma: no cover - fallback when executed as a script
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from myagent.agent.plan_solver import create_plan_solver_session_agent
    from myagent.ws import AgentWebSocketServer

# Support running both as a module and as a script.
try:  # Prefer package-relative import
    from src.pipeline import build_pipeline
except Exception:  # pragma: no cover - fallback when executed as a script
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
        name="plan_solve_data2ppt_ws",
        broadcast_tasks=_get_bool_env("SLIDE_WS_BROADCAST_TASKS", True),
        max_retry_attempts=_get_int_env("SLIDE_WS_MAX_RETRY", 1),
        retry_delay_seconds=float(os.environ.get("SLIDE_WS_RETRY_DELAY", "3.0")),
        require_plan_confirmation=_get_bool_env("SLIDE_WS_REQUIRE_CONFIRM", True),
        plan_confirmation_timeout=_get_int_env("SLIDE_WS_CONFIRM_TIMEOUT", 600),
    )


async def main(host: str, port: int) -> None:
    server = AgentWebSocketServer(agent_factory, host=host, port=port)

    def _configure_api_from_session(content: dict | None) -> None:
        """Configure API-backed DB settings per session when DB_TYPE=api.

        Supported payload shapes (any of these works):
        - { "api": { "dataset_id": 123, "token": "<jwt>", "scheme": "Bearer", "base_url": "http://.../api" } }
        - { "dataset_id": 123, "auth": { "token": "<jwt>", "scheme": "Bearer" }, "api_base_url": "http://.../api" }
        - { "datasetId": 123, "token": "<jwt>" }
        Sets env vars used by tools: API_BASE_URL, API_DATASET_ID, API_AUTH_TOKEN, API_AUTH_SCHEME.
        """
        try:
            if (os.environ.get("DB_TYPE", "").strip().lower() != "api"):
                return
            if not isinstance(content, dict):
                return

            api_obj = content.get("api") if isinstance(content.get("api"), dict) else None
            dataset_id = (
                (api_obj or {}).get("dataset_id")
                or content.get("dataset_id")
                or content.get("datasetId")
            )
            if dataset_id is not None:
                try:
                    os.environ["API_DATASET_ID"] = str(int(dataset_id))
                except Exception:
                    pass

            # base url
            base_url = (
                (api_obj or {}).get("base_url")
                or content.get("api_base_url")
                or content.get("base_url")
            )
            if base_url and isinstance(base_url, str) and base_url.strip():
                os.environ["API_BASE_URL"] = base_url.strip().rstrip("/")

            # token & scheme
            token = (
                (api_obj or {}).get("token")
                or (content.get("auth") or {}).get("token")
                or content.get("token")
            )
            scheme = (
                (api_obj or {}).get("scheme")
                or (content.get("auth") or {}).get("scheme")
                or content.get("scheme")
                or "Bearer"
            )
            if token and isinstance(token, str):
                os.environ["API_AUTH_TOKEN"] = token
                os.environ["API_AUTH_SCHEME"] = str(scheme or "Bearer")
            # Created-session log: print dataset/auth info (mask token)
            try:
                def _mask(tok: str | None) -> str:
                    if not tok:
                        return "<unset>"
                    s = str(tok)
                    if len(s) <= 8:
                        return "*" * len(s)
                    return s[:4] + "*" * (len(s) - 8) + s[-4:]
                print(
                    "[slide_agent] Created session: ",
                    {
                        "dataset_id": os.environ.get("API_DATASET_ID", "<unset>"),
                        "auth_scheme": os.environ.get("API_AUTH_SCHEME", "<unset>"),
                        "auth_token": _mask(os.environ.get("API_AUTH_TOKEN")),
                    },
                )
            except Exception:
                pass
            # Print effective API config for debugging (mask token)
            def _mask(tok: str | None) -> str:
                if not tok:
                    return "<unset>"
                s = str(tok)
                if len(s) <= 8:
                    return "*" * len(s)
                return s[:4] + "*" * (len(s) - 8) + s[-4:]
            try:
                print(
                    "[slide_agent] API config: ",
                    {
                        "DB_TYPE": os.environ.get("DB_TYPE"),
                        "API_BASE_URL": os.environ.get("API_BASE_URL", "<unset>"),
                        "API_DATASET_ID": os.environ.get("API_DATASET_ID", "<unset>"),
                        "API_AUTH_SCHEME": os.environ.get("API_AUTH_SCHEME", "<unset>"),
                        "API_AUTH_TOKEN": _mask(os.environ.get("API_AUTH_TOKEN")),
                    },
                )
            except Exception:
                pass
        except Exception:
            # Defensive: never let session creation fail due to env configuration
            pass

    # Try to register a session-init hook if the server supports it
    try:
        hooked = False
        if hasattr(server, "set_session_init_handler"):
            server.set_session_init_handler(_configure_api_from_session)  # type: ignore[attr-defined]
            print("[slide_agent] session_init_handler registered via set_session_init_handler")
            hooked = True
        elif hasattr(server, "on_session_created"):
            server.on_session_created(_configure_api_from_session)  # type: ignore[attr-defined]
            print("[slide_agent] session_init_handler registered via on_session_created")
            hooked = True
        elif hasattr(server, "session_init_handler"):
            setattr(server, "session_init_handler", _configure_api_from_session)
            print("[slide_agent] session_init_handler attached to attribute 'session_init_handler'")
            hooked = True

        # Monkey-patch known internal handlers as a fallback (signature-agnostic)
        if not hooked:
            for name in (
                "handle_user_create_session",
                "on_user_create_session",
                "user_create_session",
                "_handle_user_create_session",
            ):
                if hasattr(server, name):
                    try:
                        original = getattr(server, name)

                        def _wrapper(*args, **kwargs):  # type: ignore[no-redef]
                            # Try to extract a dict-like payload containing content
                            content = None
                            try:
                                seq = list(args) + list(kwargs.values())
                                for v in seq:
                                    if isinstance(v, dict) and isinstance(v.get("content"), dict):
                                        content = v.get("content")
                                        break
                                    if isinstance(v, dict) and not content:
                                        # might be the content itself
                                        content = v
                            except Exception:
                                content = None
                            try:
                                _configure_api_from_session(content if isinstance(content, dict) else None)
                            except Exception:
                                pass
                            return original(*args, **kwargs)

                        setattr(server, name, _wrapper)
                        print(f"[slide_agent] session_init_handler patched via '{name}'")
                        hooked = True
                        break
                    except Exception:
                        continue

        # Also expose for external/monkey-patch usage
        setattr(server, "_configure_api_from_session", _configure_api_from_session)
        if not hooked:
            print("[slide_agent] WARNING: No session-init hook available; Created-session logs will not be printed.")
            # Last-resort generic patch: wrap likely message handlers to catch user.create_session
            try:
                def _maybe_wrap_method(obj, name: str) -> bool:
                    try:
                        orig = getattr(obj, name)
                    except Exception:
                        return False
                    if not callable(orig):
                        return False
                    # Avoid double-wrapping
                    if getattr(orig, "__slide_agent_wrapped__", False):
                        return False

                    def _wrapper(*args, **kwargs):  # type: ignore[no-redef]
                        try:
                            # Search args/kwargs for a dict payload with event=user.create_session
                            payload = None
                            for v in list(args) + list(kwargs.values()):
                                if isinstance(v, dict) and v.get("event") == "user.create_session":
                                    payload = v
                                    break
                                if isinstance(v, dict) and isinstance(v.get("content"), dict):
                                    # Fallback if only content dict is passed
                                    payload = {"event": "user.create_session", "content": v.get("content")}
                                    break
                            if payload and isinstance(payload.get("content"), dict):
                                _configure_api_from_session(payload.get("content"))
                        except Exception:
                            pass
                        return orig(*args, **kwargs)

                    try:
                        setattr(_wrapper, "__slide_agent_wrapped__", True)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    try:
                        setattr(obj, name, _wrapper)
                        print(f"[slide_agent] generic patched handler '{name}'")
                        return True
                    except Exception:
                        return False

                patched_any = False
                for attr in dir(server):
                    # Patch handlers that plausibly process incoming WS messages
                    if any(key in attr for key in ("message", "create", "session", "user")):
                        try:
                            if _maybe_wrap_method(server, attr):
                                patched_any = True
                        except Exception:
                            continue
                if not patched_any:
                    print("[slide_agent] generic patch could not find a handler to wrap")
            except Exception as _e:
                try:
                    print(f"[slide_agent] generic patch failed: {_e}")
                except Exception:
                    pass
    except Exception as e:
        # Fail open: proceed without hook; tools will read API_* from env if already set
        try:
            print(f"[slide_agent] session-init hook registration failed: {e}")
        except Exception:
            pass
    await server.start_server()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run slide_agent_ws Plan & Solve Data→PPT pipeline as a WebSocket service."
    )
    parser.add_argument("--host", default="127.0.0.1", help="WebSocket server host")
    parser.add_argument("--port", type=int, default=8080, help="WebSocket server port")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host, args.port))
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
