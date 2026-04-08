"""Tests for OpenAI fallback model selection behavior."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from coding_agent.config import Settings


class OpenAIFallbackSelectionTests(unittest.TestCase):
    def test_get_all_models_includes_openai_when_key_present(self) -> None:
        cfg = Settings(openai_api_key="test-key")
        names = [m.provider for m in cfg.get_all_models()]
        self.assertIn("openai", names)

    def test_get_all_models_excludes_openai_when_key_missing(self) -> None:
        cfg = Settings(openai_api_key="")
        names = [m.provider for m in cfg.get_all_models()]
        self.assertNotIn("openai", names)

    @patch("coding_agent.config.find_spec")
    def test_get_all_models_excludes_ollama_when_client_missing(self, mock_find_spec) -> None:
        mock_find_spec.return_value = None
        cfg = Settings(openai_api_key="test-key")
        names = [m.provider for m in cfg.get_all_models()]
        self.assertNotIn("ollama", names)

    @patch("coding_agent.config.find_spec")
    def test_get_all_models_includes_ollama_when_client_available(self, mock_find_spec) -> None:
        def _fake_find_spec(name: str):
            if name == "langchain_ollama":
                return object()
            return None

        mock_find_spec.side_effect = _fake_find_spec
        cfg = Settings(openai_api_key="test-key")
        names = [m.provider for m in cfg.get_all_models()]
        self.assertIn("ollama", names)


if __name__ == "__main__":
    unittest.main()
