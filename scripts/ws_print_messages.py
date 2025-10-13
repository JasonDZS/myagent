"""Simple WebSocket client that prints every message from the MyAgent server.

Enhancements:
- Add `--cancel-after` to auto-send `user.cancel` after N seconds
  (after session creation, or after sending the question if provided).
- Exit on `agent.interrupted` when `--keep-alive` is not set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from typing import Any, Optional

import websockets


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


async def run_client(
    url: str,
    question: Optional[str],
    keep_alive: bool,
    cancel_after: Optional[float],
    auto_confirm_plan: bool,
    confirm_plan_tasks: Optional[Any],
    confirm_timeout: Optional[float],
    interactive_confirm: bool,
) -> None:
    print(f"Connecting to {url} ...")
    async with websockets.connect(url) as websocket:
        print("✅ Connected. Sending user.create_session ...")
        await websocket.send(
            _json_dumps(
                {
                    "event": "user.create_session",
                }
            )
        )

        session_id: str | None = None
        cancel_task: asyncio.Task | None = None

        try:
            while True:
                try:
                    raw = await websocket.recv()
                except websockets.ConnectionClosedOK:
                    print("🔌 Connection closed by server.")
                    break
                except websockets.ConnectionClosedError as exc:
                    print(f"⚠️  Connection error: {exc}")
                    break

                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"<-- {raw}")
                    continue

                pretty = json.dumps(message, ensure_ascii=False, indent=2, sort_keys=True)
                print("<--")
                print(pretty)

                event_type = message.get("event")
                if not session_id and event_type == "agent.session_created":
                    session_id = message.get("session_id")
                    print(f"📌 Session established: {session_id}")

                    # Optionally send question immediately
                    if question:
                        await websocket.send(
                            _json_dumps(
                                {
                                    "event": "user.message",
                                    "session_id": session_id,
                                    "content": question,
                                }
                            )
                        )
                        print(f"--> Sent question: {question}")

                    # Optionally schedule cancellation
                    if cancel_after is not None:
                        async def _schedule_cancel(delay: float, sid: str):
                            try:
                                await asyncio.sleep(delay)
                                await websocket.send(
                                    _json_dumps(
                                        {
                                            "event": "user.cancel",
                                            "session_id": sid,
                                        }
                                    )
                                )
                                print(f"--> Sent user.cancel after {delay}s")
                            except Exception as exc:
                                print(f"⚠️  Failed to send cancel: {exc}")

                        cancel_task = asyncio.create_task(_schedule_cancel(cancel_after, session_id))

                elif (
                    not keep_alive
                    and session_id
                    and event_type in {"agent.final_answer", "agent.session_end", "agent.interrupted"}
                ):
                    print("🛑 Terminal event received. Closing connection.")
                    break

                # Handle confirmation prompts
                if event_type == "agent.user_confirm" and session_id:
                    step_id = message.get("step_id")
                    metadata = message.get("metadata") or {}
                    scope = metadata.get("scope")

                    # Auto-confirm plan if requested
                    if auto_confirm_plan and scope == "plan" and step_id:
                        payload: dict[str, Any] = {
                            "event": "user.response",
                            "session_id": session_id,
                            "step_id": step_id,
                            "content": {"confirmed": True},
                        }
                        if confirm_plan_tasks is not None:
                            payload["content"]["tasks"] = confirm_plan_tasks
                        await websocket.send(_json_dumps(payload))
                        print(
                            f"--> Sent user.response to confirm plan (override_tasks={'yes' if confirm_plan_tasks is not None else 'no'})"
                        )
                    elif interactive_confirm:
                        # Interactive confirmation in terminal
                        await _interactive_confirm_and_reply(
                            websocket=websocket,
                            session_id=session_id,
                            message=message,
                            timeout=confirm_timeout,
                        )
        finally:
            if cancel_task and not cancel_task.done():
                cancel_task.cancel()


async def _interactive_confirm_and_reply(
    *,
    websocket,
    session_id: str,
    message: dict[str, Any],
    timeout: Optional[float],
) -> None:
    """Prompt user in terminal to confirm or deny an agent.user_confirm.

    For plan confirmation, optionally allow user to specify a JSON file path to override tasks.
    """
    step_id = message.get("step_id")
    metadata = message.get("metadata") or {}
    content = message.get("content")
    scope = metadata.get("scope")
    if not step_id:
        print("⚠️  Missing step_id in agent.user_confirm; cannot reply interactively.")
        return

    # Pretty print prompt context
    print("\n=== Confirmation requested ===")
    print(f"scope      : {scope or 'tool'}")
    if scope == "plan":
        print(f"summary    : {metadata.get('plan_summary')}")
        print("tasks      : (see below)")
        try:
            preview = json.dumps(metadata.get("tasks"), ensure_ascii=False, indent=2)
            print(preview)
        except Exception:
            print("<unprintable tasks>")
    else:
        # Tool confirmation details
        print(f"tool_name  : {metadata.get('tool_name')}")
        print(f"description: {metadata.get('tool_description')}")
        print(f"args       : {json.dumps(metadata.get('tool_args'), ensure_ascii=False)}")
    print(f"message    : {content}")

    # Ask yes/no
    confirmed = await _ask_yes_no(
        "Confirm? [y/N]: ", default=False, timeout=timeout
    )

    reply: dict[str, Any] = {
        "event": "user.response",
        "session_id": session_id,
        "step_id": step_id,
        "content": {"confirmed": bool(confirmed)},
    }

    # If plan and confirmed, optionally allow override tasks by path
    if confirmed and scope == "plan":
        override_path = await _ask_text(
            "Override tasks with JSON file path (blank to keep): ", timeout=timeout
        )
        if override_path:
            try:
                with open(override_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    reply["content"]["tasks"] = data
                else:
                    print(
                        "⚠️  Provided JSON does not contain a list; ignoring override."
                    )
            except Exception as exc:
                print(f"⚠️  Failed to load tasks from '{override_path}': {exc}")

    await websocket.send(_json_dumps(reply))
    print(
        f"--> Sent user.response (confirmed={'yes' if confirmed else 'no'}; scope={scope or 'tool'})"
    )


async def _ask_yes_no(prompt: str, *, default: bool = False, timeout: Optional[float] = None) -> bool:
    """Ask a yes/no question in a non-blocking way with optional timeout."""
    line = await _read_input(prompt, timeout=timeout)
    if line is None:
        return default
    val = line.strip().lower()
    if val in ("y", "yes"):
        return True
    if val in ("n", "no"):
        return False
    return default


async def _ask_text(prompt: str, *, timeout: Optional[float] = None) -> Optional[str]:
    """Ask for a single line of text with optional timeout."""
    line = await _read_input(prompt, timeout=timeout)
    if line is None:
        return None
    line = line.strip()
    return line or None


async def _read_input(prompt: str, *, timeout: Optional[float]) -> Optional[str]:
    """Read input via stdin without blocking the event loop, with optional timeout."""
    # If stdin is not a TTY (e.g., piped), don't wait interactively
    if not sys.stdin or not sys.stdin.isatty():
        print("⚠️  Stdin is not interactive; skipping prompt.")
        return None
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(None, input, prompt)
    if timeout and timeout > 0:
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            print("⚠️  Confirmation prompt timed out.")
            return None
    return await fut


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Connect to a MyAgent WebSocket server and print all messages."
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="WebSocket server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="WebSocket server port (default: 8080)"
    )
    parser.add_argument(
        "--question",
        default=None,
        help="Optional question to send automatically after session creation.",
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Keep connection open after receiving final answer.",
    )
    parser.add_argument(
        "--auto-confirm-plan",
        action="store_true",
        help="Automatically confirm the plan when agent.user_confirm(scope=plan) is received.",
    )
    parser.add_argument(
        "--confirm-plan-tasks-file",
        default=None,
        help="Optional JSON file containing a task list to override when auto-confirming the plan.",
    )
    parser.add_argument(
        "--cancel-after",
        type=float,
        default=None,
        help=(
            "Automatically send user.cancel after N seconds. "
            "When --question is set, the timer starts after session creation (and question sent). "
            "When no question is set, the timer starts after session creation."
        ),
    )
    parser.add_argument(
        "--confirm-timeout",
        type=float,
        default=None,
        help="Optional timeout (seconds) for interactive confirmation prompts.",
    )
    parser.add_argument(
        "--no-interactive-confirm",
        action="store_true",
        help="Disable interactive confirmation prompts for agent.user_confirm events.",
    )
    args = parser.parse_args()

    url = f"ws://{args.host}:{args.port}"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Prepare optional plan task overrides
    confirm_plan_tasks = None
    if args.confirm_plan_tasks_file:
        try:
            with open(args.confirm_plan_tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                confirm_plan_tasks = data
            else:
                print("⚠️  --confirm-plan-tasks-file must contain a JSON list; ignoring.")
        except Exception as exc:
            print(f"⚠️  Failed to load --confirm-plan-tasks-file: {exc}")

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, loop.stop)
        except NotImplementedError:
            # add_signal_handler may not be available on Windows event loop
            pass

    # Decide whether to enable interactive confirmations
    interactive_confirm = not args.no_interactive_confirm

    try:
        loop.run_until_complete(
            run_client(
                url=url,
                question=args.question,
                keep_alive=args.keep_alive,
                cancel_after=args.cancel_after,
                auto_confirm_plan=args.auto_confirm_plan,
                confirm_plan_tasks=confirm_plan_tasks,
                confirm_timeout=args.confirm_timeout,
                interactive_confirm=interactive_confirm,
            )
        )
    finally:
        loop.close()


if __name__ == "__main__":
    main()
