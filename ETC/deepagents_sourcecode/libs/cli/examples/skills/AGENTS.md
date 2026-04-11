<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# skills

## Purpose
This container groups the example skills shipped alongside the CLI repository. Each child directory demonstrates a different prompt/skill pattern, from documentation lookup to web research or scaffolded helper scripts.

## Key Files

This directory is intentionally container-only; its important content lives in subdirectories.

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `arxiv-search/` | Example external-data skill that searches arXiv papers (see `arxiv-search/AGENTS.md`). |
| `langgraph-docs/` | Example docs-lookup skill for LangGraph references (see `langgraph-docs/AGENTS.md`). |
| `skill-creator/` | Example user-space skill scaffolder with bundled scripts (see `skill-creator/AGENTS.md`). |
| `web-research/` | Example delegated multi-step web research skill (see `web-research/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Keep each example focused on one teaching goal and avoid mixing multiple extension patterns into a single skill.
- Match the real skill directory shape so users can copy these folders directly.

### Testing Requirements
- Manual validation is the norm: ensure example commands still make sense and bundled script paths remain correct.

### Common Patterns
- Every child directory contains a `SKILL.md`; some include helper scripts for deterministic tasks.

## Dependencies

### Internal
- Mirrors the conventions enforced by `deepagents_cli/skills/commands.py` and `deepagents_cli/skills/load.py`.

### External
- Optional packages depend on the example, such as `arxiv` for the arXiv example.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
