"""Middleware to enforce async-only subagent delegation."""

from __future__ import annotations

from langchain.agents.middleware.types import AgentMiddleware


class AsyncOnlySubagentsMiddleware(AgentMiddleware):
    """Remove DeepAgents' synchronous `task` tool from the visible tool list."""

    BLOCKED_TOOL_NAMES = {"task", "spawn_subagent", "list_subagents"}

    def _filter_request_tools(self, request):
        tools = getattr(request, "tools", None)
        if not tools:
            return request
        filtered = [tool for tool in tools if getattr(tool, "name", "") not in self.BLOCKED_TOOL_NAMES]
        try:
            return request.override(tools=filtered)
        except (AttributeError, TypeError):
            return request

    def wrap_model_call(self, request, handler):
        return handler(self._filter_request_tools(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._filter_request_tools(request))
