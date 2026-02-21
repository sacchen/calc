# Refactor Notes (2026-02-21)

This refactor focuses on reducing CLI monolith size and keeping behavior stable.

## Goals

- Reduce bloat pressure in `src/calc/cli.py`.
- Keep existing CLI/REPL semantics unchanged.
- Preserve compatibility for existing tests and monkeypatch patterns.

## Changes

- Added `src/calc/options.py`
  - Owns `CLIOptions`, option parsing, and format/color mode validation.

- Added `src/calc/updates.py`
  - Owns PyPI version lookup and update status line generation.

- Added `src/calc/repl.py`
  - Owns REPL command dispatch, tutorial command flow, and inline REPL option parsing.

- Added `src/calc/render.py`
  - Owns output rendering for plain/pretty/caret/latex/json formats.

- Added `src/calc/ode.py`
  - Owns ODE alias parsing and evaluation helpers.

- Updated `src/calc/cli.py`
  - Keeps compatibility wrapper functions (for tests and internal call sites).
  - Delegates to focused modules above.
  - Removes dead internal helper `_format_clickable_link`.

- Repository hygiene
  - Updated `.gitignore` to ignore `.coverage`, `.hypothesis/`, and `dist/`.
  - Removed duplicate local launcher script `calc` (kept `phil`).

## Validation

- `uv run --group dev pytest tests/test_cli.py tests/test_cli_unit.py -q`
- `uv run --group dev pytest -q`

Both pass at the time of this refactor.
