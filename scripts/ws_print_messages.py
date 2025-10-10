"""Simple WebSocket client that prints every message from the MyAgent server."""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
from typing import Any

import websockets


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


async def run_client(url: str, question: str | None, keep_alive: bool) -> None:
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
            elif (
                not keep_alive
                and session_id
                and event_type in {"agent.final_answer", "agent.session_end"}
            ):
                print("🛑 Final event received. Closing connection.")
                break


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
    args = parser.parse_args()

    url = f"ws://{args.host}:{args.port}"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, loop.stop)
        except NotImplementedError:
            # add_signal_handler may not be available on Windows event loop
            pass

    try:
        loop.run_until_complete(
            run_client(url=url, question=args.question, keep_alive=args.keep_alive)
        )
    finally:
        loop.close()


if __name__ == "__main__":
    main()
