# Repository Boundary (L3)

This repository is an L3 algorithm library for SIAS (sample-importance-aware
selection) used in tool-use continual learning.

## In-Scope

- Core sample schema and canonical contract (`sample_id`, `text`, `metadata`).
- Online continual learning replay buffer logic (`OnlineContinualLearner`).
- Coreset selection strategies (`CoresetSelector`).
- Deterministic behavior and reproducibility controls (seed plumbing).
- Lightweight documentation and tests for core behavior and boundaries.

## Out-Of-Scope

- Runtime/service orchestration, workers, queues, and serving.
- L4 application logic, UI, and production deployment glue.
- Dataset hosting, large benchmark corpora, and external data ingestion pipelines.
- Long-term compatibility shims for historical call sites.

## Forbidden Imports (Boundary Rule)

The algorithm core must remain runtime/service-neutral.

- No imports from L4 repos or application layers.
- No silent fallback logic (e.g., `dialog_id`, `id(...)`-based identifiers).
- No optional heavy dependencies unless there is code-level usage evidence and
  corresponding regression coverage.

## Fail-Fast Contract

- All samples must provide non-empty `sample_id`.
- Invalid input must raise immediately (no best-effort behavior in core).

