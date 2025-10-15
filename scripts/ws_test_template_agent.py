from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import websockets


def _dumps(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _build_default_question(template_path: str) -> str:
    return (
        f"请使用模板：{template_path} 生成一份报告。\n"
        "如有需要，可从 template_agent/workdir/datasets/ 或 workspace/ 中读取数据文件。"
    )


async def run(url: str, question: str, auto_confirm: bool) -> None:
    print(f"Connecting to {url} ...")
    async with websockets.connect(url) as ws:
        # 1) create session
        await ws.send(_dumps({"event": "user.create_session"}))
        session_id: str | None = None

        while True:
            try:
                raw = await ws.recv()
            except websockets.ConnectionClosed:
                print("🔌 WebSocket closed by server")
                break

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                print(f"<-- {raw}")
                continue

            print("<--", json.dumps(msg, ensure_ascii=False))
            event = msg.get("event")

            if not session_id and event == "agent.session_created":
                session_id = msg.get("session_id")
                # 2) send question
                await ws.send(
                    _dumps({
                        "event": "user.message",
                        "session_id": session_id,
                        "content": question,
                    })
                )
                print("--> Sent question for planning & solving")

            elif event == "agent.user_confirm" and auto_confirm:
                step_id = msg.get("step_id")
                meta = msg.get("metadata") or {}
                scope = meta.get("scope")
                if scope == "plan" and session_id and step_id:
                    await ws.send(
                        _dumps({
                            "event": "user.response",
                            "session_id": session_id,
                            "step_id": step_id,
                            "content": {"confirmed": True},
                        })
                    )
                    print("--> Auto-confirmed plan")

            elif event in {"agent.final_answer", "agent.session_end", "agent.interrupted"}:
                print("🛑 Terminal event received. Exiting.")
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Test client for template_agent WebSocket server")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8087, help="Server port (default: 8087)")
    parser.add_argument(
        "--template",
        default="template/常规团队例会模板.md",
        help="Template path relative to template_agent/workdir (default: template/常规团队例会模板.md)",
    )
    parser.add_argument(
        "--question",
        default=None,
        help="Optional custom question to send. If omitted, a default question is constructed from --template.",
    )
    parser.add_argument("--no-auto-confirm", action="store_true", help="Disable auto-confirming the plan")
    args = parser.parse_args()

    url = f"ws://{args.host}:{args.port}"
    question = args.question or _build_default_question(args.template)
    auto_confirm = not args.no_auto_confirm

    asyncio.run(run(url, question, auto_confirm))


if __name__ == "__main__":
    main()

