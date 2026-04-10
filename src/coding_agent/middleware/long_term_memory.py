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
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.tools import tool

from coding_agent.memory.categories import MemoryCategory
from coding_agent.memory.store import LongTermMemory
from coding_agent.middleware._system_message import append_system_message
from coding_agent.state.store import DurableStateStore

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

3a. **Required extraction behavior**:
   - Extract durable memory from user instructions when it is likely to matter in later turns.
   - Map extracted memory into one of the three long-term layers used by this project:
     - `user/profile`
     - `project/context`
     - `domain/knowledge`
   - Do not confuse transient thread history with long-term memory.
   - If the user gives a new rule, preference, or domain fact that should persist, store it during the same turn.

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
        self._state_store = DurableStateStore(Path(memory_dir).expanduser().parent / "state" / "agent_state.db")

    @staticmethod
    def _layer_from_category(category: MemoryCategory) -> str:
        mapping = {
            MemoryCategory.USER_PREFERENCES: "user/profile",
            MemoryCategory.PROJECT_CONTEXT: "project/context",
            MemoryCategory.DOMAIN_KNOWLEDGE: "domain/knowledge",
            MemoryCategory.CODE_PATTERNS: "project/context",
        }
        return mapping[category]

    @staticmethod
    def _category_from_name(name: str) -> MemoryCategory:
        aliases = {
            "user/profile": MemoryCategory.USER_PREFERENCES,
            "user_preferences": MemoryCategory.USER_PREFERENCES,
            "project/context": MemoryCategory.PROJECT_CONTEXT,
            "project_context": MemoryCategory.PROJECT_CONTEXT,
            "domain/knowledge": MemoryCategory.DOMAIN_KNOWLEDGE,
            "domain_knowledge": MemoryCategory.DOMAIN_KNOWLEDGE,
            "code_patterns": MemoryCategory.CODE_PATTERNS,
        }
        try:
            return aliases[name]
        except KeyError as exc:
            valid = ", ".join(sorted(aliases))
            raise ValueError(f"Invalid category: {name}. Use one of: {valid}") from exc

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
        layered = self._state_store.search_memory(query, limit=5)

        if not memories and not layered:
            return MEMORY_CONTEXT_TEMPLATE.format(
                memory_content="(No relevant long-term memories found)"
            )

        sections = []
        for row in layered:
            sections.append(f"[{row['layer']}] (durable)\n{row['content']}")
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
            new_system = append_system_message(current_system, memory_text)
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
            new_system = append_system_message(current_system, memory_text)
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
                cat = self._category_from_name(category)
            except ValueError as exc:
                return str(exc)

            metadata = {}
            if tags:
                metadata["tags"] = tags

            doc_id = store.store(content, cat, metadata)
            state_id = self._state_store.store_memory(
                layer=self._layer_from_category(cat),
                content=content,
                source="memory_store_tool",
                tags=[t.strip() for t in tags.split(",") if t.strip()],
            )
            return f"Stored in {category} with vector ID: {doc_id} and durable ID: {state_id}"

        @tool
        def memory_correct(record_id: str, replacement_content: str, category: str, reason: str = "") -> str:
            """Correct a previously stored long-term memory record."""
            existing = self._state_store.get_memory_record(record_id)
            if not existing:
                return f"Memory record not found: {record_id}"
            try:
                cat = self._category_from_name(category)
            except ValueError as exc:
                return str(exc)
            corrected_id = self._state_store.store_memory(
                layer=self._layer_from_category(cat),
                content=replacement_content,
                source="memory_correct_tool",
                correction_of=record_id,
                tags=[reason] if reason else [],
            )
            store.store(
                replacement_content,
                cat,
                {"corrects": record_id, "reason": reason} if reason else {"corrects": record_id},
            )
            return f"Corrected {record_id} with new durable ID: {corrected_id}"

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
                    cat = self._category_from_name(category)
                except ValueError as exc:
                    return str(exc)

            results = store.search(query, cat, n_results)
            layered = self._state_store.search_memory(
                query,
                layer=self._layer_from_category(cat) if cat else None,
                limit=n_results,
            )
            if not results:
                if not layered:
                    return "No relevant memories found."

            output = []
            for row in layered:
                output.append(f"[{row['layer']}] (durable)\n{row['content']}")
            for r in results:
                similarity = max(0, 1 - r["distance"])
                output.append(
                    f"[{r['category']}] (similarity: {similarity:.2f})\n{r['content']}"
                )
            return "\n\n---\n\n".join(output)

        return [memory_store, memory_correct, memory_search]
