"""Configuration management for the Coding AI Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelSpec:
    """Specification for an LLM model."""

    name: str
    context_window: int
    provider: str  # "openrouter" or "ollama"
    priority: int  # lower = preferred


# Default model priority list
DEFAULT_MODELS = [
    ModelSpec("deepseek/deepseek-chat-v3-0324", 65536, "openrouter", 1),
    ModelSpec("qwen/qwen-2.5-coder-32b-instruct", 32768, "openrouter", 2),
    ModelSpec("meta-llama/llama-3.3-70b-instruct", 131072, "openrouter", 3),
    ModelSpec("mistralai/mistral-small-3.1-24b-instruct", 96000, "openrouter", 4),
]

# Local fallback model (Ollama)
DEFAULT_LOCAL_MODEL = ModelSpec(
    name=os.getenv("LOCAL_FALLBACK_MODEL", "qwen2.5-coder:7b"),
    context_window=32768,
    provider="ollama",
    priority=99,
)


@dataclass
class Settings:
    """Application settings."""

    # API Keys
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )

    # Ollama
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # Model configuration
    model_priority: list[ModelSpec] = field(default_factory=lambda: list(DEFAULT_MODELS))
    local_fallback_model: ModelSpec = field(default_factory=lambda: DEFAULT_LOCAL_MODEL)

    # Memory
    memory_dir: Path = field(
        default_factory=lambda: Path(
            os.path.expanduser(os.getenv("MEMORY_DIR", "~/.coding_agent/memory"))
        )
    )

    # Sub-agents
    max_subagents: int = field(
        default_factory=lambda: int(os.getenv("MAX_SUBAGENTS", "3"))
    )

    # Agentic loop
    max_iterations: int = 25
    model_timeout: float = 60.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_reset: float = 300.0  # 5 minutes

    @property
    def has_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    def get_all_models(self) -> list[ModelSpec]:
        """Return all models in priority order, including local fallback."""
        return sorted(
            self.model_priority + [self.local_fallback_model],
            key=lambda m: m.priority,
        )


# Global settings instance
settings = Settings()
