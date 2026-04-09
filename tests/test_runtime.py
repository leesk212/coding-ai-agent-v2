from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from coding_agent.config import Settings
from coding_agent.runtime import create_runtime_components


class RuntimeSelectionTests(unittest.TestCase):
    def test_single_topology_uses_remote_runtime(self) -> None:
        cfg = Settings(
            deployment_topology="single",
            langgraph_deployment_url="http://localhost:2024",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch("coding_agent.runtime.create_remote_coding_agent", return_value={"mode": "remote"}) as remote_mock:
                result = create_runtime_components(cfg, cwd=Path(tmp))

        self.assertEqual(result, {"mode": "remote"})
        remote_mock.assert_called_once()

    def test_split_topology_uses_local_runtime(self) -> None:
        cfg = Settings(deployment_topology="split")
        with tempfile.TemporaryDirectory() as tmp:
            with patch("coding_agent.runtime.create_coding_agent", return_value={"mode": "local"}) as local_mock:
                result = create_runtime_components(cfg, cwd=Path(tmp))

        self.assertEqual(result, {"mode": "local"})
        local_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
