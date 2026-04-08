"""Middleware that biases the supervisor to complete async tasks in-turn."""

from __future__ import annotations

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage


COMPLETION_POLICY_PROMPT = """
## Async Task Completion Policy (project override)

Default behavior for this product is "complete within the same user turn".

When a user asks for a final answer now:
1. You may launch async subagent tasks with `start_async_task`.
2. Then you should actively collect results in the same turn using `check_async_task`.
3. Synthesize collected outputs before you send the final answer.

Only stop after launch if the user explicitly asks for background execution
or asks to check later.

Do not rely on stale task statuses from memory. Always check live status using tools.
"""


class AsyncTaskCompletionMiddleware(AgentMiddleware):
    """Append completion-first async task guidance to the system prompt."""

    def _inject_policy(self, request):
        current_system = getattr(request, "system_message", None)
        if isinstance(current_system, SystemMessage):
            existing_blocks = list(current_system.content_blocks)
            if existing_blocks:
                text = f"\n\n{COMPLETION_POLICY_PROMPT}"
            else:
                text = COMPLETION_POLICY_PROMPT
            new_system = SystemMessage(
                content_blocks=[*existing_blocks, {"type": "text", "text": text}]
            )
        else:
            current_text = str(current_system or "").strip()
            if current_text:
                combined = f"{current_text}\n\n{COMPLETION_POLICY_PROMPT}"
            else:
                combined = COMPLETION_POLICY_PROMPT
            new_system = SystemMessage(content_blocks=[{"type": "text", "text": combined}])
        try:
            return request.override(system_message=new_system)
        except (AttributeError, TypeError):
            return request

    def wrap_model_call(self, request, handler):
        return handler(self._inject_policy(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._inject_policy(request))
