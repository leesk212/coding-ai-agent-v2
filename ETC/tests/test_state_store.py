from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coding_agent.state.store import DurableStateStore
from coding_agent.webui._pages.chat import _capture_subagent_history_snapshot


class DurableStateStoreTests(unittest.TestCase):
    def test_memory_layers_and_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableStateStore(Path(tmp) / "agent_state.db")
            record_id = store.store_memory(layer="user/profile", content="Prefer Korean explanations.")
            corrected_id = store.store_memory(
                layer="user/profile",
                content="Prefer Korean explanations with English code.",
                correction_of=record_id,
            )

            original = store.get_memory_record(record_id)
            corrected = store.get_memory_record(corrected_id)

        self.assertEqual(original["status"], "superseded")
        self.assertEqual(corrected["status"], "active")
        self.assertEqual(corrected["correction_of"], record_id)

    def test_subagent_lifecycle_lookup_by_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableStateStore(Path(tmp) / "agent_state.db")
            agent_id = store.create_subagent(
                role="researcher",
                task_summary="Investigate API contract",
                parent_id="main-agent",
            )
            store.update_subagent(agent_id, state="assigned", event_detail="assigned")
            store.update_subagent(agent_id, state="running", task_id="task-12345", event_detail="running")
            found = store.find_subagent_by_task_id("task-12345")
            events = store.list_subagent_events(agent_id)

        self.assertIsNotNone(found)
        self.assertEqual(found["agent_id"], agent_id)
        self.assertEqual(found["state"], "running")
        self.assertEqual([event["state"] for event in events], ["created", "assigned", "running"])

    def test_loop_run_upsert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableStateStore(Path(tmp) / "agent_state.db")
            store.upsert_loop_run(
                run_id="loop-1",
                thread_id="thread-1",
                status="running",
                current_step="planning",
            )
            store.upsert_loop_run(
                run_id="loop-1",
                thread_id="thread-1",
                status="completed",
                current_step="done",
            )
            row = store.get_loop_run("loop-1")

        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["current_step"], "done")

    def test_subagent_history_snapshot_preserves_lifecycle_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableStateStore(Path(tmp) / "agent_state.db")
            agent_id = store.create_subagent(
                role="coder",
                task_summary="Implement function",
                parent_id="main-agent",
            )
            store.update_subagent(agent_id, state="assigned", event_detail="assigned")
            store.update_subagent(
                agent_id,
                state="running",
                task_id="task-777",
                run_id="run-1",
                endpoint="127.0.0.1:30241",
                pid=1234,
                event_detail="running",
            )
            store.update_subagent(agent_id, state="completed", event_detail="done")

            snapshot = _capture_subagent_history_snapshot(
                [
                    {
                        "type": "coder",
                        "status": "completed",
                        "query": "Implement function",
                        "task_id": "task-777",
                        "run_id": "run-1",
                        "endpoint": "127.0.0.1:30241",
                        "pid": 1234,
                        "result_summary": "ok",
                    }
                ],
                store,
            )

        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0]["durable_state"], "completed")
        self.assertEqual(
            [event["state"] for event in snapshot[0]["lifecycle_events"]],
            ["created", "assigned", "running", "completed"],
        )


if __name__ == "__main__":
    unittest.main()
