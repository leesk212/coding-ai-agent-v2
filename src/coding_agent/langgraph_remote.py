"""Remote LangGraph deployment client for supervisor execution."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph_sdk import get_sync_client

from coding_agent.async_subagent_manager import LocalAsyncSubagentManager
from coding_agent.async_task_tracker import AsyncTaskTracker
from coding_agent.config import Settings, settings
from coding_agent.memory.store import LongTermMemory


class RemoteFallbackStatus:
    def __init__(self, model_name: str = "langgraph-remote") -> None:
        self._current_model_name = model_name

    @property
    def current_model(self) -> str:
        return self._current_model_name

    def get_status(self) -> dict[str, Any]:
        return {
            "current_model": self._current_model_name,
            "models": [
                {
                    "name": self._current_model_name,
                    "provider": "langgraph",
                    "priority": 0,
                    "circuit_state": "closed",
                    "failure_count": 0,
                }
            ],
        }


class RemoteLoopGuard:
    def reset(self) -> None:
        return None


class RemoteMemoryFacade:
    def __init__(self, memory_dir: str) -> None:
        self.store = LongTermMemory(memory_dir)


class RemoteLangGraphAgent:
    """Adapter that makes a deployed LangGraph assistant look graph-like enough for the UI."""

    def __init__(self, deployment_url: str, assistant_id: str) -> None:
        self._client = get_sync_client(url=deployment_url, api_key=None)
        self._assistant_id = assistant_id

    @staticmethod
    def _serialize_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
        messages = []
        for msg in inputs.get("messages", []):
            if isinstance(msg, HumanMessage):
                messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, dict):
                messages.append(msg)
            else:
                content = getattr(msg, "content", str(msg))
                role = "user" if getattr(msg, "type", "") == "human" else "assistant"
                messages.append({"role": role, "content": content})
        return {"messages": messages}

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        thread_id = ((config or {}).get("configurable") or {}).get("thread_id")
        state = self._client.runs.wait(
            thread_id=thread_id,
            assistant_id=self._assistant_id,
            input=self._serialize_inputs(inputs),
            if_not_exists="create",
        )
        return state.get("values") or {}

    def stream(
        self,
        inputs: dict[str, Any],
        config: dict[str, Any] | None = None,
        *,
        stream_mode: list[str] | tuple[str, ...] | None = None,
        subgraphs: bool = False,
    ):
        thread_id = ((config or {}).get("configurable") or {}).get("thread_id")
        modes = list(stream_mode or ["messages", "updates"])
        for part in self._client.runs.stream(
            thread_id=thread_id,
            assistant_id=self._assistant_id,
            input=self._serialize_inputs(inputs),
            stream_mode=modes,
            stream_subgraphs=subgraphs,
            if_not_exists="create",
            multitask_strategy="interrupt",
            version="v2",
        ):
            event_type = str(part.get("type", "updates"))
            namespace = tuple(part.get("ns") or [])
            data = part.get("data")
            if event_type == "messages" and isinstance(data, list) and len(data) == 2:
                data = (data[0], data[1])
            yield (namespace, event_type, data)

    def get_state(self, config: dict[str, Any] | None = None):
        thread_id = ((config or {}).get("configurable") or {}).get("thread_id")
        if not thread_id:
            return SimpleNamespace(values={})
        state = self._client.threads.get_state(thread_id=thread_id)
        return SimpleNamespace(values=state.get("values") or {}, metadata=state.get("metadata") or {})


def create_remote_coding_agent(
    custom_settings: Settings | None = None,
    *,
    cwd=None,
) -> dict[str, Any]:
    cfg = custom_settings or settings
    if not cfg.langgraph_deployment_url:
        raise RuntimeError(
            "single deployment topology requires LANGGRAPH_DEPLOYMENT_URL to point at a running langgraph deployment."
        )

    runtime = LocalAsyncSubagentManager(
        cfg=cfg,
        root_dir=cwd,
        topology="single",
    )
    fallback = RemoteFallbackStatus()
    agent = RemoteLangGraphAgent(cfg.langgraph_deployment_url, cfg.langgraph_assistant_id)
    return {
        "agent": agent,
        "backend": None,
        "fallback_middleware": fallback,
        "memory_middleware": RemoteMemoryFacade(str(cfg.memory_dir)),
        "subagent_middleware": runtime,
        "subagent_runtime": runtime,
        "subagent_manager": runtime,
        "deployment_topology": "single",
        "async_subagents": runtime.build_async_subagents(),
        "async_task_tracker": AsyncTaskTracker(agent),
        "loop_guard": RemoteLoopGuard(),
        "checkpointer": None,
    }
