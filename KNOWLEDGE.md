# KNOWLEDGE

Project-specific knowledge for contributors.

## Product Surface

- Distribution name: `philcalc`
- CLI command: `phil`
- Core module path: `src/calc/`

## Parsing and Evaluation Model

- Uses SymPy `parse_expr` with restricted globals.
- Default mode is relaxed parsing for calculator-style input.
- Strict mode (`--strict`) disables relaxed transforms.
- Optional no-simplify mode (`--no-simplify`) returns parsed form without `simplify()`.

## Supported Syntax Highlights

- Derivative:
  - `d(expr, var)`
  - `d(expr)` when variable can be inferred uniquely
  - Leibniz shorthand: `d(sin(x))/dx`, `df(t)/dt`
  - ODE shorthand equation: `dy/dx = y`, `y' = y`, `y'' + y = 0`
  - LaTeX ODE shorthand: `\frac{dy}{dx} = y`, `\frac{d^2y}{dx^2} + y = 0`
  - LaTeX wrappers/commands normalized: `$...$`, `\(...\)`, `\sin`, `\cos`, `\ln`, `\sqrt{...}`, `\frac{a}{b}`
- Integral:
  - `int(expr, var)`
  - `int(expr)` with unique variable inference
- Matrix helpers:
  - `Matrix`, `eye`, `zeros`, `ones`
  - `det`, `inv`, `rank`, `eigvals`
- Session behavior (REPL):
  - assignment: `A = ...`
  - `ans` = last result
  - inline options are accepted (example: `--latex d(x^2, x)`)
  - guided tutorial commands: `:tutorial`/`:tour`, `:next`, `:repeat`, `:done`
  - ODE helper command: `:ode`

## Formatting Modes

- `--format plain` (default)
- `--format pretty`
- `--format latex`
- `--format latex-inline`
- `--format latex-block`
- `--format json` (compact JSON with `input`, `parsed`, `result`; diagnostics on stderr)
- `--color auto|always|never` (diagnostic stderr coloring only)

Legacy aliases:

- `--latex`, `--latex-inline`, `--latex-block`

## Error UX

- Errors start with `E:`
- Follow-up guidance via `hint:`
- Syntax-specific hints exist for common derivative and matrix mistakes.
- Reserved-name assignment errors show targeted hints (e.g. `f` → ODE function-notation guidance).
- WolframAlpha hint is suppressed for reserved-name assignment errors.

## Testing Expectations

- Unit + integration + regression tests.
- Property tests via `hypothesis` for core invariants.
- CI checks multiple Python versions and install smoke tests.
