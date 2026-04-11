<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# benchmarks

## Purpose
This directory contains performance guardrails for the CLI, especially around cold-start imports and startup latency. These tests exist to prevent seemingly harmless imports from regressing the user-visible startup experience.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Package marker for benchmark tests. |
| `test_codspeed_import_benchmarks.py` | CodSpeed-focused import benchmark coverage. |
| `test_startup_benchmarks.py` | Cold-start subprocess benchmarks for import and startup fast paths. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Treat startup thresholds and import-isolation assertions as product requirements, not incidental test details.
- If a benchmark fails after a runtime change, look for newly eager imports first.

### Testing Requirements
- Run `uv run --group test pytest tests/integration_tests/benchmarks -m benchmark` or `make benchmark`.

### Common Patterns
- Benchmarks spawn fresh subprocesses so `sys.modules` starts empty on every measurement.

## Dependencies

### Internal
- Protects import behavior in `deepagents_cli/main.py`, `config.py`, and other startup-sensitive modules.

### External
- Relies on pytest benchmark tooling and optional CodSpeed integration.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
