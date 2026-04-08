"""Local Agent Protocol server for DeepAgents async subagents."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from coding_agent.config import settings
from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
from coding_agent.middleware.model_fallback import ModelFallbackMiddleware, create_model

logger = logging.getLogger(__name__)

_ARGS: argparse.Namespace | None = None
_AGENT = None
_CONN = sqlite3.connect(":memory:", check_same_thread=False)
_CONN.row_factory = sqlite3.Row


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local async subagent server")
    parser.add_argument("--agent-type", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--root-dir", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--system-prompt", required=True)
    return parser.parse_args()


def _init_db() -> None:
    _CONN.executescript("""
        CREATE TABLE IF NOT EXISTS threads (
            thread_id  TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            messages   TEXT NOT NULL DEFAULT '[]',
            values_    TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS runs (
            run_id       TEXT PRIMARY KEY,
            thread_id    TEXT NOT NULL REFERENCES threads(thread_id),
            assistant_id TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'pending',
            created_at   TEXT NOT NULL,
            error        TEXT
        );
        CREATE TABLE IF NOT EXISTS run_events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL REFERENCES runs(run_id),
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    _CONN.commit()


def _get_thread(thread_id: str) -> dict[str, Any] | None:
    row = _CONN.execute(
        "SELECT thread_id, created_at, messages, values_ FROM threads WHERE thread_id = ?",
        (thread_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "thread_id": row["thread_id"],
        "created_at": row["created_at"],
        "messages": json.loads(row["messages"]),
        "values": json.loads(row["values_"]),
    }


def _get_run(run_id: str) -> dict[str, Any] | None:
    row = _CONN.execute(
        "SELECT run_id, thread_id, assistant_id, status, created_at, error FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _bootstrap_agent():
    if _ARGS is None:
        raise RuntimeError("Server arguments were not initialized.")

    from deepagents import create_deep_agent
    from deepagents.backends import LocalShellBackend

    model_spec = next(
        (spec for spec in settings.get_all_models() if spec.to_model_string() == _ARGS.model),
        settings.get_all_models()[0],
    )
    backend = LocalShellBackend(
        root_dir=str(Path(_ARGS.root_dir).resolve()),
        inherit_env=True,
        virtual_mode=False,
    )

    fallback = ModelFallbackMiddleware()
    ltm = LongTermMemoryMiddleware()

    return create_deep_agent(
        model=create_model(model_spec),
        system_prompt=_ARGS.system_prompt,
        middleware=[fallback, ltm],
        tools=ltm.get_tools(),
        backend=backend,
        memory=[],
        skills=[],
        debug=False,
        name=f"async-subagent-{_ARGS.agent_type}",
    )


def _append_run_event(run_id: str, event_type: str, payload: dict[str, Any]) -> None:
    _CONN.execute(
        "INSERT INTO run_events (run_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
        (run_id, event_type, json.dumps(payload), datetime.now(UTC).isoformat()),
    )
    _CONN.commit()


async def _execute_run(run_id: str, thread_id: str, user_message: str) -> None:
    _CONN.execute("UPDATE runs SET status = 'running' WHERE run_id = ?", (run_id,))
    _CONN.commit()
    _append_run_event(run_id, "status", {"status": "running"})
    try:
        output_chunks: list[str] = []
        async for event in _AGENT.astream_events(
            {"messages": [HumanMessage(user_message)]},
            version="v2",
        ):
            if event.get("event") != "on_chat_model_stream":
                continue
            chunk = (event.get("data") or {}).get("chunk")
            content = getattr(chunk, "content", "")
            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                parts: list[str] = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(str(block.get("text", "")))
                text = "".join(parts)
            if text:
                output_chunks.append(text)
                _append_run_event(run_id, "token", {"text": text})

        output = "".join(output_chunks).strip()
        if not output:
            result = await _AGENT.ainvoke({"messages": [HumanMessage(user_message)]})
            last = result["messages"][-1]
            output = last.content if isinstance(last.content, str) else json.dumps(last.content)

        assistant_msg = {"role": "assistant", "content": output}
        row = _CONN.execute(
            "SELECT messages FROM threads WHERE thread_id = ?",
            (thread_id,),
        ).fetchone()
        msgs = json.loads(row[0]) if row else []
        msgs.append(assistant_msg)
        serialized = json.dumps(msgs)
        _CONN.execute(
            "UPDATE threads SET messages = ?, values_ = ? WHERE thread_id = ?",
            (serialized, json.dumps({"messages": msgs}), thread_id),
        )
        _CONN.execute("UPDATE runs SET status = 'success' WHERE run_id = ?", (run_id,))
        _CONN.commit()
        _append_run_event(run_id, "final", {"text": output, "status": "success"})
    except Exception as exc:  # noqa: BLE001
        _CONN.execute(
            "UPDATE runs SET status = 'error', error = ? WHERE run_id = ?",
            (str(exc), run_id),
        )
        _CONN.commit()
        _append_run_event(run_id, "error", {"error": str(exc), "status": "error"})


@asynccontextmanager
async def _lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _AGENT
    _init_db()
    _AGENT = _bootstrap_agent()
    yield


app = FastAPI(lifespan=_lifespan)


@app.get("/ok")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/threads")
async def create_thread() -> dict[str, Any]:
    thread_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    _CONN.execute(
        "INSERT INTO threads (thread_id, created_at) VALUES (?, ?)",
        (thread_id, now),
    )
    _CONN.commit()
    return {"thread_id": thread_id, "created_at": now, "messages": [], "values": {}}


@app.post("/threads/{thread_id}/runs")
async def create_run(thread_id: str, request: Request) -> dict[str, Any]:
    thread = _get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    body = await request.json()
    multitask_strategy = body.get("multitask_strategy")
    if multitask_strategy == "interrupt":
        _CONN.execute(
            "UPDATE runs SET status = 'cancelled' WHERE thread_id = ? AND status = 'running'",
            (thread_id,),
        )
        _CONN.execute(
            "UPDATE threads SET values_ = '{}' WHERE thread_id = ?",
            (thread_id,),
        )
        _CONN.commit()

    messages = (body.get("input") or {}).get("messages") or []
    user_message = next((m["content"] for m in messages if m.get("role") == "user"), "")

    if user_message:
        existing = json.loads(
            _CONN.execute(
                "SELECT messages FROM threads WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()[0]
        )
        existing.append({"role": "user", "content": user_message})
        _CONN.execute(
            "UPDATE threads SET messages = ? WHERE thread_id = ?",
            (json.dumps(existing), thread_id),
        )
        _CONN.commit()

    run_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    assistant_id = body.get("assistant_id") or (_ARGS.agent_type if _ARGS else "async-subagent")
    _CONN.execute(
        "INSERT INTO runs (run_id, thread_id, assistant_id, created_at) VALUES (?, ?, ?, ?)",
        (run_id, thread_id, assistant_id, now),
    )
    _CONN.commit()

    asyncio.ensure_future(_execute_run(run_id, thread_id, user_message))
    return {
        "run_id": run_id,
        "thread_id": thread_id,
        "assistant_id": assistant_id,
        "status": "pending",
        "created_at": now,
        "error": None,
    }


@app.get("/threads/{thread_id}/runs/{run_id}")
async def get_run(thread_id: str, run_id: str) -> dict[str, Any]:
    run = _get_run(run_id)
    if run is None or run["thread_id"] != thread_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str) -> dict[str, Any]:
    thread = _get_thread(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@app.post("/threads/{thread_id}/runs/{run_id}/cancel")
async def cancel_run(thread_id: str, run_id: str) -> dict[str, Any]:
    run = _get_run(run_id)
    if run is None or run["thread_id"] != thread_id:
        raise HTTPException(status_code=404, detail="Run not found")
    _CONN.execute("UPDATE runs SET status = 'cancelled' WHERE run_id = ?", (run_id,))
    _CONN.commit()
    _append_run_event(run_id, "status", {"status": "cancelled"})
    return {**run, "status": "cancelled"}


@app.get("/threads/{thread_id}/runs/{run_id}/stream")
async def stream_run_events(thread_id: str, run_id: str, after: int = 0):
    run = _get_run(run_id)
    if run is None or run["thread_id"] != thread_id:
        raise HTTPException(status_code=404, detail="Run not found")

    async def _event_generator():
        last_seq = int(after)
        terminal = {"success", "error", "cancelled"}
        while True:
            rows = _CONN.execute(
                """
                SELECT seq, event_type, payload
                FROM run_events
                WHERE run_id = ? AND seq > ?
                ORDER BY seq ASC
                """,
                (run_id, last_seq),
            ).fetchall()

            for row in rows:
                last_seq = int(row["seq"])
                payload = row["payload"]
                yield f"id: {last_seq}\n"
                yield f"event: {row['event_type']}\n"
                yield f"data: {payload}\n\n"

            latest = _get_run(run_id)
            if latest is None:
                break
            if str(latest.get("status", "")).lower() in terminal and not rows:
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    global _ARGS
    _ARGS = _parse_args()
    import uvicorn

    uvicorn.run(
        app,
        host=_ARGS.host,
        port=_ARGS.port,
        reload=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
