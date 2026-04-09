"""DeepAgents v0.5-style agent assembly for the Coding AI Agent.

This module intentionally mirrors the DeepAgents CLI composition style:
- load and normalize AsyncSubAgent specs first
- build a clear middleware stack
- build a concrete system prompt from runtime context
- assemble `create_deep_agent(...)` last
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from deepagents import AsyncSubAgent, create_deep_agent
from coding_agent.async_subagent_manager import LocalAsyncSubagentManager
from coding_agent.async_task_tracker import AsyncTaskTracker
from coding_agent.config import Settings, settings
from coding_agent.middleware.async_only_subagents import AsyncOnlySubagentsMiddleware
from coding_agent.middleware.async_task_completion import AsyncTaskCompletionMiddleware
from coding_agent.middleware.lazy_async_subagents import LazyAsyncSubagentsMiddleware
from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
from coding_agent.middleware.model_fallback import ModelFallbackMiddleware
from coding_agent.middleware.subagent_lifecycle import SubAgentLifecycleMiddleware

logger = logging.getLogger(__name__)


BASE_SYSTEM_PROMPT = """You are Danny's Coding AI Agent, a software engineering supervisor built with DeepAgents.

## Core Architecture
- You are the main supervisor agent created with `create_deep_agent`.
- Use the built-in async subagent tools to delegate background work to specialized local agents.
- Those async subagents run as separate local processes on the user's PC.

## Async Subagent Workflow
- Use `start_async_task` to launch background work when a task is large, parallelizable, or should continue while you reason.
- If the user explicitly asks for subagents, lifecycle validation, async review, code+review, or parallel delegation, you must use `start_async_task` instead of solving the entire request alone.
- For product-building requests with PRD, task breakdown, spec-driven development, TDD, web/mobile support, or clear frontend/backend separation, prefer splitting work across specialized subagents such as `planner`, `architect`, `researcher`, `frontend`, `backend`, `mobile`, and `reviewer`.
- For normal "solve now" requests, keep working in the same turn until you collect relevant completed async task outputs and synthesize them.
- Use `check_async_task` to collect results after launch. Only stop immediately after launch when the user explicitly asks for background execution.
- Use `update_async_task` to change the instructions for an existing task.
- Use `cancel_async_task` to stop work that is no longer needed.
- Use `list_async_tasks` when you need a live overview of every active or completed subagent task.
- Do not launch dependent subagents in parallel when one needs another's artifact.
- Example: if `reviewer` must review code written by `coder`, wait until `coder` completes and you know the file path or code artifact before launching `reviewer`.
- Example: for a project request like "build a Task PMS system with PRD, spec, web/mobile UX, gantt chart, and TDD", split PRD/work breakdown to `planner`, system design to `architect`, web UI to `frontend`, mobile UX to `mobile`, backend/data/APIs to `backend`, and final validation to `reviewer`.
- When delegating implementation work, include the expected target file path in the subagent task description whenever possible.
- If the user asks to perform development work, build a system, implement a project, or execute the spec, the deliverable must include executable code artifacts. Do not stop at PRD, plan, architecture, or abstract specs unless the user explicitly limits the scope to documentation only.
- If the turn produced durable artifacts worth remembering, use a `remember` subagent at the end to nominate up to 10 files for long-term memory review. Only after human approval may those artifacts be stored into long-term memory.

## Aggregation Rules
- When multiple subagents were launched, collect their latest results before synthesizing a final answer.
- Never rely on stale task status from memory. Use `check_async_task` or `list_async_tasks`.
- When several completed subagents are relevant, summarize each result briefly and then synthesize the combined answer.

## Memory Usage
- Use `memory_search` before starting work when prior project context may help.
- Use `memory_store` for durable preferences, patterns, and architecture decisions.
"""


def build_system_prompt(
    *,
    cfg: Settings,
    cwd: Path,
    topology: str,
    async_subagents: list[AsyncSubAgent],
) -> str:
    """Build a runtime-aware system prompt, similar to DeepAgents CLI."""
    model_identity = cfg.primary_model_string
    main_prompt_override = cfg.main_system_prompt_override.strip()
    subagent_lines = []
    for spec in async_subagents:
        line = f"- `{spec['name']}` -> graph_id=`{spec['graph_id']}`"
        if spec.get("url"):
            line += f", url=`{spec['url']}`"
        else:
            line += ", transport=`asgi`"
        subagent_lines.append(line)
    subagent_block = "\n".join(subagent_lines) if subagent_lines else "- No async subagents configured"

    prompt = (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        "## Runtime Context\n"
        f"- Deployment topology: `{topology}`\n"
        f"- Working directory: `{cwd}`\n"
        f"- Primary model: `{model_identity}`\n"
        f"- OpenRouter enabled: `{cfg.has_openrouter}`\n\n"
        "## Registered AsyncSubAgents\n"
        f"{subagent_block}\n\n"
        "## Execution Rules\n"
        "- Prefer async subagents for parallelizable or specialized work.\n"
        "- Use only the information required by each subagent; do not forward full chat history blindly.\n"
        "- If a subagent fails or blocks, collect the latest state and either recover or stop safely.\n"
        "- Keep file paths absolute and scoped to the current working directory.\n"
    )
    if main_prompt_override:
        prompt += f"\n## User Prompt Override\n{main_prompt_override}\n"
    return prompt


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
    progress_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Create the main supervisor with DeepAgents AsyncSubAgent specs."""

    prewarmed = prewarm_coding_agent(
        custom_settings=custom_settings,
        cwd=cwd,
        topology=topology,
        progress_cb=progress_cb,
    )
    return finalize_coding_agent(prewarmed, progress_cb=progress_cb)


