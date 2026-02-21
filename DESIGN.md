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
src/calc/diagnostics.py ← hint logic and diagnostic policy
tests/test_core.py
tests/test_cli.py
phil                ← local launcher script (uv run --project)
CONTRIBUTOR.md      ← contribution and extension guide
```

## Packaging model

This project is a standard `uv` package:

- `pyproject.toml` declares metadata and dependencies.
- `[project.scripts]` exposes the `phil` command.
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
`--strict` disables relaxed parsing in both one-shot and REPL modes.
`--no-simplify` skips the simplify step for large or structure-sensitive expressions.

`d(expr)` and `int(expr)` can infer the variable only when the expression has exactly one free symbol. Ambiguous or symbol-free expressions must pass the variable explicitly.
REPL evaluation supports session locals, assignment (`name = expr`), and `ans` for last result.
Matrix helpers are exposed in the allowed namespace (`Matrix`, `eye`, `zeros`, `ones`, `det`, `inv`, `rank`, `eigvals`).

## Exit-code behavior

- One-shot mode returns `0` on success.
- One-shot mode returns `1` on parse/evaluation errors.
- REPL mode keeps running on expression errors and exits `0` on Ctrl-C/Ctrl-D.

## REPL UX

- Prompt is `phil>`.
- Minimal command mode inspired by terminal-first tools:
  - `:h` or `:help` shows available commands
  - `:examples` shows a compact learning set
  - `:tutorial` / `:tour` starts a guided walkthrough (`:next`, `:repeat`, `:done`)
  - `:ode` prints ODE-specific templates and `dsolve` patterns
  - `:version` shows installed version
  - interactive startup prints automatic update status
  - `:update` / `:check` compare current vs latest version and print upgrade command
  - `:q` or `:quit` exits
- Errors are terse and prefixed with `E:`.
- Common failures include contextual `hint:` lines.
- Evaluation failures include a WolframAlpha URL hint for optional browser lookup.
- Complex successful expressions also show a WolframAlpha equivalent hint.
- REPL accepts inline CLI options (`--latex ...`, `--format ...`, etc.) and `phil ...`-prefixed lines.
- `--wa` forces hints for all expressions; `--copy-wa` attempts clipboard copy.
- `--color auto|always|never` controls ANSI color for diagnostic stderr lines (`E:` and `hint:`).
- `NO_COLOR` disables auto color mode.
- Output format selection and user-facing flag docs live in `README.md`.
- ODE shorthand (`dy/dx = y`, `y' = y`, `y'' + y = 0`) is normalized to `Eq(...)` expressions using `y(x)` semantics.
- Common LaTeX-style input (`$...$`, `\frac{...}{...}`, `\sin`, `\ln`, `\sqrt{...}`) is normalized before parsing.

## Startup time

Startup cost is mostly from Python + SymPy import time. Packaging improves distribution/testing and reproducibility, but not raw import latency by itself.
