<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# remember

## Purpose
This leaf directory contains the built-in `remember` skill, which teaches the CLI agent how to capture durable learnings from a conversation into memory or new reusable skills.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Built-in instructions for reviewing a conversation and storing best practices, preferences, or workflows. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Preserve the distinction between memory-worthy guidance and workflow-worthy skill creation.
- Keep the description broad enough to trigger on “remember/save/update memory” style requests without becoming vague.

### Testing Requirements
- Discovery or metadata changes should be covered by `tests/unit_tests/skills/test_load.py`.

### Common Patterns
- The skill is instruction-only: no bundled scripts or assets.

## Dependencies

### Internal
- Loaded by the built-in skill discovery path in `deepagents_cli/skills/load.py`.

### External
- None beyond the CLI skill loader and Markdown/frontmatter parser.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
