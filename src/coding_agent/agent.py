"""Agent assembly - combines DeepAgents core with custom middleware.

This module creates the main agent by extending DeepAgents' create_deep_agent()
with our custom middleware stack:
1. ModelFallbackMiddleware - automatic model fallback with circuit breaker
2. LongTermMemoryMiddleware - ChromaDB vector memory
3. SubAgentLifecycleMiddleware - dynamic sub-agent management
4. Agentic loop defense - iteration guards, stuck detection, error recovery
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from coding_agent.config import Settings, settings
from coding_agent.middleware.long_term_memory import LongTermMemoryMiddleware
from coding_agent.middleware.model_fallback import ModelFallbackMiddleware, _create_model
from coding_agent.middleware.subagent_lifecycle import SubAgentLifecycleMiddleware

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a Coding AI Agent, an advanced AI assistant specialized in software engineering tasks.

## Capabilities
- Read, write, and edit files in the project
- Execute shell commands
- Search the web for documentation and solutions
- Store and recall knowledge from long-term memory
- Spawn specialized sub-agents for complex tasks
- Automatically switch between AI models for reliability

## Working Style
- Be concise and direct
- Read code before modifying it
- Verify your work after making changes
- Use long-term memory to remember user preferences and project context
- Delegate complex sub-tasks to specialized sub-agents when appropriate
- If a task is complex, break it down and use sub-agents for parallel work

## Memory Usage
- Store important learnings (user preferences, code patterns, domain knowledge)
- Search memory before starting tasks to leverage past knowledge
- Update memory when you receive feedback or discover new patterns

## Sub-Agent Usage
- Use `spawn_subagent` for tasks that can be delegated:
  - `code_writer`: Writing new code or functions
  - `researcher`: Investigating codebases, documentation
  - `reviewer`: Code review and quality analysis
  - `debugger`: Root cause analysis and bug fixing
  - `general`: Any other task
"""


class AgentLoopGuard:
    """Defense mechanisms for the agentic loop.

    Prevents infinite loops, stuck states, and handles errors gracefully.
    """

    def __init__(self, max_iterations: int = 25, max_retries: int = 3) -> None:
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.iteration_count = 0
        self.empty_response_count = 0
        self.tool_call_history: list[tuple[str, str]] = []  # (tool_name, args_hash)

    def check_iteration(self) -> str | None:
        """Check if we've exceeded max iterations. Returns warning message or None."""
        self.iteration_count += 1
        if self.iteration_count >= self.max_iterations:
            return (
                f"Reached maximum iterations ({self.max_iterations}). "
                "Stopping to prevent infinite loop. Here's a summary of what was accomplished."
            )
        return None

    def check_empty_response(self, response: str) -> bool:
        """Check for empty/meaningless responses. Returns True if should retry."""
        if not response or not response.strip():
            self.empty_response_count += 1
            if self.empty_response_count >= self.max_retries:
                logger.warning("Max empty responses reached (%d)", self.max_retries)
                return False  # Don't retry anymore
            logger.warning(
                "Empty response detected (attempt %d/%d)",
                self.empty_response_count,
                self.max_retries,
            )
            return True  # Should retry
        self.empty_response_count = 0
        return False

    def check_stuck(self, tool_name: str, args: str) -> str | None:
        """Detect if agent is stuck calling the same tool repeatedly."""
        import hashlib

        args_hash = hashlib.md5(args.encode()).hexdigest()[:8]
        entry = (tool_name, args_hash)

        self.tool_call_history.append(entry)

        # Check last 3 calls
        if len(self.tool_call_history) >= 3:
            last_3 = self.tool_call_history[-3:]
            if len(set(last_3)) == 1:
                self.tool_call_history.clear()
                return (
                    f"WARNING: You've called `{tool_name}` with the same arguments 3 times. "
                    "This suggests you're stuck. Try a different approach."
                )
        return None

    def reset(self) -> None:
        self.iteration_count = 0
        self.empty_response_count = 0
        self.tool_call_history.clear()


def create_coding_agent(
    custom_settings: Settings | None = None,
) -> dict[str, Any]:
    """Create the coding agent with all custom middleware.

    Returns a dict with:
    - agent: The compiled LangGraph agent
    - fallback_middleware: For status monitoring
    - memory_middleware: For memory access
    - subagent_middleware: For sub-agent monitoring
    - loop_guard: For loop defense
    """
    cfg = custom_settings or settings

    # Create primary model (first in priority list)
    primary_model_spec = cfg.model_priority[0] if cfg.model_priority else cfg.local_fallback_model
    primary_model = _create_model(primary_model_spec)

    # Initialize middleware
    fallback_mw = ModelFallbackMiddleware(
        models=cfg.get_all_models(),
        timeout=cfg.model_timeout,
    )

    memory_mw = LongTermMemoryMiddleware(
        memory_dir=str(cfg.memory_dir),
    )

    subagent_mw = SubAgentLifecycleMiddleware(
        model=primary_model,
        max_concurrent=cfg.max_subagents,
    )

    loop_guard = AgentLoopGuard(max_iterations=cfg.max_iterations)

    # Collect custom tools from middleware
    custom_tools = memory_mw.get_tools() + subagent_mw.get_tools()

    # Build middleware stack (order matters!)
    # Custom middleware is inserted AFTER DeepAgents' base stack
    custom_middleware = [
        fallback_mw,
        memory_mw,
        subagent_mw,
    ]

    try:
        from deepagents import create_deep_agent

        agent = create_deep_agent(
            model=primary_model,
            tools=custom_tools,
            system_prompt=SYSTEM_PROMPT,
            middleware=custom_middleware,
        )
    except ImportError:
        logger.warning(
            "DeepAgents not installed. Using standalone LangGraph agent."
        )
        agent = _create_standalone_agent(
            primary_model, custom_tools, custom_middleware
        )

    return {
        "agent": agent,
        "fallback_middleware": fallback_mw,
        "memory_middleware": memory_mw,
        "subagent_middleware": subagent_mw,
        "loop_guard": loop_guard,
    }


def _create_standalone_agent(model, tools, middleware):
    """Fallback: create a basic LangGraph agent without DeepAgents dependency."""
    from langgraph.graph import END, StateGraph
    from langgraph.graph.message import add_messages
    from typing import Annotated, TypedDict

    class State(TypedDict):
        messages: Annotated[list, add_messages]

    def call_model(state: State) -> dict:
        messages = state["messages"]
        response = model.bind_tools(tools).invoke(messages)
        return {"messages": [response]}

    def should_continue(state: State) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"

    def execute_tools(state: State) -> dict:
        from langchain_core.messages import ToolMessage

        last = state["messages"][-1]
        results = []
        tool_map = {t.name: t for t in tools}
        for tc in last.tool_calls:
            tool = tool_map.get(tc["name"])
            if tool:
                try:
                    result = tool.invoke(tc["args"])
                except Exception as e:
                    result = f"Error: {e}"
            else:
                result = f"Unknown tool: {tc['name']}"
            results.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        return {"messages": results}

    graph = StateGraph(State)
    graph.add_node("agent", call_model)
    graph.add_node("tools", execute_tools)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    return graph.compile()
