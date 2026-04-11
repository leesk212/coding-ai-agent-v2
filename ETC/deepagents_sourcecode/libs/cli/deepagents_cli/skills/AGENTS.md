<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# skills

## Purpose
This directory contains the CLI-side skill management layer: argument parsing hooks, filesystem-backed skill discovery, and command implementations such as list/create/info/delete/validate.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Exposes skill parser setup helpers to the main CLI entrypoint. |
| `commands.py` | Implements skill-management subcommands and template generation helpers. |
| `load.py` | Lists available skills across precedence layers and safely reads `SKILL.md` content. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Preserve skill precedence rules and path-safety guarantees when touching loaders or commands.
- Keep template generation, validation, and CLI help text aligned with the skill specification.

### Testing Requirements
- Run `uv run --group test pytest tests/unit_tests/skills/test_commands.py tests/unit_tests/skills/test_load.py tests/unit_tests/skills/test_skills_json.py`.

### Common Patterns
- User and project skill paths are merged with explicit precedence.
- Command handlers are thin CLI-facing wrappers around reusable validation/loading helpers.

## Dependencies

### Internal
- `main.py` wires these commands into the top-level parser.
- `built_in_skills/` provides one of the sources consumed by `load.py`.

### External
- `deepagents.middleware.skills` supplies the base metadata types and backend listing behavior.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
