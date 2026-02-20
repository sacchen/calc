# AGENTS

Guidance for human/AI contributors working in this repository.

## Mission

Keep `phil` accurate, safe, and fast to use for real math workflows in a terminal.

## Non-Negotiables

- Do not weaken parser safety (`GLOBAL_DICT`, blocked tokens, input limits).
- Keep one-shot and REPL semantics aligned.
- Keep output predictable for piping/scripts.
- Add tests for every user-visible behavior change.

## Preferred Workflow

1. Implement smallest coherent change.
2. Add/adjust tests (`unit`, `integration`, `regression`).
3. Update docs (`README.md`, `DESIGN.md`, `KNOWLEDGE.md`, `CONTRIBUTOR.md`) if needed.
4. Run:
   - `uv run --group dev pytest`
   - `uv run --group dev pytest --cov=calc --cov-report=term-missing --cov-fail-under=90`

## Perfect Commit Protocol

Use "perfect commit" discipline for every change:

1. One logical change per commit.
2. Commit must build, test, and run in isolation.
3. Include tests for behavior changes or bug fixes.
4. Include docs updates for user-visible changes.
5. Keep unrelated refactors out of the same commit.

Commit message format:

- Subject: imperative, specific, <=72 chars.
- Body: why this change exists, what changed, and user impact.
- Footer (optional): issue/PR references.

Suggested pre-commit gate:

- `git diff --staged` is coherent and minimal.
- tests pass locally for touched areas (or full suite for broad changes).

## High-Value Areas

- Parser normalization and syntax sugar (`df/dt`, relaxed input).
- Error hint quality (`E:` + actionable `hint:`).
- Matrix/ODE workflow ergonomics.
- Formatting modes and copy/paste behavior.

## Avoid

- Hidden behavior that changes math semantics silently.
- Implicit defaults when ambiguity exists (prefer explicit error + hint).
- Breaking existing CLI flags without compatibility path.
