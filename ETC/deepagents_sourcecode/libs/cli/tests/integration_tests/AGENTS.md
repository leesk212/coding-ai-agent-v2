<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# integration_tests

## Purpose
This directory verifies CLI behavior that crosses real process or provider boundaries: ACP mode, sandbox operations, resume behavior, and cold-start characteristics that are difficult to validate with pure unit tests alone.

## Key Files

| File | Description |
|------|-------------|
| `conftest.py` | Shared fixtures and setup for integration scenarios. |
| `test_acp_mode.py` | End-to-end smoke test for ACP server mode and client session startup. |
| `test_compact_resume.py` | Integration coverage for resume/compact thread behavior. |
| `test_sandbox_factory.py` | Higher-level sandbox factory behavior across supported providers. |
| `test_sandbox_operations.py` | File-operation integration tests against a real sandbox backend. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `benchmarks/` | Startup and import-performance benchmark tests (see `benchmarks/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Preserve test determinism where possible, but accept that these tests intentionally cross process/network/provider boundaries.
- Document any new credential or environment prerequisites in `tests/README.md`.

### Testing Requirements
- Run only the affected integration slice, for example `uv run --group test pytest tests/integration_tests/test_acp_mode.py`.
- Sandbox tests may require external services or API keys; do not silently assume they run everywhere.

### Common Patterns
- Uses subprocess startup, real protocol handshakes, and backend fixtures rather than deep mocking.

## Dependencies

### Internal
- Exercises `main.py`, `server_manager.py`, `remote_client.py`, and integration-layer code.

### External
- ACP SDK, optional sandbox providers, and environment-provided API keys.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
