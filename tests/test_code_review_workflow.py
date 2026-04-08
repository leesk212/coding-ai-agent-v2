"""Tests for code-writing + review workflow prompts and async-only tool policy."""

from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from coding_agent.middleware.async_only_subagents import AsyncOnlySubagentsMiddleware
from coding_agent.middleware.async_task_completion import (
    AsyncTaskCompletionMiddleware,
    COMPLETION_POLICY_PROMPT,
)
from coding_agent.webui._pages.chat import TEST_PROMPTS


class CodeReviewPromptTests(unittest.TestCase):
    def test_code_review_prompt_exists(self) -> None:
        self.assertIn("Code+Review Test", TEST_PROMPTS)

    def test_code_review_prompt_mentions_writer_and_reviewer(self) -> None:
        prompt = TEST_PROMPTS["Code+Review Test"].lower()
        self.assertIn("code_writer", prompt)
        self.assertIn("reviewer", prompt)
        self.assertIn("launch two async tasks", prompt)
        self.assertIn("collect", prompt)
        self.assertIn("same response", prompt)


@dataclass
class _FakeTool:
    name: str


class _FakeRequest:
    def __init__(self, tools):
        self.tools = tools

    def override(self, tools):
        return _FakeRequest(tools)


class _FakeRequestWithSystem:
    def __init__(self, system_message):
        self.system_message = system_message

    def override(self, system_message):
        return _FakeRequestWithSystem(system_message)


class AsyncOnlySubagentsMiddlewareTests(unittest.TestCase):
    def test_wrap_model_call_filters_sync_subagent_tools(self) -> None:
        mw = AsyncOnlySubagentsMiddleware()
        request = _FakeRequest(
            [
                _FakeTool("task"),
                _FakeTool("spawn_subagent"),
                _FakeTool("list_subagents"),
                _FakeTool("start_async_task"),
                _FakeTool("memory_search"),
            ]
        )

        seen = {}

        def handler(filtered_request):
            seen["tools"] = [tool.name for tool in filtered_request.tools]
            return "ok"

        result = mw.wrap_model_call(request, handler)

        self.assertEqual(result, "ok")
        self.assertEqual(seen["tools"], ["start_async_task", "memory_search"])

    def test_awrap_model_call_filters_sync_subagent_tools(self) -> None:
        mw = AsyncOnlySubagentsMiddleware()
        request = _FakeRequest(
            [
                _FakeTool("task"),
                _FakeTool("start_async_task"),
                _FakeTool("check_async_task"),
            ]
        )

        seen = {}

        async def handler(filtered_request):
            seen["tools"] = [tool.name for tool in filtered_request.tools]
            return "ok"

        result = asyncio.run(mw.awrap_model_call(request, handler))

        self.assertEqual(result, "ok")
        self.assertEqual(seen["tools"], ["start_async_task", "check_async_task"])


class AsyncTaskCompletionMiddlewareTests(unittest.TestCase):
    def test_wrap_model_call_appends_completion_policy(self) -> None:
        mw = AsyncTaskCompletionMiddleware()
        request = _FakeRequestWithSystem("BASE")

        seen = {}

        def handler(filtered_request):
            seen["system"] = filtered_request.system_message
            return "ok"

        result = mw.wrap_model_call(request, handler)
        self.assertEqual(result, "ok")
        rendered = (
            "".join(b.get("text", "") for b in seen["system"].content_blocks)
            if hasattr(seen["system"], "content_blocks")
            else str(seen["system"])
        )
        self.assertIn("BASE", rendered)
        self.assertIn("complete within the same user turn", rendered)
        self.assertIn(COMPLETION_POLICY_PROMPT.strip().splitlines()[0], rendered)


if __name__ == "__main__":
    unittest.main()
