"""Helpers for preserving LangChain SystemMessage shape in middleware."""

from __future__ import annotations

from langchain_core.messages import SystemMessage


def append_system_message(current_system, appended_text: str):
    """Append text while preserving rich SystemMessage objects when possible."""
    base_text = ""
    if isinstance(current_system, SystemMessage):
        content = current_system.content
        if isinstance(content, str):
            base_text = content
        elif isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
            base_text = "".join(parts)
        else:
            base_text = str(content)
        return SystemMessage(content=f"{base_text}\n\n{appended_text}".strip())

    base_text = str(current_system or "")
    return f"{base_text}\n\n{appended_text}".strip()
