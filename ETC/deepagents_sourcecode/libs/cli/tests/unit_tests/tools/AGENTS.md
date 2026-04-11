<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# tools

## Purpose
This directory holds focused unit tests for standalone tool helpers exposed by the CLI package.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Package marker for tool-specific tests. |
| `test_fetch_url.py` | Verifies URL fetching, HTML-to-markdown conversion, and request error handling. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Keep tests narrowly scoped to tool contracts and returned payload structure.
- Prefer mocked HTTP responses over real network access.

### Testing Requirements
- Run `uv run --group test pytest tests/unit_tests/tools/test_fetch_url.py`.

### Common Patterns
- `responses` is used to intercept HTTP requests and make behavior deterministic.

## Dependencies

### Internal
- Covers helpers in `deepagents_cli/tools.py`.

### External
- Depends on `responses` and `requests` test utilities.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
