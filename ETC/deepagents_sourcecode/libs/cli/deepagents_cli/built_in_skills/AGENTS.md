<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# built_in_skills

## Purpose
This directory contains the skills that ship with `deepagents-cli` out of the box. They are discovered before user or project skills and establish examples for frontmatter quality, resource layout, and bundled helper scripts.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Package marker for shipped built-in skills. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `remember/` | Built-in skill for capturing learnings into memory or reusable skills (see `remember/AGENTS.md`). |
| `skill-creator/` | Built-in skill for scaffolding and validating new skills (see `skill-creator/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Keep SKILL frontmatter accurate because `name` and `description` determine discovery behavior.
- Favor concise, trigger-oriented instructions; built-in skills should model best practices for user-authored skills.

### Testing Requirements
- Run `uv run --group test pytest tests/unit_tests/skills/test_load.py tests/unit_tests/skills/test_commands.py` when changing built-in skill packaging or discovery semantics.

### Common Patterns
- Each skill directory centers on a required `SKILL.md`.
- More complex skills may bundle deterministic helper scripts under `scripts/`.

## Dependencies

### Internal
- `deepagents_cli/skills/load.py` and `deepagents_cli/skills/commands.py` discover and operate on these assets.

### External
- YAML frontmatter parsing and Markdown processing happen through the CLI runtime, not custom tooling in this directory.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
