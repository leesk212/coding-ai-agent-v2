<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# langgraph-docs

## Purpose
This leaf directory contains a documentation-lookup skill that teaches the agent to fetch the LangGraph docs index first, then retrieve a focused subset of pages before answering.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Example workflow for selecting and fetching the right LangGraph documentation pages. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Keep the instructions aligned with the current docs index URL and the intended “fetch a small relevant subset first” workflow.

### Testing Requirements
- Manual validation is sufficient: confirm the referenced docs URL and fetch strategy still make sense.

### Common Patterns
- Documentation lookup skills should prioritize a staged retrieval process instead of loading too many pages at once.

## Dependencies

### Internal
- Uses the same `fetch_url` workflow documented elsewhere in the CLI skill system.

### External
- Depends on the public LangChain/LangGraph docs endpoints remaining available.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
