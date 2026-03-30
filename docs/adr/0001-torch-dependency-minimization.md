# ADR 0001: Torch dependency minimization

## Status

Accepted

## Context

Issue `intellistream/sage-agentic-tooluse-sias#3` requires clarifying whether `torch` is mandatory and minimizing unnecessary dependencies.

Audit results in this repository:

- No runtime imports of `torch` exist in core modules.
- `pyproject.toml` still declared a `torch` optional extra that had no code-level usage evidence.
- README installation section exposed a torch-specific install path without runtime dependency evidence.

## Decision

1. Remove `torch` optional dependency extra from `pyproject.toml`.
2. Keep optional dependency surface minimal: `dev` and `all` only.
3. Update README installation instructions to remove torch-specific installation guidance.
4. Add regression tests that assert there are no `torch` imports in repository Python modules and no `torch` dependency declarations in `pyproject.toml`.

## Consequences

- Dependency declarations now match actual runtime requirements.
- No compatibility/deprecation shim is added.
- Future introduction of `torch` must include explicit code-level evidence and test updates.
