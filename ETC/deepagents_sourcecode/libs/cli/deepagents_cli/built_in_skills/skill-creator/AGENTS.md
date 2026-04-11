<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# skill-creator

## Purpose
This directory contains the built-in `skill-creator` skill, which documents how to design, scaffold, and validate Deep Agents skills. It also bundles scripts that turn the guidance into repeatable file generation and validation steps.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Built-in instructions for creating, structuring, and validating skills with correct precedence and frontmatter. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `scripts/` | Helper scripts for scaffolding and validating skill directories (see `scripts/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Keep the prose aligned with the actual script behavior and skill precedence rules implemented elsewhere in the package.
- When changing the template or validation rules, update both `SKILL.md` and the bundled scripts together.

### Testing Requirements
- Run `uv run --group test pytest tests/unit_tests/skills/test_commands.py tests/unit_tests/skills/test_load.py` for behavior changes.

### Common Patterns
- Human-readable guidance lives in `SKILL.md`; deterministic file creation and validation live in `scripts/`.

## Dependencies

### Internal
- `deepagents_cli/skills/commands.py` exposes related CLI operations.
- The bundled scripts are invoked as standalone helpers from the skill instructions.

### External
- The scripts rely on standard-library filesystem handling and YAML parsing.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
