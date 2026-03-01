# ADR 0002: Separate SIAS algorithm core from external dependency conventions

## Status

Accepted

## Context

Issue `intellistream/sage-agentic-tooluse-sias#2` requires clear layering between continual-learning core and external dependency conventions.

Two boundary issues were present:

- compatibility alias in core types (`Sample = SIASSample`),
- legacy sample-id fallbacks (`dialog_id` / object id) inside core algorithms.

These patterns mixed historical integration assumptions into the algorithm core.

## Decision

- Keep canonical sample contract: `sample_id` is required.
- Remove compatibility alias from core types.
- Remove `dialog_id` and `id(...)` fallback paths from:
  - `CoresetSelector`
  - `OnlineContinualLearner`
- Keep docs and package exports aligned to canonical APIs only.

## Consequences

- Core algorithms are deterministic and framework-neutral.
- External adapters must normalize data before calling SIAS core APIs.
- No compatibility shim/alias path remains in core modules.
