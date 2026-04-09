"""Official LangGraph registry for DeepAgents async-subagent deployments.

This module is intended to back `langgraph.json` so the project can be run as a
single co-deployed DeepAgents application, which is the recommended starting
topology for async subagents in the official docs.
"""

from __future__ import annotations

from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

from coding_agent.agent import SYSTEM_PROMPT, _setup_agents_md
from coding_agent.async_subagent_manager import DEFAULT_ASYNC_SUBAGENTS, LocalAsyncSubagentManager
from coding_agent.config import settings
from coding_agent.middleware.async_only_subagents import AsyncOnlySubagentsMiddleware
from coding_agent.middleware.async_task_completion import AsyncTaskCompletionMiddleware
from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
from coding_agent.middleware.model_fallback import ModelFallbackMiddleware, create_model


def _working_dir() -> Path:
    return Path.cwd().resolve()


def _backend() -> LocalShellBackend:
    return LocalShellBackend(
        root_dir=str(_working_dir()),
        inherit_env=True,
        virtual_mode=False,
    )


def _model_fallback() -> ModelFallbackMiddleware:
    return ModelFallbackMiddleware(
        models=settings.get_all_models(),
        timeout=settings.model_timeout,
    )


def _memory() -> LongTermMemoryMiddleware:
    return LongTermMemoryMiddleware(memory_dir=str(settings.memory_dir))


def create_specialist_graph(agent_name: str):
    meta = DEFAULT_ASYNC_SUBAGENTS[agent_name]
    fallback_mw = _model_fallback()
    ltm_mw = _memory()
    return create_deep_agent(
        model=fallback_mw.get_model_with_fallback(),
        system_prompt=str(meta["system_prompt"]),
        middleware=[fallback_mw, ltm_mw],
        tools=ltm_mw.get_tools(),
        backend=_backend(),
        memory=_setup_agents_md(agent_id=f"coding-agent-{agent_name}"),
        skills=[],
        debug=False,
        name=agent_name,
    )


def create_supervisor_graph():
    fallback_mw = _model_fallback()
    ltm_mw = _memory()
    runtime = LocalAsyncSubagentManager(
        cfg=settings,
        root_dir=_working_dir(),
        topology="single",
    )
    async_subagents = runtime.build_async_subagents()
    return create_deep_agent(
        model=fallback_mw.get_model_with_fallback(),
        system_prompt=SYSTEM_PROMPT,
        middleware=[
            fallback_mw,
            ltm_mw,
            AsyncOnlySubagentsMiddleware(),
            AsyncTaskCompletionMiddleware(),
        ],
        tools=ltm_mw.get_tools(),
        subagents=async_subagents,
        backend=_backend(),
        memory=_setup_agents_md(),
        skills=[],
        debug=False,
        name="coding-ai-agent",
    )


supervisor = create_supervisor_graph()
researcher = create_specialist_graph("researcher")
coder = create_specialist_graph("coder")
reviewer = create_specialist_graph("reviewer")
debugger = create_specialist_graph("debugger")
