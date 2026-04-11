"""Version constants and import-safe metadata for `deepagents-cli`.

Keep this module dependency-free so version checks, help screens, and update
logic can import it without triggering the heavier CLI runtime.
"""

__version__ = "0.0.34"  # x-release-please-version

DOCS_URL = "https://docs.langchain.com/oss/python/deepagents/cli"
"""URL for `deepagents-cli` documentation."""

PYPI_URL = "https://pypi.org/pypi/deepagents-cli/json"
"""PyPI JSON API endpoint for version checks."""

CHANGELOG_URL = (
    "https://github.com/langchain-ai/deepagents/blob/main/libs/cli/CHANGELOG.md"
)
"""URL for the full changelog."""

USER_AGENT = f"deepagents-cli/{__version__} update-check"
"""User-Agent header sent with PyPI requests."""
