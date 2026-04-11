<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# widgets

## Purpose
`widgets/` contains the Textual presentation layer for `deepagents-cli`: input controls, transcript rendering, modal screens, approval UI, status/footer widgets, and specialized rendering helpers. These modules are intentionally split so the main app coordinates behavior without owning every UI detail directly.

## Key Files

| File | Description |
|------|-------------|
| `chat_input.py` | Main multiline input widget with completion, history, paste heuristics, and mode handling. |
| `messages.py` | Transcript widgets for user, assistant, tool, diff, and app-system messages. |
| `thread_selector.py` | Thread browser modal with filtering, sorting, and delete support. |
| `model_selector.py` | Modal model picker used by `/model`. |
| `approval.py` | Human-in-the-loop approval UI for side-effecting tool calls. |
| `ask_user.py` | Interactive question widgets used by the `ask_user` flow. |
| `autocomplete.py` | Slash-command and file-mention completion engines. |
| `message_store.py` | Virtualized message store backing the transcript DOM. |
| `status.py` | Footer/status bar widgets summarizing active session state. |
| `welcome.py` | Welcome banner and startup footer rendering. |
| `mcp_viewer.py` | Modal viewer for loaded MCP servers and tools. |
| `tool_renderers.py` | Registry that maps tool calls to specialized approval widgets. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Follow Textual patterns for `compose`, `Binding`, reactive state, and widget-local messages.
- Prefer `textual.content.Content` for in-app rendering and keep theme-aware styling consistent with existing widget code.
- Keep widget behavior paired with tests in `tests/unit_tests/` because UI regressions often show up in focus, keyboard, or render-state flows.

### Testing Requirements
- Run only the widget-specific test slice you touched, such as `test_chat_input.py`, `test_messages.py`, `test_thread_selector.py`, `test_model_selector.py`, `test_status.py`, `test_welcome.py`, or `test_approval.py`.

### Common Patterns
- Widgets communicate via Textual message classes rather than direct cross-module mutation.
- Larger widgets split local helpers, row widgets, and modal/container classes inside the same file.
- Theme colors and ASCII-mode fallbacks are applied consistently across renderers.

## Dependencies

### Internal
- Mounted and orchestrated by `deepagents_cli/app.py`.
- Many widgets depend on shared runtime helpers such as `theme.py`, `config.py`, and `message_store.py`.

### External
- `textual` is the primary UI framework, with `rich`/`Content`-style rendering for formatted text.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
