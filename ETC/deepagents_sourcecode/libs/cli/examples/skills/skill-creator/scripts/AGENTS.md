<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# scripts

## Purpose
These example helper scripts demonstrate how a skill can bundle deterministic tooling alongside `SKILL.md` instructions. They scaffold a starter skill and perform lightweight validation.

## Key Files

| File | Description |
|------|-------------|
| `init_skill.py` | Example script that creates a new skill directory with starter content and resource folders. |
| `quick_validate.py` | Example script that validates `SKILL.md` frontmatter and naming rules. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Keep these scripts copy-friendly and easy to understand for users adapting them into their own environments.
- Avoid depending on repository-only assumptions that would make them brittle as examples.

### Testing Requirements
- Manual execution in a temp directory is usually enough; package-level tests cover the shipped built-in equivalents instead.

### Common Patterns
- Scripts are intentionally standalone and CLI-oriented rather than library-like.

## Dependencies

### Internal
- Referenced by `examples/skills/skill-creator/SKILL.md`.

### External
- Standard library plus `yaml` for validation.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
