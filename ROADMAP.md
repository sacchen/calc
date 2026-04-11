# Roadmap

This roadmap defines the next two major planning horizons for `phil`.

## v0.3.0 - Workflow Depth

Goal: make day-to-day terminal math workflows materially faster and clearer.

### Scope

- Linear algebra command expansion:
  - Add `linalg eig`, `linalg det`, `linalg inv`, and `linalg nullspace`.
  - Keep one-shot and REPL behavior aligned with existing `linalg solve` and `linalg rref`.
- Equation-solving ergonomics:
  - Add a focused solve alias for equation/system workflows.
  - Prefer explicit errors and hints over implicit assumptions when unknowns are ambiguous.
  - Keep `solve(...)` focused on symbolic solving; if users try matrix-style input like `solve(A=..., B=...)`, steer them to `linalg solve` or `msolve(A, b)` with an explicit recovery hint instead of overloading `solve`.
- Parser and diagnostics quality:
  - Extend shorthand support where safe.
  - Always show rewrite/normalization hints when interpretation could surprise users.
- Scriptability improvements:
  - Tighten `--format json` behavior for matrix/tuple-heavy outputs.
  - Ensure output stays predictable for pipes and shell scripts.

### Non-Goals

- No graphing/plotting subsystem.
- No breaking changes to existing CLI flags or aliases.

### Exit Criteria

- New linalg subcommands are documented and tested (unit + integration + regression).
- One-shot and REPL parity tests cover new aliases and error behavior.
- Coverage gate stays at or above project threshold.

## v1.0.0 - Stability Contract

Goal: lock in a reliable long-term CLI contract suitable for production scripting and teaching workflows.

### Scope

- API/CLI stability contract:
  - Freeze core flag and alias semantics.
  - Publish compatibility/deprecation policy.
- Deterministic machine interfaces:
  - Define and document a stable JSON output contract.
  - Add regression coverage for deterministic field structure and ordering expectations.
- Safety and robustness:
  - Maintain parser hardening guarantees and blocked-token protections.
  - Expand fuzz/property checks around high-risk normalization and parser boundaries.
- Documentation maturity:
  - Publish a workflow cookbook (calc, ODE, linalg, symbolic solve).
  - Add migration and troubleshooting guidance.

### Non-Goals

- Full CAS feature parity with larger symbolic platforms.
- Broad plugin ecosystem before baseline contract is stable.

### Exit Criteria

- All release gates pass consistently across supported environments.
- JSON/scriptability guarantees are documented and covered by regression tests.
- Contributor docs reflect the final release process and stability guarantees.

## Candidate Sequencing

1. v0.3.0-alpha: linalg subcommand expansion + diagnostics updates.
2. v0.3.0: parser/JSON polishing + docs + parity/regression tests.
3. v1.0.0-rc1: contract freeze draft + regression hardening.
4. v1.0.0: stable contract release.
