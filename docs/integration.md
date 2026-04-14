# Integration Guide

## Goal

Provide a stable integration path from `sage-agentic-tooluse` to SIAS without
compatibility shims.

## Minimal Interface

Input sample schema:

- `sample_id: str`
- `text: str`
- `metadata: dict`

Output selection schema:

- `sample_id`
- `text`
- `metadata`
- `importance_score`
- `importance_breakdown`

## Integration Entry Point

Use `sage_sias.integration.select_samples_for_agentic_tooluse(...)`.

See runnable example:

- `examples/integration_sage_agentic_tooluse.py`

## Migration Rule

- Do not rely on historical compatibility aliases or alternate identifiers.
- Normalize upstream payloads to canonical `sample_id` before calling SIAS.
- Prefer direct migration to the contract v1 format over adding adapter shims.
