from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from coding_agent.async_subagent_manager import (
    LocalAsyncSubagentManager,
    load_async_subagent_specs,
    load_async_subagents,
)


class AsyncSubagentManagerTests(unittest.TestCase):
    def test_build_async_subagents_returns_deepagents_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = LocalAsyncSubagentManager(root_dir=Path(tmp), topology="split")
            specs = manager.build_async_subagents()

        self.assertTrue(specs)
        names = {spec["name"] for spec in specs}
        self.assertIn("researcher", names)
        self.assertIn("coder", names)
        self.assertIn("frontend", names)
        self.assertIn("backend", names)
        self.assertIn("planner", names)
        self.assertIn("architect", names)
        self.assertIn("mobile", names)

        researcher = next(spec for spec in specs if spec["name"] == "researcher")
        self.assertEqual(researcher["graph_id"], "researcher")
        self.assertIn("url", researcher)
        self.assertTrue(str(researcher["url"]).startswith("http://127.0.0.1:"))

    def test_single_topology_omits_urls_for_asgi_transport(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = LocalAsyncSubagentManager(root_dir=Path(tmp), topology="single")
            specs = manager.build_async_subagents()

        self.assertTrue(specs)
        self.assertTrue(all("url" not in spec for spec in specs))

    def test_load_async_subagents_reads_config_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                """
[async_subagents.researcher]
description = "Research override"
graph_id = "research-v2"
transport = "asgi"
                """.strip(),
                encoding="utf-8",
            )
            loaded = load_async_subagents(config_path)

        self.assertEqual(loaded["researcher"]["description"], "Research override")
        self.assertEqual(loaded["researcher"]["graph_id"], "research-v2")
        self.assertEqual(loaded["researcher"]["transport"], "asgi")

    def test_load_async_subagent_specs_reads_reference_style_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.toml"
            config_path.write_text(
                """
[async_subagents.researcher]
description = "Research override"
graph_id = "research-v2"
url = "http://127.0.0.1:31111"
headers = { Authorization = "Bearer demo" }
                """.strip(),
                encoding="utf-8",
            )
            loaded = load_async_subagent_specs(config_path)

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["name"], "researcher")
        self.assertEqual(loaded[0]["description"], "Research override")
        self.assertEqual(loaded[0]["graph_id"], "research-v2")
        self.assertEqual(loaded[0]["url"], "http://127.0.0.1:31111")
        self.assertEqual(loaded[0]["headers"]["Authorization"], "Bearer demo")


if __name__ == "__main__":
    unittest.main()
