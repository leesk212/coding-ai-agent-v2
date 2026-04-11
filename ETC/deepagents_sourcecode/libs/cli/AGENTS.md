<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# deepagents-cli

## Purpose
`libs/cli` packages the Deep Agents terminal application: the shipped `deepagents_cli` Python package, developer scripts, example skills, screenshots, and the full test suite. This directory is the package root for publishing, local development, and documentation of the CLI-specific architecture.

## Key Files

| File | Description |
|------|-------------|
| `README.md` | Public package overview, installation instructions, and resource links. |
| `ARCHITECTURE.md` | Maintainer-facing architecture map for the CLI runtime, subsystems, and execution flows. |
| `DEV.md` | Development notes for live Textual CSS iteration and local UI debugging. |
| `THREAT_MODEL.md` | Security-oriented boundary and data-flow analysis for the CLI package. |
| `pyproject.toml` | Package metadata, dependencies, scripts, and lint/type/test configuration. |
| `Makefile` | Canonical lint, test, type-check, benchmark, and helper commands. |
| `uv.lock` | Locked dependency graph for reproducible local and CI environments. |
| `COMMENTING_GUIDE.ko.md` | Korean companion guide explaining the recent code-commenting pass. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `deepagents_cli/` | Shipped Python package implementing the CLI runtime (see `deepagents_cli/AGENTS.md`). |
| `tests/` | Unit and integration test suites for the package (see `tests/AGENTS.md`). |
| `examples/` | Example skills and reference material that demonstrate extension patterns (see `examples/AGENTS.md`). |
| `scripts/` | Developer and installer scripts used outside the packaged runtime (see `scripts/AGENTS.md`). |
| `images/` | Screenshot assets used in package documentation (see `images/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Treat `deepagents_cli/` as the shipped product and keep documentation/tests aligned with behavioral changes there.
- Ignore generated state such as `.venv/`, `.pytest_cache/`, `.ruff_cache/`, and `.benchmarks/` unless a task is explicitly about tooling output.
- Preserve CLI surface area described in `README.md` and `pyproject.toml` unless the task explicitly calls for a breaking change.

### Testing Requirements
- Package code changes: `make lint_package` and targeted `uv run --group test pytest ...`.
- Cross-cutting CLI changes: `uv run --group test pytest tests/unit_tests`.
- Script-only or docs-only changes usually need a lightweight sanity check rather than the full suite.

### Common Patterns
- Startup-sensitive modules rely on deferred imports to keep `--help` and `--version` fast.
- Interactive and headless modes share the same agent/server boundary and much of the same backend wiring.
- Tests mirror source layout closely, so new runtime modules should usually gain corresponding unit tests.

## Dependencies

### Internal
- `../deepagents/` provides the SDK and core agent/backends used by the CLI package.
- `tests/` validates the runtime behavior described by `deepagents_cli/`.

### External
- `textual`, `rich`, and `prompt-toolkit` drive the terminal UI.
- `langchain`, `langgraph`, and `langgraph-sdk` power the agent runtime and local dev server.
- `ruff`, `ty`, and `pytest` are the primary local quality gates.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
