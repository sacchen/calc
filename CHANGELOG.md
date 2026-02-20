# Changelog

## 0.1.7 - 2026-02-20

- Refactor CLI internals to use a dedicated diagnostics module and typed option parsing.
- Keep CLI behavior stable while improving maintainability and test clarity.
- Consolidate contributor docs to keep `README.md` as the canonical CLI flag reference.

## 0.1.6 - 2026-02-20

- Add interop output mode: `--format json`.
- Improve reserved-name assignment hints (including explicit `f` function-notation guidance).
- Suppress WolframAlpha hint for reserved-name assignment errors.

## 0.1.5 - 2026-02-20

- Relaxed parsing now accepts shorthand trig input like `sinx`/`cosx`/`tanx` as `sin(x)`/`cos(x)`/`tan(x)`.
- CLI and REPL print an explicit `hint:` notice when shorthand is auto-interpreted.
- Add `--explain-parse` to show normalized input as a `hint:` on `stderr`.

## 0.1.4 - 2026-02-20

- Add in-app guided tour commands (`:tutorial`, `:tour`, `:next`, `:repeat`, `:done`).
- Add `:ode` quick reference with `Eq(...)`/`dsolve(...)` templates.
- Improve syntax hints for malformed `Eq(...)`, missing `Eq(...)` in `dsolve(...)`, and LaTeX fraction syntax errors.
- Link and expand new-user onboarding with `TUTORIAL.md`.

## 0.1.3 - 2026-02-20

- Improve ODE input ergonomics for homework-style notation.
- Accept REPL inline options and `phil ...`-prefixed input lines.
- Normalize ODE shorthand forms such as `dy/dx = y`, `y' = y`, and `y'' + y = 0`.
- Normalize common LaTeX-style inputs including `\frac{dy}{dx}`, `$...$`, and `\sin/\cos/\ln/\sqrt`.
- Add targeted `dsolve` function-notation hints for `y(x)` usage.

## 0.1.0 - 2026-02-20

- Initial public release.
- Symbolic CLI calculator with exact arithmetic and core SymPy operations.
- Hardened parser configuration and input guardrails.
- Minimal terminal UX (`:h`, `:examples`, `:q`, `:x`) with actionable hints.
- Optional WolframAlpha fallback hint on evaluation errors.
- uv package layout, tests, and GitHub Actions CI.
