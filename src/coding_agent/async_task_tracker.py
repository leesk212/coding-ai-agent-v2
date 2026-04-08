"""Helpers for inspecting DeepAgents async subagent task state."""

from __future__ import annotations

from typing import Any


class AsyncTaskTracker:
    """Read tracked async tasks from a compiled DeepAgents supervisor."""

    def __init__(self, agent: Any) -> None:
        self.agent = agent

    def get_tasks(self, thread_id: str) -> list[dict[str, Any]]:
        if not thread_id:
            return []
        try:
            snapshot = self.agent.get_state({"configurable": {"thread_id": thread_id}})
        except Exception:
            return []

        values = getattr(snapshot, "values", {}) or {}
        tasks = values.get("async_tasks") or {}
        if not isinstance(tasks, dict):
            return []

        rows: list[dict[str, Any]] = []
        for task_id, task in tasks.items():
            if not isinstance(task, dict):
                continue
            rows.append(
                {
                    "task_id": task_id,
                    "agent_type": task.get("agent_name", "unknown"),
                    "status": task.get("status", "unknown"),
                    "thread_id": task.get("thread_id", task_id),
                    "run_id": task.get("run_id", ""),
                    "created_at": task.get("created_at", ""),
                    "last_checked_at": task.get("last_checked_at", ""),
                    "last_updated_at": task.get("last_updated_at", ""),
                }
            )

        rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        return rows
