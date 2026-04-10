from __future__ import annotations

import unittest

from langchain_core.messages import SystemMessage

from coding_agent.agent import BASE_SYSTEM_PROMPT
from coding_agent.middleware._system_message import append_system_message


class SystemMessageHelperTests(unittest.TestCase):
    def test_base_system_prompt_requires_memory_extraction(self) -> None:
        prompt = BASE_SYSTEM_PROMPT
        self.assertIn("long-term memory extraction path", prompt)
        self.assertIn("user/profile", prompt)
        self.assertIn("project/context", prompt)
        self.assertIn("domain/knowledge", prompt)
        self.assertIn("memory_store", prompt)
        self.assertIn("memory_search", prompt)

    def test_append_preserves_system_message_object(self) -> None:
        current = SystemMessage(content="BASE")

        updated = append_system_message(current, "EXTRA")

        self.assertIsInstance(updated, SystemMessage)
        self.assertIn("BASE", updated.content)
        self.assertIn("EXTRA", updated.content)
        self.assertTrue(updated.content_blocks)

    def test_append_string_returns_string(self) -> None:
        updated = append_system_message("BASE", "EXTRA")
        self.assertIsInstance(updated, str)
        self.assertIn("BASE", updated)
        self.assertIn("EXTRA", updated)


if __name__ == "__main__":
    unittest.main()