def prewarm_coding_agent(
    custom_settings: Settings | None = None,
    cwd: Path | None = None,
    *,
    topology: str | None = None,
    progress_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Prewarm everything except the final model-bound DeepAgents graph assembly."""

    cfg = custom_settings or settings
    working_dir = (cwd or Path.cwd()).resolve()
    if progress_cb:
        progress_cb(f"Preparing local coding agent (topology={topology or cfg.deployment_topology}, cwd={working_dir})")

    try:
        from deepagents.backends import LocalShellBackend
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError as exc:  # pragma: no cover - dependency mismatch path
        raise RuntimeError(
            "DeepAgents v0.5+ with async subagent support is required. "
            "Install the updated dependencies from pyproject.toml."
        ) from exc

    if progress_cb:
        progress_cb("Creating model fallback middleware")
    fallback_mw = ModelFallbackMiddleware(
        models=cfg.get_all_models(),
        timeout=cfg.model_timeout,
    )
    if progress_cb:
        progress_cb("Creating long-term memory middleware")
    ltm_mw = LongTermMemoryMiddleware(memory_dir=str(cfg.memory_dir))
    if progress_cb:
        progress_cb("Creating async-only and lifecycle middleware")
    async_only_mw = AsyncOnlySubagentsMiddleware()
    subagent_runtime = LocalAsyncSubagentManager(
        cfg=cfg,
        root_dir=working_dir,
        topology=topology,
    )
    if progress_cb:
        progress_cb("Creating lazy async subagent runtime manager")
    lazy_async_mw = LazyAsyncSubagentsMiddleware(subagent_runtime)
    subagent_lifecycle_mw = SubAgentLifecycleMiddleware(subagent_runtime)
    completion_mw = AsyncTaskCompletionMiddleware()
    loop_guard = AgentLoopGuard(max_iterations=cfg.max_iterations)

    if progress_cb:
        progress_cb("Building AsyncSubAgent specs")
    async_subagents: list[AsyncSubAgent] = subagent_runtime.build_async_subagents()
    if progress_cb:
        progress_cb(f"AsyncSubAgent specs ready: {', '.join(spec.get('name', '?') for spec in async_subagents)}")
        progress_cb(f"Building runtime-aware system prompt (cwd={working_dir})")
    system_prompt = build_system_prompt(
        cfg=cfg,
        cwd=working_dir,
        topology=subagent_runtime.topology,
        async_subagents=async_subagents,
    )
    if progress_cb:
        progress_cb("Creating checkpointer and shell backend")
    checkpointer = MemorySaver()
    backend = LocalShellBackend(
        root_dir=str(working_dir),
        inherit_env=True,
        virtual_mode=False,
    )

    return {
        "backend": backend,
        "working_dir": str(working_dir),
        "cfg": cfg,
        "system_prompt": system_prompt,
        "tools": ltm_mw.get_tools(),
        "memory_sources": _setup_agents_md(),
        "fallback_middleware": fallback_mw,
        "memory_middleware": ltm_mw,
        "async_only_middleware": async_only_mw,
        "lazy_async_middleware": lazy_async_mw,
        "subagent_lifecycle_middleware": subagent_lifecycle_mw,
        "completion_middleware": completion_mw,
        "subagent_middleware": subagent_runtime,
        "subagent_manager": subagent_runtime,
        "subagent_runtime": subagent_runtime,
        "state_store": subagent_runtime.state_store,
        "deployment_topology": subagent_runtime.topology,
        "async_subagents": async_subagents,
        "loop_guard": loop_guard,
        "checkpointer": checkpointer,
        "prewarmed": True,
    }


def finalize_coding_agent(
    prewarmed: dict[str, Any],
    *,
    progress_cb: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Create the final DeepAgents graph from a prewarmed local runtime bundle."""

    if progress_cb:
        progress_cb("Binding model provider with current API key configuration")
    fallback_mw = prewarmed["fallback_middleware"]
    if progress_cb:
        progress_cb("Assembling DeepAgents supervisor graph")
    agent = create_deep_agent(
        model=fallback_mw.get_model_with_fallback(),
        system_prompt=prewarmed["system_prompt"],
        middleware=[
            fallback_mw,
            prewarmed["memory_middleware"],
            prewarmed["async_only_middleware"],
            prewarmed["lazy_async_middleware"],
            prewarmed["subagent_lifecycle_middleware"],
            prewarmed["completion_middleware"],
        ],
        tools=prewarmed["tools"],
        subagents=prewarmed["async_subagents"],
        memory=prewarmed["memory_sources"],
        skills=[],
        checkpointer=prewarmed["checkpointer"],
        backend=prewarmed["backend"],
        debug=False,
        name="coding-ai-agent",
    )
    if progress_cb:
        progress_cb("DeepAgents supervisor graph assembled")

    logger.info(
        "Created DeepAgents supervisor with %d AsyncSubAgent specs",
        len(prewarmed["async_subagents"]),
    )

    components = dict(prewarmed)
    components["agent"] = agent
    components["async_task_tracker"] = AsyncTaskTracker(agent)
    return components
