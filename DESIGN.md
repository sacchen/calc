# Design & Implementation

## Architecture

```
user input
    ↓
parse_expr()        ← controlled namespace + restricted globals
    ↓
SymPy expression
    ↓
simplify()          ← skipped for list/tuple/dict results
    ↓
print()
```

## Project layout

```
pyproject.toml
src/calc/core.py    ← parser and evaluator
src/calc/cli.py     ← command-line interface
tests/test_core.py
tests/test_cli.py
calc                ← local launcher script (uv run --project)
CONTRIBUTOR.md      ← contribution and extension guide
```

## Packaging model

This project is a standard `uv` package:

- `pyproject.toml` declares metadata and dependencies.
- `[project.scripts]` exposes the `calc` command.
- Tests run via `uv run --group dev pytest`.

## Parsing model

`parse_expr` is configured with:

- Controlled `local_dict` (only the symbols and operations we allow)
- Restricted `global_dict` with `__builtins__` removed
- Transformations: `auto_number`, `factorial_notation`, `convert_xor`
- Input validation before parsing (length and blocked-token checks)
- Normalization pass for user-friendly syntax (`{}` -> `()`, `ln(` -> `log(`)

This significantly reduces parser attack surface for CLI usage. It is still not a hardened sandbox for arbitrary untrusted multi-tenant input.

By default, CLI evaluation uses relaxed parsing (`implicit_multiplication_application`) to make long calculator-style expressions easier to enter.

## Exit-code behavior

- One-shot mode returns `0` on success.
- One-shot mode returns `1` on parse/evaluation errors.
- REPL mode keeps running on expression errors and exits `0` on Ctrl-C/Ctrl-D.

## REPL UX

- Prompt is `calc>`.
- Minimal command mode inspired by terminal-first tools:
  - `:h` or `:help` shows available commands
  - `:examples` shows a compact learning set
  - `:version` shows installed version
  - `:update` prints the upgrade command
  - `:q` or `:quit` exits
- Errors are terse and prefixed with `E:`.
- Common failures include contextual `hint:` lines.
- Evaluation failures include a WolframAlpha URL hint for optional browser lookup.
- Complex successful expressions also show a WolframAlpha equivalent hint.
- `--wa` forces hints for all expressions; `--copy-wa` attempts clipboard copy.
- Optional LaTeX output via `--latex`.

## Startup time

Startup cost is mostly from Python + SymPy import time. Packaging improves distribution/testing and reproducibility, but not raw import latency by itself.
