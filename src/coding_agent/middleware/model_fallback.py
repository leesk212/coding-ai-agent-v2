"""Model Fallback Middleware - OpenRouter → Local LLM with Circuit Breaker.

Extends DeepAgents' model handling to automatically fall back through a priority
list of models when the current model fails or times out. The last resort is
always a local Ollama model.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    PrivateStateAttr,
    ResponseT,
)

from coding_agent.config import ModelSpec, settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Per-model circuit breaker to skip consistently failing models."""

    failure_count: int = 0
    failure_threshold: int = 3
    reset_timeout: float = 300.0
    last_failure_time: float = 0.0
    state: CircuitState = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d failures", self.failure_count
            )

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker HALF_OPEN, allowing test attempt")
                return True
            return False
        return True  # HALF_OPEN


class FallbackState(AgentState):
    """State for tracking which model is currently active."""

    fallback_model_used: NotRequired[str]
    fallback_errors: NotRequired[list[str]]


def _create_model(spec: ModelSpec) -> BaseChatModel:
    """Create a LangChain chat model from a ModelSpec."""
    if spec.provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=spec.name,
            openai_api_key=settings.openrouter_api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/coding-ai-agent",
                "X-Title": "CodingAIAgent",
            },
            request_timeout=settings.model_timeout,
        )
    elif spec.provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=spec.name,
            base_url=settings.ollama_base_url,
        )
    else:
        raise ValueError(f"Unknown provider: {spec.provider}")


class ModelFallbackMiddleware(AgentMiddleware[FallbackState, ContextT, ResponseT]):
    """Middleware that wraps LLM calls with automatic model fallback.

    Tries models in priority order. If a model fails or times out,
    automatically switches to the next model. Local Ollama is the last resort.

    Uses circuit breakers to skip models that consistently fail.
    """

    state_schema = FallbackState

    def __init__(
        self,
        models: list[ModelSpec] | None = None,
        timeout: float | None = None,
    ) -> None:
        all_models = models or settings.get_all_models()
        self.models = sorted(all_models, key=lambda m: m.priority)
        self.timeout = timeout or settings.model_timeout
        self.breakers: dict[str, CircuitBreaker] = {
            m.name: CircuitBreaker(
                failure_threshold=settings.circuit_breaker_threshold,
                reset_timeout=settings.circuit_breaker_reset,
            )
            for m in self.models
        }
        self._current_model_name: str | None = None
        self._model_cache: dict[str, BaseChatModel] = {}

    def _get_model(self, spec: ModelSpec) -> BaseChatModel:
        if spec.name not in self._model_cache:
            self._model_cache[spec.name] = _create_model(spec)
        return self._model_cache[spec.name]

    def _get_available_models(self) -> list[ModelSpec]:
        """Return models whose circuit breakers allow attempts."""
        return [m for m in self.models if self.breakers[m.name].can_attempt()]

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]],
    ) -> ModelResponse[ResponseT]:
        """Wrap model call with fallback logic.

        Tries each available model in priority order. On timeout or error,
        moves to the next model. Records success/failure for circuit breakers.
        """
        available = self._get_available_models()
        if not available:
            # All circuit breakers open - force reset the local model
            local = self.models[-1]  # lowest priority = local
            self.breakers[local.name].state = CircuitState.HALF_OPEN
            available = [local]

        errors: list[str] = []

        for spec in available:
            breaker = self.breakers[spec.name]
            model = self._get_model(spec)
            modified_request = request.override(model=model)

            try:
                logger.info("Trying model: %s (%s)", spec.name, spec.provider)

                if spec.provider == "ollama":
                    # No timeout for local models
                    response = await handler(modified_request)
                else:
                    response = await asyncio.wait_for(
                        handler(modified_request),
                        timeout=self.timeout,
                    )

                breaker.record_success()
                self._current_model_name = spec.name
                logger.info("Model %s succeeded", spec.name)

                # Inject model info into state
                if hasattr(response, 'state_update'):
                    response.state_update = {
                        **(response.state_update or {}),
                        "fallback_model_used": spec.name,
                    }

                return response

            except asyncio.TimeoutError:
                breaker.record_failure()
                err = f"{spec.name}: timeout after {self.timeout}s"
                errors.append(err)
                logger.warning(err)
                continue

            except Exception as e:
                breaker.record_failure()
                err = f"{spec.name}: {type(e).__name__}: {e}"
                errors.append(err)
                logger.warning(err)
                continue

        # All models failed - return error as AI message
        error_summary = "\n".join(errors)
        logger.error("All models failed:\n%s", error_summary)
        raise RuntimeError(
            f"All models failed. Errors:\n{error_summary}"
        )

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        """Synchronous fallback - tries models in order."""
        available = self._get_available_models()
        if not available:
            local = self.models[-1]
            self.breakers[local.name].state = CircuitState.HALF_OPEN
            available = [local]

        errors: list[str] = []

        for spec in available:
            breaker = self.breakers[spec.name]
            model = self._get_model(spec)
            modified_request = request.override(model=model)

            try:
                logger.info("Trying model: %s (%s)", spec.name, spec.provider)
                response = handler(modified_request)
                breaker.record_success()
                self._current_model_name = spec.name
                return response
            except Exception as e:
                breaker.record_failure()
                err = f"{spec.name}: {type(e).__name__}: {e}"
                errors.append(err)
                logger.warning(err)
                continue

        error_summary = "\n".join(errors)
        raise RuntimeError(f"All models failed. Errors:\n{error_summary}")

    @property
    def current_model(self) -> str | None:
        return self._current_model_name

    def get_status(self) -> dict[str, Any]:
        """Get current status of all models and circuit breakers."""
        return {
            "current_model": self._current_model_name,
            "models": [
                {
                    "name": m.name,
                    "provider": m.provider,
                    "priority": m.priority,
                    "circuit_state": self.breakers[m.name].state.value,
                    "failure_count": self.breakers[m.name].failure_count,
                }
                for m in self.models
            ],
        }
