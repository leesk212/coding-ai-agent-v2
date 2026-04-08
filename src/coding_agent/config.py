"""Configuration management for the Coding AI Agent.

Uses OpenRouter open-source models as primary, with Ollama local fallback.
"""

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
    provider: str  # "openrouter" or "ollama"
    priority: int  # lower = preferred

    def __hash__(self) -> int:
        return hash(self.name)

    def to_model_string(self) -> str:
        """Convert to DeepAgents CLI model string format: 'provider:model_name'."""
        if self.provider == "openrouter":
            return f"openrouter:{self.name}"
        elif self.provider == "ollama":
            return f"ollama:{self.name}"
        return self.name


# ── Recommended open-source models (OpenRouter) ──────────────────────
# Reference: project requirements recommend these open models for bonus points
DEFAULT_MODELS = [
    ModelSpec("qwen/qwen3.5-35b-a3b", "openrouter", 1),
    ModelSpec("nvidia/nemotron-3-super-120b-a12b", "openrouter", 2),
    ModelSpec("z-ai/glm-5v-turbo", "openrouter", 3),
    ModelSpec("deepseek/deepseek-chat-v3-0324", "openrouter", 4),
    ModelSpec("qwen/qwen-2.5-coder-32b-instruct", "openrouter", 5),
]

# Local fallback model (Ollama)
DEFAULT_LOCAL_MODEL = ModelSpec(
    name=os.getenv("LOCAL_FALLBACK_MODEL", "qwen2.5-coder:7b"),
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
    async_subagent_host: str = field(
        default_factory=lambda: os.getenv("ASYNC_SUBAGENT_HOST", "127.0.0.1")
    )
    async_subagent_base_port: int = field(
        default_factory=lambda: int(os.getenv("ASYNC_SUBAGENT_BASE_PORT", "30240"))
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

    @property
    def primary_model_string(self) -> str:
        """Get the primary model as a DeepAgents CLI model string."""
        if self.model_priority:
            return self.model_priority[0].to_model_string()
        return self.local_fallback_model.to_model_string()


# Global settings instance
settings = Settings()
