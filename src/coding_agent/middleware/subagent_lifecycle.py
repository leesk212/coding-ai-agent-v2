"""Dynamic SubAgent Lifecycle Middleware.

Extends DeepAgents' SubAgentMiddleware to support runtime creation,
execution, and destruction of sub-agents with explicit state tracking.

Sub-agents are created dynamically based on task requirements rather than
pre-defined in AGENTS.md files.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    PrivateStateAttr,
    ResponseT,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── SubAgent status lifecycle ──────────────────────────────────────────

class SubAgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── SubAgent type templates ────────────────────────────────────────────

SUBAGENT_TEMPLATES = {
    "code_writer": {
        "system_prompt": (
            "You are a code writing specialist. Write clean, efficient, well-tested code. "
            "Follow the existing code style and patterns in the project. "
            "Always explain your design decisions briefly."
        ),
    },
    "researcher": {
        "system_prompt": (
            "You are a research specialist. Thoroughly investigate the topic, "
            "search through files, documentation, and code to gather comprehensive information. "
            "Provide structured findings with sources."
        ),
    },
    "reviewer": {
        "system_prompt": (
            "You are a code review specialist. Review code for bugs, security issues, "
            "performance problems, and style violations. Provide specific, actionable feedback "
            "with line references."
        ),
    },
    "debugger": {
        "system_prompt": (
            "You are a debugging specialist. Systematically identify the root cause of issues. "
            "Read error messages carefully, trace execution flow, check edge cases, "
            "and propose targeted fixes."
        ),
    },
    "general": {
        "system_prompt": (
            "You are a general-purpose assistant. Help with any coding task as needed. "
            "Be thorough and precise."
        ),
    },
}


# ── SubAgent task data ─────────────────────────────────────────────────

@dataclass
class SubAgentTask:
    """Represents a dynamically created sub-agent task."""

    id: str
    task_description: str
    agent_type: str
    status: SubAgentStatus
    result: str | None = None
    error: str | None = None
    model_used: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    @classmethod
    def create(cls, task_description: str, agent_type: str = "general") -> SubAgentTask:
        return cls(
            id=uuid.uuid4().hex[:8],
            task_description=task_description,
            agent_type=agent_type,
            status=SubAgentStatus.PENDING,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_description": self.task_description,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "model_used": self.model_used,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


# ── SubAgent Registry ──────────────────────────────────────────────────

class SubAgentRegistry:
    """Registry for tracking active sub-agents and their lifecycle."""

    def __init__(self, max_concurrent: int = 3) -> None:
        self.tasks: dict[str, SubAgentTask] = {}
        self.history: list[SubAgentTask] = []  # completed/failed tasks
        self.max_concurrent = max_concurrent

    def spawn(self, description: str, agent_type: str = "general") -> SubAgentTask:
        """Create and register a new sub-agent task."""
        active = sum(
            1 for t in self.tasks.values()
            if t.status in (SubAgentStatus.PENDING, SubAgentStatus.RUNNING)
        )
        if active >= self.max_concurrent:
            raise RuntimeError(
                f"Max concurrent sub-agents ({self.max_concurrent}) reached. "
                f"Wait for active tasks to complete."
            )

        if agent_type not in SUBAGENT_TEMPLATES:
            agent_type = "general"

        task = SubAgentTask.create(description, agent_type)
        self.tasks[task.id] = task
        logger.info("Spawned sub-agent [%s] type=%s: %s", task.id, agent_type, description[:80])
        return task

    def start(self, task_id: str) -> None:
        self.tasks[task_id].status = SubAgentStatus.RUNNING

    def complete(self, task_id: str, result: str, model_used: str | None = None) -> None:
        task = self.tasks[task_id]
        task.status = SubAgentStatus.COMPLETED
        task.result = result
        task.model_used = model_used
        task.completed_at = time.time()
        logger.info("Sub-agent [%s] completed in %.1fs", task_id, task.completed_at - task.created_at)

    def fail(self, task_id: str, error: str) -> None:
        task = self.tasks[task_id]
        task.status = SubAgentStatus.FAILED
        task.error = error
        task.completed_at = time.time()
        logger.warning("Sub-agent [%s] failed: %s", task_id, error)

    def cleanup(self) -> list[SubAgentTask]:
        """Move completed/failed tasks to history and remove from active."""
        done = [
            t for t in self.tasks.values()
            if t.status in (SubAgentStatus.COMPLETED, SubAgentStatus.FAILED)
        ]
        for t in done:
            self.history.append(t)
            del self.tasks[t.id]
        return done

    def get_active_summary(self) -> str:
        """Summary of active sub-agents for system prompt injection."""
        active = [t for t in self.tasks.values() if t.status in (SubAgentStatus.PENDING, SubAgentStatus.RUNNING)]
        if not active:
            return "(no active sub-agents)"
        lines = []
        for t in active:
            elapsed = time.time() - t.created_at
            lines.append(f"[{t.id}] {t.status.value} ({t.agent_type}, {elapsed:.0f}s): {t.task_description[:80]}")
        return "\n".join(lines)

    def get_all_tasks(self) -> list[dict]:
        """Get all tasks (active + history) as dicts."""
        all_tasks = list(self.tasks.values()) + self.history
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in all_tasks]


# ── Tool schemas ───────────────────────────────────────────────────────

class SpawnSubAgentInput(BaseModel):
    task_description: str = Field(description="Detailed description of the task for the sub-agent")
    agent_type: str = Field(
        default="general",
        description="Type of sub-agent: code_writer, researcher, reviewer, debugger, or general",
    )


class ListSubAgentsInput(BaseModel):
    pass


# ── SubAgent State ─────────────────────────────────────────────────────

class SubAgentLifecycleState(AgentState):
    active_subagents_summary: NotRequired[str]


# ── Middleware ──────────────────────────────────────────────────────────

class SubAgentLifecycleMiddleware(AgentMiddleware[SubAgentLifecycleState, ContextT, ResponseT]):
    """Middleware for dynamic sub-agent lifecycle management.

    Provides tools:
    - spawn_subagent: Create a new sub-agent dynamically
    - list_subagents: View active and historical sub-agents

    Sub-agents execute using the DeepAgents create_deep_agent infrastructure
    but are created at runtime rather than pre-defined.
    """

    state_schema = SubAgentLifecycleState

    def __init__(
        self,
        model: BaseChatModel | None = None,
        max_concurrent: int = 3,
    ) -> None:
        self.registry = SubAgentRegistry(max_concurrent=max_concurrent)
        self._model = model

    def modify_request(self, request: ModelRequest[ContextT]) -> ModelRequest[ContextT]:
        """Inject active sub-agent summary into system prompt."""
        summary = self.registry.get_active_summary()
        if summary == "(no active sub-agents)":
            return request

        injection = f"\n\n<active_subagents>\n{summary}\n</active_subagents>"
        current_system = request.system_message or ""
        if isinstance(current_system, str):
            new_system = current_system + injection
        else:
            new_system = str(current_system) + injection

        return request.override(system_message=new_system)

    def _execute_subagent(self, task: SubAgentTask) -> str:
        """Execute a sub-agent task synchronously.

        Uses the model to process the task with the appropriate system prompt.
        """
        if self._model is None:
            return "Error: No model configured for sub-agent execution"

        self.registry.start(task.id)

        template = SUBAGENT_TEMPLATES.get(task.agent_type, SUBAGENT_TEMPLATES["general"])
        system_prompt = template["system_prompt"]

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task.task_description},
            ]
            response = self._model.invoke(messages)
            result = response.content if isinstance(response.content, str) else str(response.content)
            self.registry.complete(task.id, result)
            return result
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            self.registry.fail(task.id, error)
            return f"Sub-agent failed: {error}"

    async def _aexecute_subagent(self, task: SubAgentTask) -> str:
        """Execute a sub-agent task asynchronously."""
        if self._model is None:
            return "Error: No model configured for sub-agent execution"

        self.registry.start(task.id)

        template = SUBAGENT_TEMPLATES.get(task.agent_type, SUBAGENT_TEMPLATES["general"])
        system_prompt = template["system_prompt"]

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task.task_description},
            ]
            response = await self._model.ainvoke(messages)
            result = response.content if isinstance(response.content, str) else str(response.content)
            self.registry.complete(task.id, result)
            return result
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            self.registry.fail(task.id, error)
            return f"Sub-agent failed: {error}"

    def get_tools(self) -> list[StructuredTool]:
        """Return sub-agent management tools."""
        middleware = self

        def spawn_subagent(task_description: str, agent_type: str = "general") -> str:
            """Spawn a new sub-agent to handle a specific task.

            Types: code_writer, researcher, reviewer, debugger, general
            """
            try:
                task = middleware.registry.spawn(task_description, agent_type)
                result = middleware._execute_subagent(task)

                # Auto-cleanup completed tasks
                middleware.registry.cleanup()

                return f"[Sub-agent {task.id} ({agent_type})] Result:\n{result}"
            except RuntimeError as e:
                return str(e)

        def list_subagents() -> str:
            """List all sub-agents (active and historical)."""
            tasks = middleware.registry.get_all_tasks()
            if not tasks:
                return "No sub-agents have been created yet."

            lines = []
            for t in tasks:
                status = t["status"]
                elapsed = ""
                if t["completed_at"]:
                    elapsed = f" ({t['completed_at'] - t['created_at']:.1f}s)"
                lines.append(
                    f"[{t['id']}] {status}{elapsed} ({t['agent_type']}): "
                    f"{t['task_description'][:80]}"
                )
                if t.get("error"):
                    lines.append(f"  Error: {t['error']}")
            return "\n".join(lines)

        return [
            StructuredTool.from_function(
                func=spawn_subagent,
                name="spawn_subagent",
                description="Spawn a dynamic sub-agent to handle a specific task. Types: code_writer, researcher, reviewer, debugger, general",
                args_schema=SpawnSubAgentInput,
            ),
            StructuredTool.from_function(
                func=list_subagents,
                name="list_subagents",
                description="List all sub-agents with their status and results",
                args_schema=ListSubAgentsInput,
            ),
        ]
