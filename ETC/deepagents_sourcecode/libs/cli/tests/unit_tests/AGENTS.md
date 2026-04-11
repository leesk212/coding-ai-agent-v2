<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# unit_tests

## Purpose
`unit_tests/` is the main verification bed for `deepagents-cli`. It mirrors the source package closely and provides fast, targeted feedback for runtime modules, widgets, parsers, configuration logic, and helper utilities.

## Key Files

| File | Description |
|------|-------------|
| `conftest.py` | Shared fixtures and pytest configuration for unit-level coverage. |
| `test_app.py` | Large Textual app behavior suite covering command handling, focus, modals, and message queueing. |
| `test_textual_adapter.py` | Stream adapter and session-stat behavior coverage. |
| `test_config.py` | Configuration, model bootstrap, and shell-allow logic coverage. |
| `test_model_config.py` | Saved model preference and provider-profile persistence coverage. |
| `test_sessions.py` | Thread/session database and formatting helper coverage. |
| `test_main.py` | CLI startup, argument, and mode dispatch coverage. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `skills/` | Tests for the skill loader and skill-management commands (see `skills/AGENTS.md`). |
| `tools/` | Tests for standalone tool helpers such as `fetch_url` (see `tools/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Add or update the narrowest test file that matches the runtime module you changed.
- Keep tests deterministic; prefer fixtures, mocks, and fake models over real network/provider calls.

### Testing Requirements
- Run the specific file(s) you touched first, then expand to `uv run --group test pytest tests/unit_tests` for broader confidence.

### Common Patterns
- Test modules usually mirror source filenames exactly.
- Textual-heavy tests use `run_test()`/pilot flows, while utility tests lean on mocks, `responses`, and temp paths.

## Dependencies

### Internal
- Covers almost every module inside `deepagents_cli/`.

### External
- Depends on pytest and its configured plugins, including Textual test helpers and `responses`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
