from __future__ import annotations

"""
End-to-end self-check for Template Agent WS + Backend.

This script:
- Verifies backend health
- Ensures a template and a knowledge base exist (creates if missing)
- Connects to the WS server, opens a session, sends a structured user.message
- Auto-confirms plan/tools when required, and prints aggregate/final results

Usage examples:
  python template_agent/scripts/ws_e2e_check.py \
    --backend http://127.0.0.1:8787 \
    --ws ws://127.0.0.1:8081 \
    --template-name 自检模板 \
    --kb-name 自检知识库

Requirements:
- websockets Python package (same as server dependency)
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib import request, error as urlerror


# -----------------------------
# HTTP helpers (stdlib)
# -----------------------------


def http_get_json(url: str) -> Any:
    req = request.Request(url, headers={"Accept": "application/json"})
    with request.urlopen(req, timeout=10) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        data = resp.read().decode(charset)
        return json.loads(data)


def http_post_json(url: str, payload: dict) -> Any:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=10) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset)
        return json.loads(body)


# -----------------------------
# Backend provisioning
# -----------------------------


def ensure_backend_ready(backend: str) -> None:
    url = backend.rstrip("/") + "/api/health"
    try:
        data = http_get_json(url)
        ok = bool(data.get("ok")) if isinstance(data, dict) else False
        if not ok:
            raise RuntimeError(f"Backend health not OK: {data!r}")
        print(f"[✓] Backend health: ok ({data.get('service')})")
    except Exception as exc:
        raise SystemExit(f"[x] Backend health check failed: {exc}")


def get_or_create_template(backend: str, *, name: str | None, content: str | None = None) -> dict:
    base = backend.rstrip("/")
    tpls = http_get_json(base + "/api/templates")
    if not isinstance(tpls, list):
        raise RuntimeError("Unexpected /api/templates response")
    if name:
        for t in tpls:
            if str(t.get("name")) == name:
                print(f"[=] Using existing template: {name}")
                return t
    # Create
    payload = {"name": name or "自检模板"}
    if content:
        payload["content"] = content
    created = http_post_json(base + "/api/templates", payload)
    print(f"[+] Created template: {created.get('name')} ({created.get('id')})")
    return created


def get_or_create_database(backend: str, *, name: str | None, seed: dict | None = None) -> dict:
    base = backend.rstrip("/")
    dbs = http_get_json(base + "/api/databases")
    if not isinstance(dbs, list):
        raise RuntimeError("Unexpected /api/databases response")
    if name:
        for d in dbs:
            if str(d.get("name")) == name:
                print(f"[=] Using existing knowledge base: {name}")
                # Fetch full
                full = http_get_json(base + f"/api/databases/{d.get('id')}")
                return full
    # Create with seed file
    files = []
    if seed:
        files = [{"name": "seed.json", "data": seed}]
    created = http_post_json(base + "/api/databases", {"name": name or "自检知识库", "files": files})
    print(f"[+] Created knowledge base: {created.get('name')} ({created.get('id')}) with {len(created.get('files') or [])} files")
    return created


# -----------------------------
# WS client
# -----------------------------


async def run_ws_flow(ws_url: str, *, backend: str, template_name: str, kb_name: str, timeout: int = 120) -> None:
    try:
        import websockets  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit("websockets package is required to run this script") from exc

    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
        # 1) Create session
        await ws.send(json.dumps({"event": "user.create_session"}))
        session_id = None

        async def _send(ev: dict) -> None:
            if session_id:
                ev.setdefault("session_id", session_id)
            await ws.send(json.dumps(ev, ensure_ascii=False))

        # Message loop
        report_preview = None
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            msg = json.loads(raw)
            event = msg.get("event")
            content = msg.get("content")
            metadata = msg.get("metadata")
            step_id = msg.get("step_id")

            if event == "agent.session_created":
                session_id = msg.get("session_id")
                print(f"[✓] Session created: {session_id}")
                # 2) Send structured user.message
                await _send(
                    {
                        "event": "user.message",
                        "content": {
                            "question": "请基于指定模版与知识库生成报告",
                            "template_name": template_name,
                            "knowledge_base_name": kb_name,
                            "api_base_url": backend,
                        },
                    }
                )

            elif event == "plan.start":
                print("[·] Planning started")

            elif event == "plan.completed":
                tasks = (content or {}).get("tasks") if isinstance(content, dict) else None
                print(f"[✓] Plan completed: {len(tasks or [])} tasks")

            elif event == "agent.user_confirm":
                # Auto-confirm plan or tool actions
                scope = (metadata or {}).get("scope") if isinstance(metadata, dict) else None
                print(f"[?] User confirm requested (scope={scope or 'unknown'}) → auto-confirm")
                await _send({"event": "user.response", "step_id": step_id, "content": {"confirmed": True}})

            elif event == "solver.start":
                print("[·] Solver started for a section")

            elif event == "solver.completed":
                summary = (content or {}).get("summary") if isinstance(content, dict) else None
                if summary:
                    print(f"[✓] Solver completed: {summary}")
                else:
                    print("[✓] Solver completed")

            elif event == "aggregate.completed":
                out = (content or {}).get("output") if isinstance(content, dict) else None
                report = (out or {}).get("report") if isinstance(out, dict) else None
                rep_content = (report or {}).get("content") if isinstance(report, dict) else None
                if rep_content:
                    report_preview = rep_content[:400]
                print("[✓] Aggregate completed")

            elif event == "pipeline.completed":
                print("[✓] Pipeline completed")

            elif event == "agent.final_answer":
                print("[✓] Final answer received")
                if report_preview:
                    print("\n--- Report Preview (first 400 chars) ---\n")
                    print(report_preview)
                return

            elif event == "agent.error" or event == "system.error":
                raise SystemExit(f"[x] Error event: {content}")


def build_default_template() -> str:
    return (
        "# 自检模板\n\n"
        "## 概述\n"
        "{{summary}}\n\n"
        "## 结论\n"
        "{{conclusion}}\n"
    )


def build_default_seed() -> dict:
    return {
        "summary": "这是一个自检流程自动创建的知识库样例，包含基础占位符数据。",
        "conclusion": "后端与WS联通正常，流程运行成功。",
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Template Agent WS E2E self-check")
    parser.add_argument("--backend", default="http://127.0.0.1:8787", help="Backend base URL")
    parser.add_argument("--ws", default="ws://127.0.0.1:8081", help="WebSocket URL (ws://host:port)")
    parser.add_argument("--template-name", dest="template_name", default="自检模板")
    parser.add_argument("--kb-name", dest="kb_name", default="自检知识库")
    args = parser.parse_args()

    # 1) Backend health
    ensure_backend_ready(args.backend)

    # 2) Ensure template and KB
    tpl = get_or_create_template(args.backend, name=args.template_name, content=build_default_template())
    kb = get_or_create_database(args.backend, name=args.kb_name, seed=build_default_seed())
    print(f"[i] Using template='{tpl.get('name')}', knowledge_base='{kb.get('name')}'")

    # 3) WS flow
    await run_ws_flow(args.ws, backend=args.backend, template_name=str(tpl.get("name")), kb_name=str(kb.get("name")))
    print("\n[✓] E2E self-check completed successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted by user")
    except urlerror.URLError as e:
        sys.exit(f"[x] Network error: {e}")
    except Exception as e:
        sys.exit(f"[x] Failed: {e}")

