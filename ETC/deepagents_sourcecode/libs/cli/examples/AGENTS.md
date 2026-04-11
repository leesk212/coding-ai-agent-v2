<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# examples

## Purpose
`examples/` contains reference extension assets for the CLI, currently centered on example skills. These files are not packaged runtime code; they serve as learning material and starting points for users building their own skills.

## Key Files

This directory currently acts as a container for example subdirectories rather than owning top-level files.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `skills/` | Sample skills that demonstrate different extension styles and bundled resources (see `skills/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Keep examples simple, illustrative, and safe to copy into a user skill directory.
- Prefer clarity over exhaustive edge-case handling; these files are teaching material first.

### Testing Requirements
- Examples are usually validated through manual smoke checks rather than the main unit-test suite.

### Common Patterns
- Each example skill is self-contained and mirrors the same `SKILL.md` plus optional `scripts/` structure used by real skills.

## Dependencies

### Internal
- These examples mirror conventions implemented in `deepagents_cli/skills/` and `deepagents_cli/built_in_skills/`.

### External
- Some example scripts rely on optional third-party packages that users install themselves.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
