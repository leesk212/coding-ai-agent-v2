"""Long-Term Memory Middleware - ChromaDB-backed vector memory.

Extends DeepAgents' MemoryMiddleware pattern with semantic vector search.
Injects relevant memories into the system prompt and provides tools for
the agent to store/search memories.

Implements DeepAgents AgentMiddleware interface:
  - wrap_model_call: inject relevant memories into system prompt
  - get_tools(): provide memory_store and memory_search tools
"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.tools import tool

from coding_agent.memory.categories import MemoryCategory
from coding_agent.memory.store import LongTermMemory

logger = logging.getLogger(__name__)


MEMORY_CONTEXT_TEMPLATE = """<long_term_memory>
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


class LongTermMemoryMiddleware(AgentMiddleware):
    """Manages long-term memory via ChromaDB.

    Implements the DeepAgents middleware pattern:
    - wrap_model_call: injects relevant memories into the system prompt
    - get_tools(): returns tools for agent use (memory_store, memory_search)

    This is layered on top of DeepAgents' native MemoryMiddleware (AGENTS.md)
    to provide semantic vector search across sessions.
    """

    def __init__(self, memory_dir: str = "~/.coding_agent/memory") -> None:
        self._store = LongTermMemory(persist_dir=memory_dir)

    @property
    def store(self) -> LongTermMemory:
        return self._store

    def get_relevant_context(self, query: str) -> str:
        """Search for relevant memories and format them for system prompt injection."""
        if not query:
            return MEMORY_CONTEXT_TEMPLATE.format(
                memory_content="(No relevant long-term memories found)"
            )

        memories = self._store.search(query, n_results=5)

        if not memories:
            return MEMORY_CONTEXT_TEMPLATE.format(
                memory_content="(No relevant long-term memories found)"
            )

        sections = []
        for m in memories:
            similarity = max(0, 1 - m["distance"])
            sections.append(
                f"[{m['category']}] (relevance: {similarity:.2f})\n{m['content']}"
            )

        return MEMORY_CONTEXT_TEMPLATE.format(
            memory_content="\n\n---\n\n".join(sections)
        )

    def wrap_model_call(self, request, handler):
        """DeepAgents AgentMiddleware interface: inject memories into system prompt.

        Searches for relevant memories based on the latest user message,
        then appends them to the system prompt before the LLM call.
        """
        # Extract latest user query from messages in the request
        query = ""
        messages = getattr(request, "messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                query = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        memory_text = self.get_relevant_context(query)

        # Try to inject into system prompt
        try:
            current_system = getattr(request, "system_message", "") or ""
            new_system = current_system + "\n\n" + memory_text
            modified_request = request.override(system_message=new_system)
            return handler(modified_request)
        except (AttributeError, TypeError):
            # If request doesn't support override, just pass through
            return handler(request)

    async def awrap_model_call(self, request, handler):
        """Async version of wrap_model_call."""
        query = ""
        messages = getattr(request, "messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "human":
                query = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        memory_text = self.get_relevant_context(query)

        try:
            current_system = getattr(request, "system_message", "") or ""
            new_system = current_system + "\n\n" + memory_text
            modified_request = request.override(system_message=new_system)
            return await handler(modified_request)
        except (AttributeError, TypeError):
            return await handler(request)

    def get_tools(self) -> list:
        """Return memory tools for the DeepAgents agent to use."""
        store = self._store

        @tool
        def memory_store(content: str, category: str, tags: str = "") -> str:
            """Store knowledge in long-term memory for future recall.

            Args:
                content: The knowledge or information to store.
                category: One of: domain_knowledge, user_preferences, code_patterns, project_context.
                tags: Optional comma-separated tags for the memory.
            """
            try:
                cat = MemoryCategory(category)
            except ValueError:
                valid = ", ".join(c.value for c in MemoryCategory)
                return f"Invalid category: {category}. Use one of: {valid}"

            metadata = {}
            if tags:
                metadata["tags"] = tags

            doc_id = store.store(content, cat, metadata)
            return f"Stored in {category} with ID: {doc_id}"

        @tool
        def memory_search(query: str, category: str = "", n_results: int = 5) -> str:
            """Search long-term memory for relevant past knowledge.

            Args:
                query: Search query to find relevant memories.
                category: Optional category filter (domain_knowledge, user_preferences, code_patterns, project_context).
                n_results: Number of results to return (default 5).
            """
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
                similarity = max(0, 1 - r["distance"])
                output.append(
                    f"[{r['category']}] (similarity: {similarity:.2f})\n{r['content']}"
                )
            return "\n\n---\n\n".join(output)

        return [memory_store, memory_search]
