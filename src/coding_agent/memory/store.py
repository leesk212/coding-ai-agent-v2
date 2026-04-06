"""ChromaDB-backed vector store for long-term memory."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings as ChromaSettings

from coding_agent.memory.categories import MemoryCategory

logger = logging.getLogger(__name__)


class LongTermMemory:
    """ChromaDB-backed vector store for persistent memory.

    Uses ChromaDB's built-in embedding (all-MiniLM-L6-v2) for semantic search.
    One collection per memory category for clean separation.
    """

    def __init__(self, persist_dir: str = "~/.coding_agent/memory") -> None:
        persist_path = os.path.expanduser(persist_dir)
        os.makedirs(persist_path, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collections = {
            cat: self.client.get_or_create_collection(
                name=cat.value,
                metadata={"hnsw:space": "cosine"},
            )
            for cat in MemoryCategory
        }
        logger.info("LongTermMemory initialized at %s", persist_path)

    def store(
        self,
        content: str,
        category: MemoryCategory,
        metadata: dict | None = None,
    ) -> str:
        """Store a memory entry with auto-generated embedding.

        Returns the document ID.
        """
        collection = self.collections[category]
        doc_id = f"{category.value}_{uuid.uuid4().hex[:12]}"
        meta = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id],
        )
        logger.debug("Stored memory [%s]: %s...", category.value, content[:80])
        return doc_id

    def search(
        self,
        query: str,
        category: MemoryCategory | None = None,
        n_results: int = 5,
    ) -> list[dict]:
        """Semantic search across one or all categories.

        Returns list of dicts with content, category, metadata, distance.
        """
        results = []
        targets = [category] if category else list(MemoryCategory)

        for cat in targets:
            collection = self.collections[cat]
            if collection.count() == 0:
                continue
            hits = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count()),
            )
            for doc, meta, dist in zip(
                hits["documents"][0],
                hits["metadatas"][0],
                hits["distances"][0],
                strict=True,
            ):
                results.append({
                    "content": doc,
                    "category": cat.value,
                    "metadata": meta,
                    "distance": dist,
                })

        results.sort(key=lambda x: x["distance"])
        return results[:n_results]

    def get_all(self, category: MemoryCategory) -> list[dict]:
        """Retrieve all entries for a category."""
        collection = self.collections[category]
        result = collection.get()
        entries = []
        if result["documents"]:
            for doc, meta, doc_id in zip(
                result["documents"],
                result["metadatas"],
                result["ids"],
                strict=True,
            ):
                entries.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                })
        return entries

    def delete(self, doc_id: str, category: MemoryCategory) -> bool:
        """Delete a memory entry by ID."""
        try:
            self.collections[category].delete(ids=[doc_id])
            return True
        except Exception:
            logger.exception("Failed to delete memory %s", doc_id)
            return False

    def get_stats(self) -> dict[str, int]:
        """Get count of entries per category."""
        return {
            cat.value: self.collections[cat].count()
            for cat in MemoryCategory
        }
