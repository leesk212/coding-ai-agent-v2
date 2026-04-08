from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coding_agent.async_subagent_manager import (
    LocalAsyncSubagentManager,
    load_async_subagents,
)
from coding_agent.config import Settings


class AsyncSubagentConfigTests(unittest.TestCase):
    def test_load_async_subagents_returns_empty_when_file_missing(self) -> None:
        missing = Path("/tmp/definitely-missing-deepagents-config.toml")
        loaded = load_async_subagents(missing)
        self.assertEqual(loaded, {})

    def test_load_async_subagents_parses_valid_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                """
[async_subagents.researcher]
description = "Research specialist"
graph_id = "research_graph"
system_prompt = "Research deeply."
model = "openai:gpt-4o-mini"
url = "http://127.0.0.1:33221"

[async_subagents.invalid]
graph_id = "invalid_graph"
""".strip(),
                encoding="utf-8",
            )

            loaded = load_async_subagents(config_path)
            self.assertIn("researcher", loaded)
            self.assertNotIn("invalid", loaded)
            self.assertEqual(loaded["researcher"]["description"], "Research specialist")
            self.assertEqual(loaded["researcher"]["graph_id"], "research_graph")
            self.assertEqual(loaded["researcher"]["model"], "openai:gpt-4o-mini")
            self.assertEqual(loaded["researcher"]["host"], "127.0.0.1")
            self.assertEqual(loaded["researcher"]["port"], 33221)

    def test_manager_uses_subagent_host_port_model_overrides(self) -> None:
        cfg = Settings()
        manager = LocalAsyncSubagentManager(
            cfg=cfg,
            root_dir=Path.cwd(),
            subagents={
                "researcher": {
                    "description": "Research specialist",
                    "system_prompt": "Research deeply.",
                    "graph_id": "research_graph",
                    "host": "127.0.0.2",
                    "port": 39991,
                    "model": "openai:gpt-4o-mini",
                }
            },
        )
        spec = manager.get_async_subagent_specs()[0]
        self.assertEqual(spec["name"], "researcher")
        self.assertEqual(spec["graph_id"], "research_graph")
        self.assertEqual(spec["url"], "http://127.0.0.2:39991")


if __name__ == "__main__":
    unittest.main()
