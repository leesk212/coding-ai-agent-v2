<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# scripts

## Purpose
These standalone helper scripts implement the deterministic parts of the built-in `skill-creator` workflow: creating a starter skill directory and validating frontmatter/basic shape.

## Key Files

| File | Description |
|------|-------------|
| `init_skill.py` | Creates a starter skill directory with a template `SKILL.md` and example resource folders. |
| `quick_validate.py` | Performs lightweight validation of `SKILL.md` frontmatter, naming, and description rules. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Treat these as standalone scripts: keep CLI help text, skill paths, and validation rules accurate and synchronized with the surrounding skill docs.
- Avoid adding package-only assumptions that would make the scripts unusable when executed directly.

### Testing Requirements
- Use `uv run --group test pytest tests/unit_tests/skills/test_commands.py` for command-level behavior and run the script manually in a temp directory when template output changes.

### Common Patterns
- Scripts are intentionally simple, print-oriented entrypoints rather than reusable libraries.
- Validation focuses on frontmatter shape and safe skill naming conventions.

## Dependencies

### Internal
- Referenced by the built-in `skill-creator/SKILL.md`.

### External
- Standard library for path handling plus `yaml` in `quick_validate.py`.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
