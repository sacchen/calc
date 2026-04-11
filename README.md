# phil

A minimal command-line calculator for exact arithmetic, symbolic differentiation, integration, algebraic equation solving, and ordinary differential equations.

Powered by [SymPy](https://www.sympy.org/).

## Why phil

`phil` is designed to be the first-stop calculator for quick terminal math, homework, and symbolic workflows — before reaching for WolframAlpha, a Python REPL, or a graphing calculator.

It prioritizes exactness, speed, and discoverability. When it rewrites your input, it says so.

## Install

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv tool install philcalc
```

- PyPI: [https://pypi.org/project/philcalc/](https://pypi.org/project/philcalc/)
- Source: [https://github.com/sacchen/phil](https://github.com/sacchen/phil)
- Tutorial: [TUTORIAL.md](TUTORIAL.md)
- Roadmap: [ROADMAP.md](ROADMAP.md)

## Quick Start

```bash
phil '1/3 + 1/6'
phil '10^100000 + 1 - 10^100000'
phil 'd(x^3 + 2*x, x)'
phil 'int(sin(x), x)'
phil "ode y' = y, y(0)=1"
phil '(1 - 25e^5)e^{-5t} + (25e^5 - 1)t e^{-5t} + t e^{-5t} ln(t)'
```

Or open the REPL (`phil`) and try these in order:

1. `1/3 + 1/6`
2. `d(x^3 + 2*x, x)`
3. `int(sin(x), x)`
4. `solve(x^2 - 4, x)`
5. `N(pi, 20)`

If stuck, run `:examples` or `:h`.

## Usage

### One-shot

```bash
phil '<expression>'
phil --format pretty '<expression>'
phil --format json '<expression>'
phil --no-simplify '<expression>'
phil --explain-parse '<expression>'
phil --latex '<expression>'
phil --latex-inline '<expression>'
phil --latex-block '<expression>'
phil --wa '<expression>'
phil --wa --copy-wa '<expression>'
phil --color always '<expression>'   # also: auto (default), never
phil "ode y' = y"
phil "ode y' = y, y(0)=1"
phil "linalg solve A=[[2,1],[1,3]] b=[1,2]"
phil "linalg rref A=[[1,2],[2,4]]"
phil "linalg det A=[[1,2],[3,4]]"
phil "linalg inv A=[[1,2],[3,4]]"
phil "linalg eig A=[[1,2],[3,4]]"
phil "linalg nullspace A=[[1,2],[2,4]]"
phil :examples
phil :tutorial
phil :ode
phil :linalg
```

### Interactive REPL

```bash
phil
phil> <expression>
```

REPL commands:

- `:h` / `:help` show strict command reference
- `?`, `??`, `???` progressive feature discovery (quick start, speed shortcuts, advanced demos)
- `:examples` show runnable expression patterns
- `:tutorial` / `:t` / `:tour` start interactive tutorial mode
- `:ode` show ODE cheat sheet and templates
- `:linalg` / `:la` show linear algebra cheat sheet and templates
- `:next` / `:repeat` / `:done` control interactive tutorial mode (`Enter` advances while tutorial is active)
- `:v` / `:version` show current version
- `:update` / `:check` compare current vs latest version and print update command
- `:q` / `:quit` / `:x` exit

The REPL starts with `phil vX.Y.Z REPL [status] (:h help, :t tutorial)` on interactive terminals.
When an update is available, startup prints `uv tool upgrade philcalc` on the next line.
Errors are prefixed with `E:` followed by a `hint:` line.
Most evaluation errors also include `hint: try WolframAlpha: <url>` (suppressed for some local guardrail failures).
Session keeps `ans` (last result) and supports assignment: `A = Matrix([[1,2],[3,4]])`.
Inline CLI options work per-expression: `--latex d(x^2, x)`.
For readable ODE solving, prefer `ode ...` input: `ode y' = y`.

## Parsing and Input Style

These normalizations apply in all modes (including `--strict`):

- `{}` -> `()`
- `ln(t)` -> `log(t)`
- `!` factorial
- `sin^2(x)` accepted
- Leibniz shorthand accepted (`d(sin(x))/dx`, `df(t)/dt`)
- ODE shorthand accepted (`dy/dx = y`, `y' = y`, `y'' + y = 0`, `y'(0)=0`)
- LaTeX-style ODE accepted (`\frac{dy}{dx} = y`, `\frac{d^2y}{dx^2} + y = 0`)
- Common LaTeX wrappers and commands are normalized: `$...$`, `\(...\)`, `\sin`, `\cos`, `\ln`, `\sqrt{...}`, `\frac{a}{b}`

Relaxed parsing (default) also enables implicit multiplication:

- `2x` -> `2*x`
- `sinx` -> `sin(x)` (with a `hint:` notice)

Use `--strict` to require explicit multiplication:

```bash
phil --strict '2*x'
```

Undefined symbols raise errors.
Built-in helper names are reserved for evaluation and cannot be reassigned.
In ODE input, prefer explicit multiplication (`20*y` instead of `20y`) for predictable parsing.

## Exact Arithmetic and Reliability

`phil` defaults to exact symbolic arithmetic.

Cancellable huge expressions stay fast and exact:

```text
10^10000000000 + 1 - 10^10000000000  ->  1
2^(2^20) + 1 - 2^(2^20)  ->  1
```

Non-cancellable explosive growth fails fast with a recovery hint rather than hanging:

```text
10^10000000000 + 1
2^(2^(2^20))
100001!
factorial(10^10)
```

Ambiguous shorthand is rejected with explicit guidance:

```text
sin x^2
```

Precedence note:

- `-2^2` -> `-(2^2)`
- Use `(-2)^2` for a negative base squared.

## Output and Interop

- `--format json` prints a compact JSON object with `input`, `parsed`, and `result`; diagnostics stay on `stderr`
- `--format pretty` improves matrix readability
- `--explain-parse` prints `hint: parsed as: ...` on `stderr`
- `--color auto|always|never` controls ANSI output on diagnostic lines; `NO_COLOR` also respected
- `stdout` stays result-only, so pipes and scripts remain predictable
- Complex expressions print a WolframAlpha equivalent link by default; `--wa` forces it, `--copy-wa` copies it to the clipboard

## Updates

```bash
uv tool upgrade philcalc
```

In REPL:

- Startup prints a status badge on interactive terminals; when an update is available a second line prints the upgrade command
- `:version` shows your installed version
- `:update` / `:check` show current version, latest known release, and update command

For release notifications on GitHub, use "Watch" -> "Custom" -> "Releases only" on the repo page.

## Examples

```bash
$ phil '1/3 + 1/6'
1/2

$ phil 'd(x^3 + 2*x, x)'
3*x**2 + 2

$ phil 'int(sin(x), x)'
-cos(x)

$ phil 'solve(x^2 - 4, x)'
[-2, 2]

$ phil 'N(pi, 30)'
3.14159265358979323846264338328

$ phil --latex 'd(x^2, x)'
2 x

$ phil --latex-inline 'd(x^2, x)'
$2 x$

$ phil --latex-block 'd(x^2, x)'
$$
2 x
$$

$ phil --format pretty 'Matrix([[1,2],[3,4]])'
[1  2]
[3  4]
```

## Reference

### Core operations

| Operation | Syntax |
| --- | --- |
| Derivative | `d(expr, var)` |
| Integral | `int(expr, var)` |
| Solve equation | `solve(expr, var)` |
| Solve ODE | `dsolve(Eq(...), func)` |
| Equation | `Eq(lhs, rhs)` |
| Numeric eval | `N(expr, digits)` |
| Integer GCD/LCM | `gcd(a, b)`, `lcm(a, b)` |
| Primality / factorization | `isprime(n)`, `factorint(n)` |
| Rational parts | `num(expr)`, `den(expr)` |
| Matrix determinant | `det(Matrix([[...]]))` or `linalg det A=[[...]]` |
| Matrix inverse | `inv(Matrix([[...]]))` or `linalg inv A=[[...]]` |
| Matrix rank | `rank(Matrix([[...]]))` or `linalg rank A=[[...]]` |
| Matrix eigenvalues | `eigvals(Matrix([[...]]))` or `linalg eig A=[[...]]` |
| Matrix RREF | `rref(Matrix([[...]]))` or `linalg rref A=[[...]]` |
| Matrix nullspace | `nullspace(Matrix([[...]]))` or `linalg nullspace A=[[...]]` |
| Solve linear system (Ax=b) | `msolve(Matrix([[...]]), Matrix([...]))` or `linalg solve A=[[...]] b=[...]` |
| Symbolic linear solve | `linsolve((Eq(...), Eq(...)), (x, y))` |

### Common symbols

`x`, `y`, `z`, `t`, `pi`, `e`, `f`

### Functions

`sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `abs`, `gamma`, `atan2`, `binomial`, `limit`, `series`, `factor`, `expand`

### Exact arithmetic helpers

`gcd`, `lcm`, `isprime`, `factorint`, `num`, `den`

### Symbol helpers

- `symbols("A B C")` returns a tuple of symbols
- `S("A")` is shorthand for `Symbol("A")`

### Matrix helpers

`Matrix`, `eye`, `zeros`, `ones`, `det`, `inv`, `rank`, `eigvals`, `rref`, `nullspace`, `msolve`, `linsolve`

### Syntax notes

- `^` is exponentiation (`x^2`)
- Function exponent notation is accepted (`sin^2(x)`, `cos^2(x)`)
- `!` is factorial (`5!`)
- Relaxed mode (default) allows implicit multiplication (`2x`); use `--strict` to require `2*x`
- `d(expr)` / `int(expr)` infer the variable when exactly one symbol is present
- Leibniz shorthand is accepted: `d(sin(x))/dx`, `df(t)/dt`
- ODE shorthand is accepted: `dy/dx = y`, `y' = y`, `y'' + y = 0`, `y'(0)=0`
- LaTeX-style ODE shorthand is accepted: `\frac{dy}{dx} = y`, `\frac{d^2y}{dx^2} + y = 0`
- `name = expr` assigns in the REPL session (`ans` is always the last result)
- Built-in helper names are reserved and cannot be reassigned
- Undefined symbols raise an error

## Development

From a local clone:

```bash
uv tool install .                               # install locally
uv run --group dev pytest                       # run tests
uv run --group dev pytest -m "not integration" # fast local loop
scripts/checks.sh                              # full quality gate
```

CI runs via GitHub Actions. License is MIT.
See [CONTRIBUTOR.md](CONTRIBUTOR.md) for contribution guide and release process.
