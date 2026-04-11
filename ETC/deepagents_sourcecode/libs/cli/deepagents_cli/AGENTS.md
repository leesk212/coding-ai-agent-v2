<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# deepagents_cli

## Purpose
`deepagents_cli` is the shipped Python package for the Deep Agents terminal product. It contains the CLI entrypoints, Textual TUI, non-interactive runner, agent assembly, configuration/model loading, session persistence, MCP integration, built-in skills, and the widget library used by the app.

## Key Files

| File | Description |
|------|-------------|
| `main.py` | Parses CLI arguments and dispatches interactive, ACP, and non-interactive runtime modes. |
| `app.py` | Runs the Textual application, screen state, and interactive command handling. |
| `non_interactive.py` | Headless execution path for scripting and CI-style use cases. |
| `agent.py` | Creates the CLI agent graph, middleware stack, tools, and subagent wiring. |
| `config.py` | Central runtime settings, model bootstrap, glyph handling, and shell safety helpers. |
| `model_config.py` | TOML-backed model preference and provider-profile persistence layer. |
| `textual_adapter.py` | Bridges LangGraph stream events into Textual widgets and session stats. |
| `sessions.py` | SQLite-backed thread/session listing and checkpoint-derived metadata helpers. |
| `server_manager.py` | Starts the local LangGraph server and returns a connected remote client. |
| `server.py` | Generates `langgraph.json`, allocates ports, and manages the dev-server subprocess. |
| `remote_client.py` | HTTP/SSE wrapper around the local LangGraph dev server. |
| `mcp_tools.py` | Discovers, validates, merges, and loads MCP configurations and tool metadata. |
| `tools.py` | CLI-specific tools such as web search and URL fetching. |
| `default_agent_prompt.md` | Default coding-agent system prompt shipped with the package. |
| `system_prompt.md` | Supplemental system-prompt content used by the CLI runtime. |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `widgets/` | Textual widgets and modal screens that render the interactive UI (see `widgets/AGENTS.md`). |
| `skills/` | CLI-facing skill command and loading helpers (see `skills/AGENTS.md`). |
| `integrations/` | Optional sandbox integration abstractions and provider interfaces (see `integrations/AGENTS.md`). |
| `built_in_skills/` | Built-in skills shipped inside the package (see `built_in_skills/AGENTS.md`). |

## For AI Agents

### Working In This Directory
- Preserve public entrypoints, slash commands, thread/session semantics, and lazy-import behavior unless the task explicitly changes them.
- Keep docstrings and comments concise, American English, and focused on purpose/invariants rather than line-by-line narration.
- When editing runtime code, prefer targeted changes that match the existing split between core runtime modules and `widgets/`.

### Testing Requirements
- Match touched modules to tests under `tests/unit_tests/`, for example `test_app.py`, `test_textual_adapter.py`, `test_sessions.py`, `test_mcp_tools.py`, or relevant widget tests.
- Run `uv run --group test ruff check`, `uv run --group test ty check`, and at least the affected pytest slice before closing substantial changes.

### Common Patterns
- Deferred imports are used heavily to keep CLI startup fast.
- The TUI and headless flows both talk to a local LangGraph server through `RemoteAgent`.
- Session state is persisted in SQLite and surfaced through lightweight helpers rather than direct SQL in UI code.

## Dependencies

### Internal
- `widgets/` renders state created by `app.py` and updated through `textual_adapter.py`.
- `integrations/`, `skills/`, and `built_in_skills/` extend the core behavior assembled in `agent.py`.

### External
- `deepagents` provides the agent harness and backend abstractions.
- `langchain`, `langgraph`, and `langgraph-sdk` provide model/tool/runtime primitives.
- `textual` and `rich` power the TUI rendering pipeline.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
