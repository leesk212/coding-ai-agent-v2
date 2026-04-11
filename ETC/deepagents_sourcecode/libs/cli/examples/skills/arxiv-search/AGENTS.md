<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# arxiv-search

## Purpose
This example skill shows how to package a small research-oriented tool: a concise `SKILL.md` plus a Python helper that queries arXiv and prints formatted paper summaries.

## Key Files

| File | Description |
|------|-------------|
| `SKILL.md` | Instructions for when and how the agent should call the arXiv search helper. |
| `arxiv_search.py` | Standalone script that queries the arXiv API and formats titles plus abstracts. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Keep the example command lines and optional dependency instructions synchronized with the script behavior.
- Preserve its role as a minimal example; do not turn it into a full SDK wrapper unless that is the explicit goal.

### Testing Requirements
- Manual smoke test: run `arxiv_search.py` with a sample query in an environment where the optional `arxiv` package is installed.

### Common Patterns
- Example skills should be executable directly from a user skill directory with minimal setup.

## Dependencies

### Internal
- None beyond the general skill-loading conventions used by the CLI.

### External
- The helper script requires the optional `arxiv` package.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
