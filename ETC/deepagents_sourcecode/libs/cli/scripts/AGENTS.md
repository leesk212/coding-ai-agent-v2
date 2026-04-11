<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-05 10:51:00 KST | Updated: 2026-04-05 10:51:00 KST -->

# scripts

## Purpose
`scripts/` holds developer and installation utilities that live beside the package but are not imported as part of the shipped runtime.

## Key Files

| File | Description |
|------|-------------|
| `check_imports.py` | Fast pre-test helper that tries importing Python files to catch syntax/import breakage early. |
| `install.sh` | Cross-platform installer script used by the README’s `curl | bash` installation flow. |

## Subdirectories

No subdirectories.

## For AI Agents

### Working In This Directory
- Keep scripts standalone and friendly to direct invocation from CI or shell docs.
- Preserve portability in `install.sh`; avoid Linux- or macOS-only assumptions unless clearly guarded.

### Testing Requirements
- `make check_imports` covers `check_imports.py`.
- For installer changes, run a dry/manual install flow or at minimum inspect the affected platform branches carefully.

### Common Patterns
- These scripts use direct CLI output and shell behavior instead of package-internal abstractions.

## Dependencies

### Internal
- `Makefile` and `README.md` reference these scripts directly.

### External
- `install.sh` depends on shell utilities and `uv`; `check_imports.py` uses only the Python standard library.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
