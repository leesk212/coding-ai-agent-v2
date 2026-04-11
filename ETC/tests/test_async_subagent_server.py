from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import coding_agent.async_subagent_server as server


FAKE_RESPONSE = {"messages": [AIMessage(content="Here are the coding results.")]}


class AsyncSubagentServerTests(unittest.TestCase):
    def setUp(self) -> None:
        server._CONN.executescript("DROP TABLE IF EXISTS runs; DROP TABLE IF EXISTS threads;")
        server._init_db()
        server._ARGS = SimpleNamespace(
            agent_type="coder",
            graph_id="coder",
            host="127.0.0.1",
            port=30241,
            root_dir=".",
            model="openrouter:qwen/qwen3.5-35b-a3b",
            system_prompt="You are a coder.",
        )

    def _make_client(self) -> TestClient:
        async def fake_astream(*_args, **_kwargs):
            yield (AIMessage(content="Here "), {})
            yield (AIMessage(content="are the coding results."), {})

        fake_agent = SimpleNamespace(
            ainvoke=AsyncMock(return_value=FAKE_RESPONSE),
            astream=fake_astream,
        )
        patcher = patch.object(server, "_bootstrap_agent", return_value=fake_agent)
        self.addCleanup(patcher.stop)
        patcher.start()
        return TestClient(server.app)

    def test_health(self) -> None:
        with self._make_client() as client:
            resp = client.get("/ok")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})

    def test_create_thread(self) -> None:
        with self._make_client() as client:
            resp = client.post("/threads")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("thread_id", data)
        self.assertEqual(data["messages"], [])

    def test_full_lifecycle(self) -> None:
        with self._make_client() as client:
            thread = client.post("/threads").json()
            thread_id = thread["thread_id"]

            run = client.post(
                f"/threads/{thread_id}/runs",
                json={
                    "assistant_id": "coder",
                    "input": {"messages": [{"role": "user", "content": "implement fibonacci"}]},
                },
            ).json()
            run_id = run["run_id"]

            asyncio.run(asyncio.sleep(0.2))

            status_resp = client.get(f"/threads/{thread_id}/runs/{run_id}")
            self.assertEqual(status_resp.status_code, 200)
            self.assertEqual(status_resp.json()["status"], "success")
            partial_output = status_resp.json()["partial_output"]
            self.assertIn("[status] subagent started", partial_output)
            self.assertIn("Here are the coding results.", partial_output)

            thread_resp = client.get(f"/threads/{thread_id}")
            self.assertEqual(thread_resp.status_code, 200)
            thread_data = thread_resp.json()
            values_messages = thread_data["values"]["messages"]
            self.assertTrue(any(m["content"] == "Here are the coding results." for m in values_messages))

    def test_interrupt_strategy_marks_first_run_cancelled(self) -> None:
        async def slow_ainvoke(*_args, **_kwargs):
            await asyncio.sleep(10)
            return FAKE_RESPONSE

        slow_agent = SimpleNamespace(ainvoke=AsyncMock(side_effect=slow_ainvoke))
        with patch.object(server, "_bootstrap_agent", return_value=slow_agent):
            with TestClient(server.app) as client:
                thread = client.post("/threads").json()
                thread_id = thread["thread_id"]
                first = client.post(
                    f"/threads/{thread_id}/runs",
                    json={
                        "assistant_id": "coder",
                        "input": {"messages": [{"role": "user", "content": "first"}]},
                    },
                ).json()
                second = client.post(
                    f"/threads/{thread_id}/runs",
                    json={
                        "assistant_id": "coder",
                        "input": {"messages": [{"role": "user", "content": "second"}]},
                        "multitask_strategy": "interrupt",
                    },
                ).json()
                self.assertIn("run_id", second)
                first_status = client.get(f"/threads/{thread_id}/runs/{first['run_id']}").json()
                self.assertEqual(first_status["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
