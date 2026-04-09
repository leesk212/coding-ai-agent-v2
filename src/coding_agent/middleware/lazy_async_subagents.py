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

        try:
            self._runtime.ensure_started(subagent_type)
        except Exception as exc:  # noqa: BLE001
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
