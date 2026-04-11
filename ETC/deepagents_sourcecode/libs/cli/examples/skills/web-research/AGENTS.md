<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# web-research

## Purpose
This example demonstrates a higher-autonomy skill: plan first, delegate bounded research subtasks, collect file-based findings, and synthesize a final answer with citations.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Example multi-step research workflow that coordinates planning, delegation, and synthesis. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Preserve the distinction between planning, delegated execution, and synthesis; that sequence is the core teaching value of this example.
- Keep file-based communication conventions explicit so subagents can interoperate cleanly.

### Testing Requirements
- Manual review is generally sufficient because this is instructional content rather than packaged runtime code.

### Common Patterns
- The skill encodes a reusable workflow rather than a single API integration.

## Dependencies

### Internal
- Reflects the CLI’s broader support for delegated tasks, file tools, and web search.

### External
- Depends on web access and the skill/tool set being available in the target environment.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
