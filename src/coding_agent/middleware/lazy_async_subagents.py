"""Lazy startup middleware for split-topology async subagents."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from coding_agent.async_subagent_manager import LocalAsyncSubagentManager


class LazyAsyncSubagentsMiddleware(AgentMiddleware):
    """Start a split-topology subagent runtime only when `start_async_task` is used."""

    def __init__(self, runtime: LocalAsyncSubagentManager) -> None:
        super().__init__()
        self._runtime = runtime

    def _maybe_start(self, request: ToolCallRequest) -> ToolMessage | None:
        tool_call = request.tool_call
        if tool_call.get("name") != "start_async_task":
            return None

        args = tool_call.get("args") or {}
        if not isinstance(args, dict):
            return None

        subagent_type = str(args.get("subagent_type", "")).strip()
        if not subagent_type:
            return None

        if self._runtime.topology != "split":
            return None

        task_summary = str(args.get("description", "") or "").strip()
        root_dir = str(self._runtime.root_dir)
        if task_summary:
            args["description"] = (
                f"{task_summary}\n\n"
                "Runtime context:\n"
                f"- Working directory: {root_dir}\n"
                f"- Use absolute paths rooted under {root_dir}\n"
                "- If you create or review files, inspect this directory first.\n"
            )
            task_summary = str(args["description"])
        self._runtime.begin_task(subagent_type, task_summary or "(no task summary)")
        try:
            self._runtime.ensure_started(subagent_type)
            self._runtime.note_runtime_state(
                subagent_type,
                state="running",
                task_summary=task_summary,
            )
        except Exception as exc:  # noqa: BLE001
            self._runtime.note_runtime_state(
                subagent_type,
                state="failed",
                task_summary=task_summary,
                error=str(exc),
            )
            return ToolMessage(
                content=f"Failed to prepare async subagent `{subagent_type}`: {exc}",
                name="start_async_task",
                tool_call_id=tool_call["id"],
                status="error",
            )
        return None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        if (error := self._maybe_start(request)) is not None:
            return error
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        if (error := self._maybe_start(request)) is not None:
            return error
        return await handler(request)
