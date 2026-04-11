# Changelog

## 0.2.7 - 2026-04-11

- Add `--no-wa` flag to suppress WolframAlpha fallback hints (useful for offline or privacy-sensitive workflows); also settable inline in the REPL.
- Guard `solve()` against matrix-style keyword arguments (`solve(A=..., b=...)`) with a clear error and redirect hint to `linalg solve` or `msolve(A, b)`.
- Expand linalg subcommands: `eig`, `nullspace`, `rank` now available alongside existing `solve`, `rref`, `det`, `inv`.
- Broaden SymPy symbol allowlist so more built-in functions and constants are available without manual import.
- Unify one-shot and REPL shortcut dispatch so edge-case behavior is consistent across both modes.
- Improve error hint coverage: deterministic fallback hints for unknown errors, better `solve()` ambiguity diagnostics, `zoo` hint for complex infinity results.
- Extract linalg dispatch to `linalg.py` (internal refactor; no behavior change).
- Bump `pygments` to 2.20.0 (CVE-2026-4539).

## 0.2.6 - 2026-02-23

- Add symbolic-first growth guardrails for huge integer powers, exponent towers, and large factorial inputs.
- Keep cancellable large expressions fast and exact while failing non-cancellable growth paths quickly with actionable hints.
- Improve ambiguity recovery guidance:
  - reject ambiguous trig shorthand like `sin x^2` with explicit rewrite options,
  - clarify unary-minus power precedence (`-2^2` vs `(-2)^2`) via parse explanation hints.
- Suppress WolframAlpha fallback hints for deterministic local guardrail failures.
- Expand regression coverage for guardrail behavior and one-shot/REPL parity.

## 0.2.5 - 2026-02-23

- Refine onboarding UX split:
  - `:h` is strict reference,
  - `?` is quick-start guidance,
  - `??` is speed shortcuts,
  - `???` is advanced demos.
- Curate `:examples` to runnable high-signal patterns for exact arithmetic, symbolic basics, linalg/ODE, and numeric representation.
- Add tutorial shortcut alias `:t` and allow `Enter` to advance tutorial steps while active.
- Update tutorial/help docs to match the first-minute walkthrough flow.

## 0.2.4 - 2026-02-23

- Add exact arithmetic helpers to the default namespace: `gcd`, `lcm`, `isprime`, `factorint`, `num`, `den`.
- Expand help/examples/docs to surface integer and rational exact-workflow commands.
- Add helper-specific recovery hints for common mistakes (arity and integer-only requirements).
- Add unit and integration coverage for one-shot and REPL behavior of the new helpers.

## 0.2.3 - 2026-02-23

- Simplify REPL startup banner to `phil vX.Y.Z REPL` with compact update badge status.
- Show `[latest]` when current and `[vX.Y.Z available]` when an upgrade exists.
- Print `uv tool upgrade philcalc` on startup when an update is available.
- Clarify startup fallback badges for unavailable or unverified latest-version checks.

## 0.2.2 - 2026-02-23

- Improve ODE UX: normalize dependent-variable terms more consistently in `ode ...` input (including forms like `20y` and `d(y, x)`).
- Accept prime-at-point initial conditions like `y'(0)=0` in `ode ...` workflows.
- Clarify `:ode` help text with second-order + IC examples and explicit multiplication guidance.
- Add symbol helpers `symbols("A B C")` and `S("A")` to simplify coefficient-matching workflows.
- Improve undefined-name hints for uppercase coefficient symbols with direct recovery guidance.

## 0.2.1 - 2026-02-23

- Initialize readline support on REPL startup so arrow keys and history editing work in interactive terminals.
- Add an explicit REPL hint when readline support is unavailable and escape sequences may appear.

## 0.2.0 - 2026-02-21

- Add matrix workflow helpers: `msolve(A, b)`, `rref(...)`, `nullspace(...)`, and `linsolve(...)`.
- Enable function-exponent parsing with SymPy transform support (for example `sin^2(x)`).
- Add `:linalg` / `:la` command with linear algebra quick-reference templates.
- Expand examples/tutorial/docs to highlight linear-system and exact symbolic workflows.

- Add progressive help aliases (`?`, `??`, `???`) in one-shot mode and REPL for feature discovery.
- Expand help/tutorial/example text with an exact huge-integer arithmetic demo (`10^100000 + 1 - 10^100000`).
- Update contributor-facing docs to reflect the new discoverability flow.

## 0.1.9 - 2026-02-20

- Add human-friendly `ode ...` alias input for solving ODEs (including optional initial conditions like `y(0)=1`).
- Improve `:ode` help text with a beginner-first readable format.
- Render `ode ...` plain-mode solutions as `y(x) = ...` instead of raw `Eq(...)`.

## 0.1.8 - 2026-02-20

- Add `scripts/checks.sh` to run the standard test and coverage gates.
- Add `scripts/release.sh <version>` to automate local checks plus tag-based release push steps.
- Document scripted development/release workflow in contributor and README docs.

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
