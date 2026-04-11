<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# skill-creator

## Purpose
This example mirrors the built-in `skill-creator` concept in user-space form. It shows how a skill can mix instructional guidance with helper scripts that scaffold and validate other skills.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Example guidance for designing and structuring a new skill outside the built-in package scope. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `scripts/` | Example scaffold and validation scripts bundled with the skill (see `scripts/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Keep this example in sync with the bundled scripts so the example remains runnable.
- Use it as a teaching artifact, not as the source of truth for shipped built-in skill behavior.

### Testing Requirements
- Manual smoke checks are usually enough; if logic is copied into shipped code, cover that in the package test suite separately.

### Common Patterns
- The example matches the same skill shape as the built-in version but is positioned as a copyable reference.

## Dependencies

### Internal
- Conceptually mirrors `deepagents_cli/built_in_skills/skill-creator/`.

### External
- The bundled scripts use standard library plus YAML parsing for validation.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
