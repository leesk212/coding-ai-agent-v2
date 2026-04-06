"""Long-Term Memory Middleware - ChromaDB-backed vector memory.

Extends DeepAgents' MemoryMiddleware pattern with semantic vector search.
Injects relevant memories into the system prompt and provides tools for
the agent to store/search memories.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, NotRequired, TypedDict

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
from langchain.tools import ToolRuntime
from pydantic import BaseModel, Field

from coding_agent.memory.categories import MemoryCategory
from coding_agent.memory.store import LongTermMemory

logger = logging.getLogger(__name__)

LONG_TERM_MEMORY_PROMPT = """<long_term_memory>
{memory_content}
</long_term_memory>

<long_term_memory_guidelines>
You have access to a long-term vector memory system. Use it to:

1. **Store important learnings**: When you discover useful patterns, user preferences,
   domain knowledge, or project-specific context, store it using the `memory_store` tool.

2. **Search past knowledge**: Use `memory_search` to find relevant information from
   previous sessions. This is especially useful for recalling user preferences,
   code patterns, and domain-specific knowledge.

3. **Categories**:
   - `domain_knowledge`: Technical facts, API patterns, best practices
   - `user_preferences`: User's coding style, language preferences, conventions
   - `code_patterns`: Reusable code patterns, common solutions
   - `project_context`: Project structure, architecture decisions, dependencies

4. **When to store**: After learning something new from the user, discovering a pattern,
   or receiving feedback. Store immediately before doing other work.

5. **When to search**: At the start of a new task, when the user asks about past work,
   or when you need context about the project or user preferences.
</long_term_memory_guidelines>
"""


class MemoryStoreInput(BaseModel):
    """Input schema for memory_store tool."""

    content: str = Field(description="The knowledge or information to store")
    category: str = Field(
        description="Category: domain_knowledge, user_preferences, code_patterns, or project_context"
    )
    tags: str = Field(default="", description="Comma-separated tags for the memory")


class MemorySearchInput(BaseModel):
    """Input schema for memory_search tool."""

    query: str = Field(description="Search query to find relevant memories")
    category: str = Field(
        default="",
        description="Optional category filter: domain_knowledge, user_preferences, code_patterns, or project_context",
    )
    n_results: int = Field(default=5, description="Number of results to return")


class LongTermMemoryState(AgentState):
    """State for long-term memory middleware."""

    ltm_relevant_memories: NotRequired[Annotated[list[dict], PrivateStateAttr]]


class LongTermMemoryMiddleware(AgentMiddleware[LongTermMemoryState, ContextT, ResponseT]):
    """Middleware for ChromaDB-backed long-term memory.

    - before_agent: Searches relevant memories based on the latest user message
    - modify_request: Injects relevant memories into the system prompt
    - Provides memory_store and memory_search tools
    """

    state_schema = LongTermMemoryState

    def __init__(self, memory_dir: str = "~/.coding_agent/memory") -> None:
        self._store = LongTermMemory(persist_dir=memory_dir)

    @property
    def store(self) -> LongTermMemory:
        return self._store

    def _get_latest_user_query(self, state: LongTermMemoryState) -> str:
        """Extract the latest user message from state."""
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                return msg.content if isinstance(msg.content, str) else str(msg.content)
        return ""

    def _search_relevant(self, query: str) -> list[dict]:
        """Search all categories for relevant memories."""
        if not query:
            return []
        return self._store.search(query, n_results=5)

    def _format_memories(self, memories: list[dict]) -> str:
        """Format memories for system prompt injection."""
        if not memories:
            return LONG_TERM_MEMORY_PROMPT.format(
                memory_content="(No relevant long-term memories found)"
            )

        sections = []
        for m in memories:
            sections.append(
                f"[{m['category']}] (relevance: {1 - m['distance']:.2f})\n{m['content']}"
            )

        return LONG_TERM_MEMORY_PROMPT.format(
            memory_content="\n\n---\n\n".join(sections)
        )

    def before_agent(self, state, runtime, config):
        """Search for relevant memories before agent execution."""
        query = self._get_latest_user_query(state)
        memories = self._search_relevant(query)
        return {"ltm_relevant_memories": memories}

    async def abefore_agent(self, state, runtime, config):
        """Async version of before_agent."""
        return self.before_agent(state, runtime, config)

    def modify_request(self, request: ModelRequest[ContextT]) -> ModelRequest[ContextT]:
        """Inject relevant memories into the system prompt."""
        memories = request.state.get("ltm_relevant_memories", [])
        memory_text = self._format_memories(memories)

        current_system = request.system_message or ""
        if isinstance(current_system, str):
            new_system = current_system + "\n\n" + memory_text
        else:
            new_system = str(current_system) + "\n\n" + memory_text

        return request.override(system_message=new_system)

    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT]:
        modified = self.modify_request(request)
        return handler(modified)

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], Awaitable[ModelResponse[ResponseT]]],
    ) -> ModelResponse[ResponseT]:
        modified = self.modify_request(request)
        return await handler(modified)

    def get_tools(self) -> list[StructuredTool]:
        """Return memory tools for the agent to use."""
        store = self._store

        def memory_store(content: str, category: str, tags: str = "") -> str:
            """Store knowledge in long-term memory for future recall."""
            try:
                cat = MemoryCategory(category)
            except ValueError:
                return f"Invalid category: {category}. Use: {', '.join(c.value for c in MemoryCategory)}"

            metadata = {}
            if tags:
                metadata["tags"] = tags

            doc_id = store.store(content, cat, metadata)
            return f"Stored in {category} with ID: {doc_id}"

        def memory_search(query: str, category: str = "", n_results: int = 5) -> str:
            """Search long-term memory for relevant knowledge."""
            cat = None
            if category:
                try:
                    cat = MemoryCategory(category)
                except ValueError:
                    return f"Invalid category: {category}"

            results = store.search(query, cat, n_results)
            if not results:
                return "No relevant memories found."

            output = []
            for r in results:
                output.append(
                    f"[{r['category']}] (similarity: {1 - r['distance']:.2f})\n{r['content']}"
                )
            return "\n\n---\n\n".join(output)

        return [
            StructuredTool.from_function(
                func=memory_store,
                name="memory_store",
                description="Store knowledge in long-term memory. Categories: domain_knowledge, user_preferences, code_patterns, project_context",
                args_schema=MemoryStoreInput,
            ),
            StructuredTool.from_function(
                func=memory_search,
                name="memory_search",
                description="Search long-term memory for relevant past knowledge",
                args_schema=MemorySearchInput,
            ),
        ]
