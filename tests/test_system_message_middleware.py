from __future__ import annotations

import unittest
from dataclasses import dataclass

from langchain_core.messages import SystemMessage

from coding_agent.middleware.async_task_completion import AsyncTaskCompletionMiddleware
from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware


@dataclass
class _Req:
    system_message: object | None = None
    messages: list[object] | None = None

    def override(self, **kwargs):
        return _Req(
            system_message=kwargs.get("system_message", self.system_message),
            messages=kwargs.get("messages", self.messages),
        )


class SystemMessageMiddlewareTests(unittest.TestCase):
    def test_async_task_completion_keeps_system_message_type(self) -> None:
        mw = AsyncTaskCompletionMiddleware()
        req = _Req(system_message=SystemMessage(content_blocks=[{"type": "text", "text": "base"}]))
        out = mw._inject_policy(req)  # noqa: SLF001
        self.assertIsInstance(out.system_message, SystemMessage)
        self.assertGreaterEqual(len(out.system_message.content_blocks), 2)

    def test_long_term_memory_keeps_system_message_type(self) -> None:
        mw = LongTermMemoryMiddleware(memory_dir=":memory:")
        req = _Req(system_message=SystemMessage(content_blocks=[{"type": "text", "text": "base"}]), messages=[])

        def _handler(request):
            return request

        out = mw.wrap_model_call(req, _handler)
        self.assertIsInstance(out.system_message, SystemMessage)
        self.assertGreaterEqual(len(out.system_message.content_blocks), 2)


if __name__ == "__main__":
    unittest.main()
