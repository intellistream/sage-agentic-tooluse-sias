# GitHub Issue Snapshot And 3-Agent Parallel Plan

## Purpose

This document freezes the current open-issue picture for
`intellistream/sage-agentic-tooluse-sias` and converts it into an execution plan
that can be split across 3 parallel agents.

For day-to-day progress tracking, see `docs/issue-status-tracker.md`.

## Working Constraints

- Repo layer: L3 algorithm library only.
- Keep runtime/service-neutral; no L4+ dependencies.
- No fallback logic. Fail fast.
- Do not create `.venv` or `venv`.
- Prefer direct caller updates over compatibility shims.

## Open Issue Snapshot

### Issue #1

`[Boundary Refactor][L3] 清理模块边界与依赖职责（Phase 1）`

Main tasks:

- Define repo boundary: in-scope / out-of-scope / forbidden imports.
- Audit cross-layer imports, dynamic imports, scripts, tests, and CLI paths.
- Identify compatibility layers and remove at least one unnecessary shim path.
- Audit `pyproject.toml` against real runtime imports.
- Split remaining work into follow-up PR-sized chunks.

### Issue #2

Core/external dependency boundary cleanup.

Main tasks:

- Treat `sample_id` as the only canonical identifier.
- Remove compatibility alias patterns from core types.
- Remove `dialog_id` and object-id fallback paths from core algorithms.
- Keep exports and docs aligned with canonical APIs only.

Note:

- Direct GitHub page fetch was not stable in the current environment.
- Local evidence for this issue exists in
  `docs/adr/0002-core-external-dependency-boundary.md` and
  `tests/test_issue2_core_dependency_boundary.py`.

### Issue #3

`[Wave B][tooluse-sias][B2] Torch 依赖最小化与证据化保留`

Status:

- Marked completed in issue discussion.

Delivered scope:

- Remove torch-only dependency declaration and related docs drift.
- Add ADR and regression test.

Planning decision:

- Do not spend a primary agent slot here unless regression appears.

### Issue #5

Drift-aware online continual learning.

Main tasks:

- Add minimal drift detection using token/topic distribution and loss changes.
- Add adaptive `replay_ratio` scheduling.
- Support online strategy switching among `loss_topk`, `diversity`, and `hybrid`.
- Expose observable metrics:
  `drift_score`, `forgetting_score`, `adaptive_replay_ratio`.
- Update README and docs.

### Issue #6

Streaming coreset selection.

Main tasks:

- Add incremental coreset maintenance.
- Introduce short-term / long-term candidate pools.
- Avoid frequent full recomputation.
- Add complexity notes and parameters.
- Add minimal performance benchmark script.
- Document when to use batch vs streaming coreset.

### Issue #7

Unified importance scorer.

Main tasks:

- Define a unified `importance_score` interface.
- Combine loss + diversity + novelty into one configurable scorer.
- Connect scorer into both learner and selector decisions.
- Add score explanation fields for debugging.
- Document parameters and defaults.

### Issue #8

Tool-use benchmark and ablation matrix.

Main tasks:

- Build a minimal reproducible evaluation dataset.
- Add metrics for success proxy, sample efficiency, forgetting, and runtime cost.
- Add ablations for:
  - no replay
  - fixed replay ratio
  - dynamic replay ratio
  - no coreset / batch coreset / streaming coreset
- Generate markdown and CSV reports.

### Issue #9

Cross-repo integration with `sage-agentic-tooluse`.

Main tasks:

- Define minimal external SIAS interface.
- Provide an integration example or demo.
- Add contract tests with mocks.
- Write migration notes with no compatibility branch.

### Issue #10

Benchmark-facing contract v1.

Main tasks:

- Define serializable `SIASConfig` with versioning.
- Freeze input/output schema for benchmark use.
- Include score explanation fields in result schema.
- Add contract tests for schema validation and breaking-change detection.
- Add `examples/benchmark_adapter_minimal.py`.

### Issue #11

Reproducibility infrastructure.

Main tasks:

- Unify random seed control across learner and selector.
- Add per-round traces:
  `replay_ratio`, `drift_score`, selected-id summary.
- Standardize artifact layout:
  `metrics.jsonl`, `summary.csv`, `config.snapshot.yaml`.
- Add regression test for same-seed stability.

## Dependency View

### Foundation

These issues define the core contract and should be treated as blockers for
follow-on feature work:

- #1 boundary definition
- #2 canonical sample contract

### Feature Layer

