# phil

A minimal command-line calculator for exact arithmetic, symbolic differentiation, integration, algebraic equation solving, and ordinary differential equations.

Powered by [SymPy](https://www.sympy.org/).

## Install

Requires [uv](https://docs.astral.sh/uv/).

Install from PyPI (no clone required):

```bash
uv tool install philcalc
```

Then run:

```bash
phil
```

Project links:

- PyPI: https://pypi.org/project/philcalc/
- Source: https://github.com/sacchen/phil

## Local Development Install

From a local clone:

```bash
uv tool install .
```

## 60-Second Start

```bash
uv tool install philcalc
phil --help
phil '1/3 + 1/6'
phil '(1 - 25e^5)e^{-5t} + (25e^5 - 1)t e^{-5t} + t e^{-5t} ln(t)'
phil
```

Then in REPL, try:

1. `d(x^3 + 2*x, x)`
2. `int(sin(x), x)`
3. `solve(x^2 - 4, x)`

## Usage

### One-shot

```bash
phil '<expression>'
phil --format pretty '<expression>'
phil --no-simplify '<expression>'
phil --latex '<expression>'
phil --latex-inline '<expression>'
phil --latex-block '<expression>'
phil --wa '<expression>'
phil --wa --copy-wa '<expression>'
phil :examples
```

### Interactive

```bash
phil
phil> <expression>
```

REPL commands:

- `:h` / `:help` show help
- `:examples` show sample expressions
- `:v` / `:version` show current version
- `:update` / `:check` compare current vs latest version and print update command
- `:q` / `:quit` / `:x` exit

The REPL starts with a short hint line and prints targeted `hint:` messages on common errors.
Unknown `:` commands return a short correction hint.
Evaluation errors also include: `hint: try WolframAlpha: <url>`.
Complex expressions also print a WolframAlpha equivalent hint after successful evaluation.
REPL sessions also keep `ans` (last result) and support assignment such as `A = Matrix([[1,2],[3,4]])`.

### Help

```bash
phil --help
```

### Wolfram helper

- By default, complex expressions print a WolframAlpha equivalent link.
- Links are printed as full URLs for terminal auto-linking (including iTerm2).
- Use `--wa` to always print the link.
- Use `--copy-wa` to copy the link to your clipboard when shown.
- Full URLs are usually clickable directly in modern terminals.

## Updates

From published package (anywhere):

```bash
uv tool upgrade philcalc
```

From a local clone of this repo:

```bash
uv tool install --force --reinstall --refresh .
```

Quick check in CLI:

```bash
phil :version
phil :update
phil :check
```

In REPL:

- `:version` shows your installed version.
- `:update`/`:check` show current version, latest known release, and update command.

For release notifications on GitHub, use "Watch" -> "Custom" -> "Releases only" on the repo page.

## Release

Tagged releases are published to PyPI automatically via GitHub Actions trusted publishing.

```bash
git pull
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

Then verify:

- GitHub Actions run: https://github.com/sacchen/phil/actions
- PyPI release page: https://pypi.org/project/philcalc/

### Long Expressions (easier input)

`phil` now uses relaxed parsing by default:

- `2x` works like `2*x`
- `{}` works like `()`
- `ln(t)` works like `log(t)`

So inputs like these work directly:

```bash
phil '(1 - 25e^5)e^{-5t} + (25e^5 - 1)t e^{-5t} + t e^{-5t} ln(t)'
phil '(854/2197)e^{8t}+(1343/2197)e^{-5t}+((9/26)t^2 -(9/169)t)e^{8t}'
```

Use strict parsing if needed:

```bash
phil --strict '2*x'
```

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

## Test

```bash
uv run --group dev pytest
```

## GitHub

- CI: `.github/workflows/ci.yml` runs tests on pushes and PRs.
- License: MIT (`LICENSE`).
- Ignore rules: Python/venv/cache (`.gitignore`).
- Contribution guide: `CONTRIBUTOR.md`.

## Learn by Doing

Try this sequence in REPL mode:

1. `1/3 + 1/6`
2. `d(x^3 + 2*x, x)`
3. `int(sin(x), x)`
4. `solve(x^2 - 4, x)`
5. `N(pi, 20)`

If you get stuck, run `:examples` or `:h`.

## Reference

### Operations

| Operation | Syntax |
|-----------|--------|
| Derivative | `d(expr, var)` |
| Integral | `int(expr, var)` |
| Solve equation | `solve(expr, var)` |
| Solve ODE | `dsolve(Eq(...), func)` |
| Equation | `Eq(lhs, rhs)` |
| Numeric eval | `N(expr, digits)` |
| Matrix determinant | `det(Matrix([[...]]))` |
| Matrix inverse | `inv(Matrix([[...]]))` |
| Matrix rank | `rank(Matrix([[...]]))` |
| Matrix eigenvalues | `eigvals(Matrix([[...]]))` |

### Symbols

`x`, `y`, `z`, `t`, `pi`, `e`, `f`

### Functions

`sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `abs`

### Matrix helpers

`Matrix`, `eye`, `zeros`, `ones`, `det`, `inv`, `rank`, `eigvals`

### Syntax notes

- `^` is exponentiation (`x^2`)
- `!` is factorial (`5!`)
- relaxed mode (default) allows implicit multiplication (`2x`); use `--strict` to require `2*x`
- `d(expr)` / `int(expr)` infer the variable when exactly one symbol is present
- Leibniz shorthand is accepted: `d(sin(x))/dx`, `df(t)/dt`
- `name = expr` assigns in REPL session (`ans` is always last result)
- Undefined symbols raise an error

## Safety limits

- Expressions longer than 2000 chars are rejected.
- Inputs containing blocked tokens like `__`, `;`, or newlines are rejected.

See [DESIGN.md](DESIGN.md) for implementation details.
