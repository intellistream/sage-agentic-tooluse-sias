# ADR 0003: Incremental learning regression and baseline coverage

## Status

Accepted

## Context

Issue `intellistream/sage-agentic-tooluse-sias#4` requires explicit coverage for:

- core incremental-learning correctness,
- reproducible baseline runtime checks.

The repository previously lacked tests that jointly validate buffer pruning behavior,
replay assembly constraints, and baseline execution time for SIAS core paths.

## Decision

1. Add regression tests for deterministic `loss_topk` selection.
2. Add regression tests for `OnlineContinualLearner` buffer-size pruning and replay exclusion.
3. Add lightweight baseline runtime tests for:
   - `CoresetSelector(strategy="hybrid")` on medium input,
   - repeated `OnlineContinualLearner.update_buffer` rounds.
4. Keep baseline thresholds loose and deterministic enough for CI stability while still catching major regressions.

## Consequences

- Core algorithm behavior is protected by executable regression tests.
- Baseline runtime regressions become visible in regular test runs.
- No compatibility path is introduced; canonical APIs remain unchanged.