These issues build algorithm capability on top of the stable core:

- #5 adaptive continual learner
- #6 streaming coreset
- #7 unified scorer
- #11 reproducibility

### Integration And Evaluation Layer

These issues package the system for upper-layer usage and paper-ready evidence:

- #8 benchmark and ablation
- #9 cross-repo integration
- #10 benchmark-facing contract

## Current Repo Signals

Observed from the current repository state:

- Tests already exist for `#2`, `#3`, and incremental regression coverage.
- Current source still appears inconsistent with `#2` expectations because core
  code keeps `dialog_id` fallback logic and a compatibility alias.
- `#3` appears documented as completed, but should remain protected by
  regression tests.

This means `#2` should be treated as an immediate cleanup item before adding
new adaptive features.

## 3-Agent Parallel Plan

### Agent 1: Boundary And Contract

Primary scope:

- Issue `#1`
- Issue `#2`
- Prep work for Issue `#10`

Deliverables:

- Boundary document update.
- Core type cleanup with strict `sample_id` enforcement.
- Removal of compatibility alias / fallback logic.
- Contract draft for config and I/O schema.
- Regression tests for boundary behavior.

Files likely touched:

- `src/sage_sias/types.py`
- `src/sage_sias/continual_learner.py`
- `src/sage_sias/coreset_selector.py`
- `src/sage_sias/__init__.py`
- `README.md`
- `docs/adr/*`
- `tests/test_issue2_core_dependency_boundary.py`

Reason this agent goes first:

- It reduces ambiguity for the other two agents.
- It minimizes later merge conflicts around sample schema and public API.

### Agent 2: Learner Adaptation And Trace

Primary scope:

- Issue `#5`
- Issue `#11`

Deliverables:

- Drift detection module or helper logic.
- Adaptive replay scheduling in `OnlineContinualLearner`.
- Trace/artifact outputs and deterministic seed handling.
- Tests for drift-triggered replay changes and same-seed stability.
- README/docs updates for learner behavior.

Files likely touched:

- `src/sage_sias/continual_learner.py`
- new helper module under `src/sage_sias/`
- `README.md`
- `tests/` new learner and reproducibility tests

Reason this is parallel-safe:

- It mainly owns learner internals.
- It can proceed once Agent 1 freezes the canonical sample contract.

### Agent 3: Selector Evolution And Scoring

Primary scope:

- Issue `#6`
- Issue `#7`

Deliverables:

- Streaming coreset API and internal data structures.
- Unified importance scorer and explanation fields.
- Benchmark micro-script for selector runtime.
- Tests for streaming edge cases and scoring monotonicity.
- Docs for batch vs streaming selector usage.

Files likely touched:

- `src/sage_sias/coreset_selector.py`
- possible new scorer module under `src/sage_sias/`
- `README.md`
- `tests/` new selector and scorer tests
- `examples/` or `scripts/` benchmark helper

Reason this is parallel-safe:

- It mainly owns selector-side logic.
- It shares only the core sample contract with Agent 1.

## Merge Strategy

Recommended order:

1. Agent 1 merges first.
2. Agent 2 rebases onto Agent 1.
3. Agent 3 rebases onto Agent 1.
4. After Agent 2 and Agent 3 land, finish `#10`.
5. Then build `#8` and `#9` on the merged feature surface.

## Suggested Execution Waves

### Wave 0

- Freeze issue snapshot in docs.
- Confirm canonical sample schema and no-fallback rule.

### Wave 1

- Agent 1: `#1 + #2`
- Agent 2: start `#5 + #11` after contract freeze
- Agent 3: start `#6 + #7` after contract freeze

### Wave 2

- Finish `#10` benchmark-facing contract using merged outputs from Wave 1.

### Wave 3

- Build `#8` benchmark and ablation around the final learner + selector APIs.
- Build `#9` integration example and contract tests against the stabilized API.

## Paper-Oriented Prioritization

If the goal is a publishable research storyline, prioritize in this order:

1. `#2` for clean and defensible core contract.
2. `#5` for adaptive continual-learning novelty.
3. `#6` for streaming efficiency contribution.
4. `#7` for unified scoring story.
5. `#11` for reproducibility.
6. `#8` for experimental evidence and ablation.
7. `#9` and `#10` for ecosystem adoption and benchmark integration.

This ordering supports a stronger narrative:

- clean core contract
- adaptive learner
- efficient streaming selector
- unified scoring mechanism
- reproducible evaluation
- benchmark evidence
