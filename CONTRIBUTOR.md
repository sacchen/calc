# Contributor Guide

This project is a terminal-first symbolic calculator (`phil`) built on SymPy.
Changes should improve correctness, safety, and practical UX for math workflows.

## Development Setup

```bash
uv run --group dev pytest
uv run phil '2+2'
uv run phil
```

## Testing Strategy (Required)

Run these before pushing:

```bash
uv run --group dev pytest
uv run --group dev pytest --cov=calc --cov-report=term-missing --cov-fail-under=90
```

Test categories:

- `unit`: pure behavior of parser/evaluator/format helpers.
- `integration`: process-level CLI/REPL behavior.
- `regression`: fixed bug cases that must never regress.

Property tests (`hypothesis`) are used for high-value invariants in numeric/symbolic behavior.

## Perfect Commit Standard

Adopt a "perfect commit" bar:

1. One logical change per commit.
2. Commit is releasable on its own (no broken intermediate states).
3. Tests accompany behavior changes.
4. Docs accompany user-facing changes.
5. Exclude unrelated cleanup from the same commit.

Before committing:

- Review staged diff only: `git diff --staged`
- Verify tests:
  - `uv run --group dev pytest`
  - `uv run --group dev pytest --cov=calc --cov-report=term-missing --cov-fail-under=90`

Commit message guidance:

- Subject: imperative and specific, <=72 chars.
- Body: explain why, summarize what changed, note user impact.

## CI Expectations

CI runs:

- tests + coverage on Python `3.12` and `3.13`
- install smoke test (`uv tool install .`, then run `phil`)

If your change adds behavior, add/adjust tests in the correct category.

## Adding or Changing Math Operations

1. Add required import(s) in `src/calc/core.py`.
2. Expose user-facing entry in `LOCALS_DICT`.
3. Add tests in `tests/test_core.py` (and regression tests if bug-fix related).
4. Update `README.md` and `KNOWLEDGE.md` if user-visible.
5. Run full suite.

## Safety Rules

- Do not loosen parser globals in `GLOBAL_DICT`.
- Keep blocked-token and input-size protections unless there is a measured reason.
- Never execute user input outside SymPy parse/eval path.

## UX Rules

- Output remains terminal-first and script-friendly.
- Errors are concise: `E:` + actionable `hint:`.
- Keep REPL behavior consistent with one-shot mode (`--strict`, `--format`, `--no-simplify`).

## Scope Guardrails

Avoid unnecessary complexity:

- plugin systems
- unrelated persistence layers
- large configuration frameworks

When adding complexity, explain the user value and testing impact in the PR.
