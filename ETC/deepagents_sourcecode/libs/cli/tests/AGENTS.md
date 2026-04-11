<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# tests

## Purpose
`tests/` contains the verification surface for `deepagents-cli`, split into deterministic unit tests and broader integration/benchmark coverage. The structure mirrors the runtime package so maintainers can quickly map behavior changes to their validation targets.

## Key Files

| File | Description |
|------|-------------|
| `README.md` | Notes about credentials required for selected integration test runs. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `unit_tests/` | Fast, heavily mocked tests that mirror most runtime modules and widgets (see `unit_tests/AGENTS.md`). |
| `integration_tests/` | Higher-level tests covering ACP mode, sandbox behavior, and performance guards (see `integration_tests/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Keep tests close to the runtime module or workflow they protect.
- Favor deterministic fixtures and narrow targeted runs before resorting to the entire suite.

### Testing Requirements
- Unit changes: run the relevant slice under `tests/unit_tests/`.
- Sandbox, ACP, or startup-performance changes may require the matching integration or benchmark tests.

### Common Patterns
- Unit tests rely on pytest, mocks, `responses`, and Textual’s test harness.
- Integration tests often use subprocesses or real backend boundaries.

## Dependencies

### Internal
- Exercises `deepagents_cli/` and documents expected behavior for its public/runtime surface.

### External
- Uses pytest plugins configured in `pyproject.toml`; some integration tests require API keys or optional providers.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
