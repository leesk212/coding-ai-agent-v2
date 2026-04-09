"""Configuration management for the Coding AI Agent.

Uses OpenRouter open-source models as primary, with optional Ollama or OpenAI
fallback.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ModelSpec:
    """Specification for an LLM model."""

    name: str
    provider: str  # "openrouter", "ollama", or "openai"
    priority: int  # lower = preferred

    def __hash__(self) -> int:
        return hash(self.name)

    def to_model_string(self) -> str:
        """Convert to DeepAgents CLI model string format: 'provider:model_name'."""
        if self.provider == "openrouter":
            return f"openrouter:{self.name}"
        elif self.provider == "ollama":
            return f"ollama:{self.name}"
        elif self.provider == "openai":
            return f"openai:{self.name}"
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

DEFAULT_OPENAI_FALLBACK_MODEL = ModelSpec(
    name=os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini"),
    provider="openai",
    priority=99,
)


@dataclass
class Settings:
    """Application settings."""

    # API Keys
    openrouter_api_key: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "")
    )
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )

    # Ollama
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # Model configuration
    model_priority: list[ModelSpec] = field(default_factory=lambda: list(DEFAULT_MODELS))
    local_fallback_model: ModelSpec = field(default_factory=lambda: DEFAULT_LOCAL_MODEL)
    openai_fallback_model: ModelSpec = field(default_factory=lambda: DEFAULT_OPENAI_FALLBACK_MODEL)
    fallback_mode: str = field(
        default_factory=lambda: os.getenv("FALLBACK_MODE", "local")
    )

    # Memory
    memory_dir: Path = field(
        default_factory=lambda: Path(
            os.path.expanduser(os.getenv("MEMORY_DIR", "~/.coding_agent/memory"))
        )
    )
    state_dir: Path = field(
        default_factory=lambda: Path(
            os.path.expanduser(os.getenv("STATE_DIR", "~/.coding_agent/state"))
        )
    )

    # Sub-agents
    max_subagents: int = field(
        default_factory=lambda: int(os.getenv("MAX_SUBAGENTS", "100"))
    )
    deployment_topology: str = field(
        default_factory=lambda: os.getenv("DEEPAGENTS_DEPLOYMENT_TOPOLOGY", "split")
    )
    langgraph_deployment_url: str = field(
        default_factory=lambda: os.getenv("LANGGRAPH_DEPLOYMENT_URL", "")
    )
    langgraph_assistant_id: str = field(
        default_factory=lambda: os.getenv("LANGGRAPH_ASSISTANT_ID", "supervisor")
    )
    async_subagent_host: str = field(
        default_factory=lambda: os.getenv("ASYNC_SUBAGENT_HOST", "127.0.0.1")
    )
    async_subagent_base_port: int = field(
        default_factory=lambda: int(os.getenv("ASYNC_SUBAGENT_BASE_PORT", "30240"))
    )
    main_system_prompt_override: str = ""
    subagent_system_prompt_overrides: dict[str, str] = field(default_factory=dict)

    # Agentic loop
    max_iterations: int = field(
        default_factory=lambda: int(os.getenv("MAX_ITERATIONS", "10000"))
    )
    model_timeout: float = 60.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_reset: float = 300.0  # 5 minutes

    @property
    def has_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def selected_fallback_model(self) -> ModelSpec | None:
        mode = (self.fallback_mode or "local").strip().lower()
        if mode == "none":
            return None
        if mode == "openai":
            return self.openai_fallback_model
        return self.local_fallback_model

    def get_all_models(self) -> list[ModelSpec]:
        """Return all models in priority order, including local fallback."""
        models = list(self.model_priority)
        fallback_model = self.selected_fallback_model
        if fallback_model is not None:
            models.append(fallback_model)
        return sorted(models, key=lambda m: m.priority)

    @property
    def primary_model_string(self) -> str:
        """Get the primary model as a DeepAgents CLI model string."""
        if self.model_priority:
            return self.model_priority[0].to_model_string()
        fallback_model = self.selected_fallback_model or self.local_fallback_model
        return fallback_model.to_model_string()

    @property
    def prompt_override_path(self) -> Path:
        return self.state_dir / "prompt_overrides.json"

    def load_prompt_overrides(self) -> None:
        path = self.prompt_override_path
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self.main_system_prompt_override = str(data.get("main_system_prompt_override", "") or "")
        raw = data.get("subagent_system_prompt_overrides", {})
        self.subagent_system_prompt_overrides = (
            {str(k): str(v) for k, v in raw.items() if str(v).strip()}
            if isinstance(raw, dict)
            else {}
        )

    def save_prompt_overrides(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "main_system_prompt_override": self.main_system_prompt_override,
            "subagent_system_prompt_overrides": self.subagent_system_prompt_overrides,
        }
        self.prompt_override_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# Global settings instance
settings = Settings()
settings.load_prompt_overrides()
