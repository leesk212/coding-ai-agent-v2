"""DeepAgents v0.5-style agent assembly for the Coding AI Agent."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from deepagents import AsyncSubAgent, create_deep_agent
from coding_agent.async_subagent_manager import LocalAsyncSubagentManager
from coding_agent.async_task_tracker import AsyncTaskTracker
from coding_agent.config import Settings, settings
from coding_agent.middleware.async_only_subagents import AsyncOnlySubagentsMiddleware
from coding_agent.middleware.async_task_completion import AsyncTaskCompletionMiddleware
from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
from coding_agent.middleware.model_fallback import ModelFallbackMiddleware

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are Danny's Coding AI Agent, a software engineering supervisor built with DeepAgents.

## Core Architecture
- You are the main supervisor agent created with `create_deep_agent`.
- Use the built-in async subagent tools to delegate background work to specialized local agents.
- Those async subagents run as separate local processes on the user's PC.

## Async Subagent Workflow
- Use `start_async_task` to launch background work when a task is large, parallelizable, or should continue while you reason.
- For normal "solve now" requests, keep working in the same turn until you collect relevant completed async task outputs and synthesize them.
- Use `check_async_task` to collect results after launch. Only stop immediately after launch when the user explicitly asks for background execution.
- Use `update_async_task` to change the instructions for an existing task.
- Use `cancel_async_task` to stop work that is no longer needed.
- Use `list_async_tasks` when you need a live overview of every active or completed subagent task.

## Aggregation Rules
- When multiple subagents were launched, collect their latest results before synthesizing a final answer.
- Never rely on stale task status from memory. Use `check_async_task` or `list_async_tasks`.
- When several completed subagents are relevant, summarize each result briefly and then synthesize the combined answer.

## Memory Usage
- Use `memory_search` before starting work when prior project context may help.
- Use `memory_store` for durable preferences, patterns, and architecture decisions.
"""


class AgentLoopGuard:
    """Simple loop-defense counters kept for UI/CLI compatibility."""

    def __init__(self, max_iterations: int = 25, max_retries: int = 3) -> None:
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.iteration_count = 0
        self.empty_response_count = 0
        self.tool_call_history: list[tuple[str, str]] = []

    def check_iteration(self) -> str | None:
        self.iteration_count += 1
        if self.iteration_count >= self.max_iterations:
            return (
                f"Reached maximum iterations ({self.max_iterations}). "
                "Stopping to prevent an infinite loop."
            )
        return None

    def check_empty_response(self, response: str) -> bool:
        if not response or not response.strip():
            self.empty_response_count += 1
            return self.empty_response_count < self.max_retries
        self.empty_response_count = 0
        return False

    def check_stuck(self, tool_name: str, args: str) -> str | None:
        args_hash = hashlib.md5(args.encode()).hexdigest()[:8]
        entry = (tool_name, args_hash)
        self.tool_call_history.append(entry)
        if len(self.tool_call_history) >= 3 and len(set(self.tool_call_history[-3:])) == 1:
            self.tool_call_history.clear()
            return f"Repeated identical tool call detected for `{tool_name}`."
        return None

    def reset(self) -> None:
        self.iteration_count = 0
        self.empty_response_count = 0
        self.tool_call_history.clear()


def _setup_agents_md(agent_id: str = "coding-agent") -> list[str]:
    agent_dir = Path.home() / ".deepagents" / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_md = agent_dir / "AGENTS.md"
    if not agent_md.exists():
        agent_md.write_text(
            "# Coding AI Agent Memory\n\nPersistent project and user memory.\n",
            encoding="utf-8",
        )

    sources = [str(agent_md)]
    for candidate in (
        Path.cwd() / ".deepagents" / "AGENTS.md",
        Path.cwd() / ".agents" / "AGENTS.md",
    ):
        if candidate.exists():
            sources.append(str(candidate))
    return sources


def create_coding_agent(
    custom_settings: Settings | None = None,
    cwd: Path | None = None,
    *,
    topology: str | None = None,
) -> dict[str, Any]:
    """Create the main supervisor with DeepAgents AsyncSubAgent specs."""

    cfg = custom_settings or settings
    working_dir = (cwd or Path.cwd()).resolve()

    try:
        from deepagents.backends import LocalShellBackend
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError as exc:  # pragma: no cover - dependency mismatch path
        raise RuntimeError(
            "DeepAgents v0.5+ with async subagent support is required. "
            "Install the updated dependencies from pyproject.toml."
        ) from exc

    fallback_mw = ModelFallbackMiddleware(
        models=cfg.get_all_models(),
        timeout=cfg.model_timeout,
    )
    ltm_mw = LongTermMemoryMiddleware(memory_dir=str(cfg.memory_dir))
    async_only_mw = AsyncOnlySubagentsMiddleware()
    completion_mw = AsyncTaskCompletionMiddleware()
    loop_guard = AgentLoopGuard(max_iterations=cfg.max_iterations)
    subagent_runtime = LocalAsyncSubagentManager(
        cfg=cfg,
        root_dir=working_dir,
        topology=topology,
    )

    async_subagents: list[AsyncSubAgent] = subagent_runtime.build_async_subagents()
    checkpointer = MemorySaver()
    backend = LocalShellBackend(
        root_dir=str(working_dir),
        inherit_env=True,
        virtual_mode=False,
    )

    agent = create_deep_agent(
        model=fallback_mw.get_model_with_fallback(),
        system_prompt=SYSTEM_PROMPT,
        middleware=[fallback_mw, ltm_mw, async_only_mw, completion_mw],
        tools=ltm_mw.get_tools(),
        subagents=async_subagents,
        memory=_setup_agents_md(),
        skills=[],
        checkpointer=checkpointer,
        backend=backend,
        debug=False,
        name="coding-ai-agent",
    )

    logger.info(
        "Created DeepAgents supervisor with %d AsyncSubAgent specs",
        len(async_subagents),
    )

    return {
        "agent": agent,
        "backend": backend,
        "fallback_middleware": fallback_mw,
        "memory_middleware": ltm_mw,
        "subagent_middleware": subagent_runtime,
        "subagent_manager": subagent_runtime,
        "subagent_runtime": subagent_runtime,
        "deployment_topology": subagent_runtime.topology,
        "async_subagents": async_subagents,
        "async_task_tracker": AsyncTaskTracker(agent),
        "loop_guard": loop_guard,
        "checkpointer": checkpointer,
    }
