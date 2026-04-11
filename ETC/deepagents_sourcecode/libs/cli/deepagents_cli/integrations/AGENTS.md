<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# integrations

## Purpose
`integrations/` isolates optional sandbox-provider abstractions from the rest of the CLI runtime. This keeps provider discovery, lifecycle management, and interface contracts localized instead of leaking vendor-specific details across the package.

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | Package marker for optional integration helpers. |
| `sandbox_factory.py` | Discovers available providers, provisions sandboxes, and applies shared setup logic. |
| `sandbox_provider.py` | Defines the provider interface and shared sandbox-related exception types. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Preserve the provider-agnostic contract exposed to the rest of the CLI.
- Keep optional dependency imports lazy so unsupported providers do not break startup.

### Testing Requirements
- Run `uv run --group test pytest tests/unit_tests/test_sandbox_factory.py tests/unit_tests/test_server_manager.py`.
- Sandbox behavior that depends on external providers may also need `tests/integration_tests/test_sandbox_factory.py` or `test_sandbox_operations.py`.

### Common Patterns
- Provider imports are conditional and often wrapped in capability checks.
- The factory is responsible for shared environment/setup behavior, not only object creation.

## Dependencies

### Internal
- Used by `agent.py`, `server_manager.py`, and some integration tests.

### External
- Optional provider packages such as AgentCore, Daytona, Modal, Runloop, or LangSmith sandbox integrations.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
