"""SQLite-backed durable store for project state."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any

from coding_agent.state.models import LoopRunRecord, MemoryRecord, SubAgentRecord, utc_now_iso


MEMORY_LAYERS = {
    "user/profile",
    "project/context",
    "domain/knowledge",
}


class DurableStateStore:
    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
            CREATE TABLE IF NOT EXISTS memory_records (
                record_id TEXT PRIMARY KEY,
                layer TEXT NOT NULL,
                content TEXT NOT NULL,
                scope_key TEXT NOT NULL,
                source TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                status TEXT NOT NULL,
                correction_of TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subagent_records (
                agent_id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                task_summary TEXT NOT NULL,
                parent_id TEXT NOT NULL,
                state TEXT NOT NULL,
                task_id TEXT,
                run_id TEXT,
                endpoint TEXT,
                pid INTEGER,
                model TEXT,
                error TEXT,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS subagent_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                state TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS loop_runs (
                run_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                status TEXT NOT NULL,
                current_step TEXT NOT NULL,
                retries INTEGER NOT NULL,
                failure_reason TEXT,
                next_action TEXT,
                model TEXT,
                fallback_model TEXT,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
            )
            self._conn.commit()

    def store_memory(
        self,
        *,
        layer: str,
        content: str,
        scope_key: str = "global",
        source: str = "agent",
        tags: list[str] | None = None,
        correction_of: str | None = None,
    ) -> str:
        if layer not in MEMORY_LAYERS:
            raise ValueError(f"Unsupported memory layer: {layer}")
        record = MemoryRecord(
            record_id=f"mem_{uuid.uuid4().hex[:12]}",
            layer=layer,
            content=content,
            scope_key=scope_key,
            source=source,
            tags=tags or [],
            correction_of=correction_of,
        )
        with self._lock:
            if correction_of:
                self._conn.execute(
                    "UPDATE memory_records SET status = 'superseded', updated_at = ? WHERE record_id = ?",
                    (record.updated_at, correction_of),
                )
            self._conn.execute(
                """
            INSERT INTO memory_records
            (record_id, layer, content, scope_key, source, tags_json, status, correction_of, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.record_id,
                    record.layer,
                    record.content,
                    record.scope_key,
                    record.source,
                    json.dumps(record.tags),
                    record.status,
                    record.correction_of,
                    record.created_at,
                    record.updated_at,
                ),
            )
            self._conn.commit()
        return record.record_id

    def search_memory(
        self,
        query: str,
        *,
        layer: str | None = None,
        scope_key: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        clauses = ["status = 'active'"]
        params: list[Any] = []
        if layer:
            clauses.append("layer = ?")
            params.append(layer)
        if scope_key:
            clauses.append("(scope_key = ? OR scope_key = 'global')")
            params.append(scope_key)
        sql = (
            "SELECT * FROM memory_records WHERE "
            + " AND ".join(clauses)
            + " ORDER BY updated_at DESC"
        )
        with self._lock:
            rows = [dict(r) for r in self._conn.execute(sql, params).fetchall()]
        query_lower = query.lower().strip()
        if query_lower:
            ranked: list[tuple[int, dict[str, Any]]] = []
            for row in rows:
                haystack = f"{row['content']} {' '.join(json.loads(row['tags_json']))}".lower()
                score = haystack.count(query_lower)
                if score > 0 or not query_lower:
                    ranked.append((score, row))
            rows = [row for _score, row in sorted(ranked, key=lambda item: (-item[0], item[1]["updated_at"]))] or rows
        return rows[:limit]

    def get_memory_record(self, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM memory_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_memory_records(
        self,
        *,
        layer: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if layer:
            clauses.append("layer = ?")
            params.append(layer)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            "SELECT * FROM memory_records "
            f"{where} "
            "ORDER BY updated_at DESC LIMIT ?"
        )
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def create_subagent(
        self,
        *,
        role: str,
        task_summary: str,
        parent_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        record = SubAgentRecord(
            agent_id=f"sa_{uuid.uuid4().hex[:12]}",
            role=role,
            task_summary=task_summary,
            parent_id=parent_id,
            state="created",
            metadata=metadata or {},
        )
        with self._lock:
            self._conn.execute(
                """
            INSERT INTO subagent_records
            (agent_id, role, task_summary, parent_id, state, task_id, run_id, endpoint, pid, model, error, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.agent_id,
                    record.role,
                    record.task_summary,
                    record.parent_id,
                    record.state,
                    record.task_id,
                    record.run_id,
                    record.endpoint,
                    record.pid,
                    record.model,
                    record.error,
                    json.dumps(record.metadata),
                    record.created_at,
                    record.updated_at,
                ),
            )
            self.record_subagent_event(record.agent_id, "created", task_summary)
            self._conn.commit()
        return record.agent_id

    def update_subagent(
        self,
        agent_id: str,
        *,
        state: str | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
        endpoint: str | None = None,
        pid: int | None = None,
        model: str | None = None,
        error: str | None = None,
        task_summary: str | None = None,
        metadata: dict[str, Any] | None = None,
        event_detail: str | None = None,
    ) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT metadata_json, state FROM subagent_records WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
            if row is None:
                return
            merged_metadata = json.loads(row["metadata_json"] or "{}")
            if metadata:
                merged_metadata.update(metadata)
            next_state = state or row["state"]
            self._conn.execute(
                """
            UPDATE subagent_records
            SET state = ?, task_id = COALESCE(?, task_id), run_id = COALESCE(?, run_id),
                endpoint = COALESCE(?, endpoint), pid = COALESCE(?, pid),
                model = COALESCE(?, model), error = COALESCE(?, error),
                task_summary = COALESCE(?, task_summary), metadata_json = ?, updated_at = ?
            WHERE agent_id = ?
                """,
                (
                    next_state,
                    task_id,
                    run_id,
                    endpoint,
                    pid,
                    model,
                    error,
                    task_summary,
                    json.dumps(merged_metadata),
                    utc_now_iso(),
                    agent_id,
                ),
            )
            if state:
                self.record_subagent_event(agent_id, state, event_detail or error or "")
            self._conn.commit()

    def record_subagent_event(self, agent_id: str, state: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO subagent_events (agent_id, state, detail, created_at) VALUES (?, ?, ?, ?)",
            (agent_id, state, detail, utc_now_iso()),
        )

    def find_subagent_by_task_id(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM subagent_records WHERE task_id = ? ORDER BY updated_at DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_subagents(self, parent_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if parent_id:
                rows = self._conn.execute(
                    "SELECT * FROM subagent_records WHERE parent_id = ? ORDER BY created_at DESC",
                    (parent_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM subagent_records ORDER BY created_at DESC"
                ).fetchall()
        return [dict(row) for row in rows]

    def list_subagent_events(self, agent_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM subagent_events WHERE agent_id = ? ORDER BY event_id ASC",
                (agent_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_loop_run(
        self,
        *,
        run_id: str,
        thread_id: str,
        status: str,
        current_step: str,
        retries: int = 0,
        failure_reason: str | None = None,
        next_action: str | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT run_id, metadata_json, created_at FROM loop_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            created_at = row["created_at"] if row else utc_now_iso()
            merged_metadata = json.loads(row["metadata_json"] or "{}") if row else {}
            if metadata:
                merged_metadata.update(metadata)
            self._conn.execute(
                """
            INSERT INTO loop_runs
            (run_id, thread_id, status, current_step, retries, failure_reason, next_action, model, fallback_model, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                thread_id=excluded.thread_id,
                status=excluded.status,
                current_step=excluded.current_step,
                retries=excluded.retries,
                failure_reason=excluded.failure_reason,
                next_action=excluded.next_action,
                model=excluded.model,
                fallback_model=excluded.fallback_model,
                metadata_json=excluded.metadata_json,
                updated_at=excluded.updated_at
                """,
                (
                    run_id,
                    thread_id,
                    status,
                    current_step,
                    retries,
                    failure_reason,
                    next_action,
                    model,
                    fallback_model,
                    json.dumps(merged_metadata),
                    created_at,
                    utc_now_iso(),
                ),
            )
            self._conn.commit()

    def get_loop_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM loop_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return dict(row) if row else None
