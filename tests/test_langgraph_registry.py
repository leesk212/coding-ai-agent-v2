from __future__ import annotations

import json
import unittest
from pathlib import Path


class LangGraphRegistryTests(unittest.TestCase):
    def test_langgraph_json_registers_supervisor_and_subagents(self) -> None:
        config = json.loads(Path("langgraph.json").read_text(encoding="utf-8"))
        graphs = config["graphs"]

        self.assertEqual(
            set(graphs.keys()),
            {"supervisor", "researcher", "coder", "reviewer", "debugger"},
        )
        self.assertEqual(graphs["supervisor"], "./src/coding_agent/graphs.py:supervisor")


if __name__ == "__main__":
    unittest.main()
