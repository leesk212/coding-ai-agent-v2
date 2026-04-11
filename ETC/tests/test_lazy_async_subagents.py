from __future__ import annotations

import unittest

from langchain_core.messages import ToolMessage

from coding_agent.middleware.lazy_async_subagents import LazyAsyncSubagentsMiddleware


class _FakeRuntime:
    def __init__(self, topology: str = "split", error: Exception | None = None) -> None:
        self.topology = topology
        self.error = error
        self.started: list[str] = []
        self.created: list[tuple[str, str]] = []
        self.noted: list[tuple[str, str]] = []

    def begin_task(self, role: str, task_summary: str, parent_id: str = "main-agent") -> str:
        self.created.append((role, task_summary))
        return "sa_test"

    def ensure_started(self, name: str) -> None:
        if self.error is not None:
            raise self.error
        self.started.append(name)

    def note_runtime_state(self, role: str, *, state: str, task_summary: str = "", error: str = "") -> None:
        self.noted.append((role, state))


class _FakeRequest:
    def __init__(self, name: str, args: dict[str, object]) -> None:
        self.tool_call = {
            "id": "tool-1",
            "name": name,
            "args": args,
        }


class LazyAsyncSubagentsMiddlewareTests(unittest.TestCase):
    def test_start_async_task_starts_named_subagent_in_split_topology(self) -> None:
        runtime = _FakeRuntime(topology="split")
        middleware = LazyAsyncSubagentsMiddleware(runtime)  # type: ignore[arg-type]
        request = _FakeRequest(
            "start_async_task",
            {"subagent_type": "researcher", "description": "investigate"},
        )

        result = middleware.wrap_tool_call(request, lambda req: ToolMessage(content="ok", tool_call_id=req.tool_call["id"]))

        self.assertEqual(runtime.started, ["researcher"])
        self.assertEqual(runtime.created, [("researcher", "investigate")])
        self.assertEqual(runtime.noted[-1], ("researcher", "running"))
        self.assertEqual(result.content, "ok")

    def test_non_start_tool_does_not_start_runtime(self) -> None:
        runtime = _FakeRuntime(topology="split")
        middleware = LazyAsyncSubagentsMiddleware(runtime)  # type: ignore[arg-type]
        request = _FakeRequest("check_async_task", {"task_id": "abc"})

        middleware.wrap_tool_call(request, lambda req: ToolMessage(content="ok", tool_call_id=req.tool_call["id"]))

        self.assertEqual(runtime.started, [])

    def test_startup_failure_returns_error_tool_message(self) -> None:
        runtime = _FakeRuntime(topology="split", error=RuntimeError("boom"))
        middleware = LazyAsyncSubagentsMiddleware(runtime)  # type: ignore[arg-type]
        request = _FakeRequest("start_async_task", {"subagent_type": "coder"})

        result = middleware.wrap_tool_call(request, lambda req: ToolMessage(content="ok", tool_call_id=req.tool_call["id"]))

        self.assertIsInstance(result, ToolMessage)
        self.assertEqual(result.status, "error")
        self.assertIn("Failed to prepare async subagent `coder`", str(result.content))
        self.assertEqual(runtime.noted[-1], ("coder", "failed"))

    def test_single_topology_skips_lazy_start(self) -> None:
        runtime = _FakeRuntime(topology="single")
        middleware = LazyAsyncSubagentsMiddleware(runtime)  # type: ignore[arg-type]
        request = _FakeRequest("start_async_task", {"subagent_type": "reviewer"})

        middleware.wrap_tool_call(request, lambda req: ToolMessage(content="ok", tool_call_id=req.tool_call["id"]))

        self.assertEqual(runtime.started, [])


if __name__ == "__main__":
    unittest.main()
