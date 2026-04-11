<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# skills

## Purpose
This directory contains unit tests for CLI skill management, covering skill discovery, skill metadata validation, JSON output, and command behavior.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Package marker for skill-related unit tests. |
| `test_commands.py` | Validates skill CLI commands, naming rules, template generation, and path safety. |
| `test_load.py` | Covers filesystem skill discovery and content loading. |
| `test_skills_json.py` | Verifies JSON-facing skill command output. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Keep tests aligned with the current skill specification and precedence rules.
- Cover both success paths and invalid-name/path rejection behavior when changing commands or loaders.

### Testing Requirements
- Run `uv run --group test pytest tests/unit_tests/skills`.

### Common Patterns
- Uses temp directories and mocked consoles to avoid touching real user skill folders.

## Dependencies

### Internal
- Primarily covers `deepagents_cli/skills/commands.py` and `deepagents_cli/skills/load.py`.

### External
- Uses pytest, rich console helpers, and Deep Agents skill metadata utilities.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
