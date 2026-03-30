# sage-agentic-tooluse-sias Copilot Instructions

## Scope
- Package: `sage-agentic-tooluse-sias` — SIAS (Selective Incremental Adaptive Selection) continual learning component for tool-use agents.
- Layer: **L3** — algorithm library, no L4+ dependencies.

## Polyrepo Context (Important)
SAGE was restructured from a monorepo into a polyrepo. This is a **specialized L3 algorithm repo** providing continual-learning and coreset-selection capabilities for tool-use agents. It integrates with `sage-agentic-tooluse` and the `sage-libs` interface layer.

## Critical rules
- Keep runtime/service-neutral; no L4+ dependencies.
- Do not create new local virtual environments (`venv`/`.venv`); use the existing configured Python environment.
- No fallback logic; fail fast.

## Architecture focus
- `continual_learner.py` — incremental learning for tool selection.
- `coreset_selector.py` — coreset selection algorithms.
- `types.py` — shared type definitions.
- Registers into `sage-agentic-tooluse` and `sage-libs` factories.

## Dependencies
- **Depends on**: `isage-common` (L1), `isage-libs` (L3), `isage-agentic-tooluse` (L3).
- **Depended on by**: `sage-agentic-tooluse-benchmark`, application repos.

## Workflow
1. Make minimal implementation changes.
2. Run tests and update docs for behavior changes.

## Git Hooks (Mandatory)
- Never use `git commit --no-verify` or `git push --no-verify`.
- If hooks fail, fix the issue first.

## 🚫 NEVER_CREATE_DOT_VENV_MANDATORY

- 永远不要创建 `.venv` 或 `venv`（无任何例外）。
- NEVER create `.venv`/`venv` in this repository under any circumstance.
- 必须复用当前已配置的非-venv Python 环境（如现有 conda 环境）。
- If any script/task suggests creating a virtualenv, skip that step and continue with the existing environment.
