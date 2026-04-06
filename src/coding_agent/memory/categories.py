"""Memory category definitions."""

from enum import Enum


class MemoryCategory(str, Enum):
    """Categories for organizing long-term memories."""

    DOMAIN_KNOWLEDGE = "domain_knowledge"
    USER_PREFERENCES = "user_preferences"
    CODE_PATTERNS = "code_patterns"
    PROJECT_CONTEXT = "project_context"
