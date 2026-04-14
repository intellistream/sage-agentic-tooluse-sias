"""Integration helpers for upstream tool-use policy layers."""

from __future__ import annotations

from typing import Any

from .contract import SIASConfig, run_selection_contract


def select_samples_for_agentic_tooluse(
    samples: list[dict[str, Any]],
    *,
    target_size: int,
    metrics: dict[str, float] | None = None,
    config: SIASConfig | None = None,
) -> dict[str, Any]:
    """Minimal stable adapter for upstream policy/trainer callers."""

    return run_selection_contract(
        config=config or SIASConfig(),
        samples=samples,
        target_size=target_size,
        metrics=metrics,
    )
