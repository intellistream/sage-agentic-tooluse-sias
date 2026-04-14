"""Benchmark-facing SIAS contract v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .continual_learner import OnlineContinualLearner
from .coreset_selector import CoresetSelector
from .importance_scorer import ImportanceScorer, ImportanceWeights


SIAS_CONTRACT_VERSION = "sias-benchmark-v1"


@dataclass(slots=True)
class SIASConfig:
    version: str = SIAS_CONTRACT_VERSION
    selector_strategy: str = "hybrid"
    buffer_size: int = 128
    replay_ratio: float = 0.25
    random_seed: int = 17
    enable_adaptive_replay: bool = True
    enable_strategy_switch: bool = True
    streaming_window_size: int = 128
    replacement_temperature: float = 0.5
    scorer_weights: dict[str, float] = field(
        default_factory=lambda: {"loss": 0.5, "diversity": 0.3, "novelty": 0.2}
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SIASConfig":
        if payload.get("version") not in (None, SIAS_CONTRACT_VERSION):
            raise ValueError(
                f"Unsupported SIAS contract version: {payload.get('version')!r}"
            )
        merged = cls().to_dict()
        merged.update(payload)
        return cls(**merged)


def validate_input_samples(samples: list[dict[str, Any]]) -> None:
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise TypeError(f"Sample at index {index} must be a dict")
        sample_id = sample.get("sample_id")
        text = sample.get("text")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"Sample at index {index} must provide non-empty 'sample_id'")
        if not isinstance(text, str):
            raise ValueError(f"Sample at index {index} must provide string 'text'")
        metadata = sample.get("metadata")
        if metadata is not None and not isinstance(metadata, dict):
            raise ValueError(f"Sample at index {index} metadata must be a dict when provided")


def build_selector(config: SIASConfig) -> CoresetSelector:
    weights = ImportanceWeights(**config.scorer_weights)
    return CoresetSelector(
        strategy=config.selector_strategy,
        random_seed=config.random_seed,
        streaming_window_size=config.streaming_window_size,
        replacement_temperature=config.replacement_temperature,
        importance_scorer=ImportanceScorer(weights=weights),
    )


def build_learner(config: SIASConfig) -> OnlineContinualLearner:
    selector = build_selector(config)
    return OnlineContinualLearner(
        buffer_size=config.buffer_size,
        replay_ratio=config.replay_ratio,
        selector=selector,
        random_seed=config.random_seed,
        enable_adaptive_replay=config.enable_adaptive_replay,
        enable_strategy_switch=config.enable_strategy_switch,
    )


def run_selection_contract(
    *,
    config: SIASConfig,
    samples: list[dict[str, Any]],
    target_size: int,
    metrics: dict[str, float] | None = None,
) -> dict[str, Any]:
    validate_input_samples(samples)
    selector = build_selector(config)
    selected = selector.select(samples=samples, target_size=target_size, metrics=metrics)
    return {
        "version": config.version,
        "config": config.to_dict(),
        "selected": [_serialize_selected_sample(sample) for sample in selected],
    }


def _serialize_selected_sample(sample: dict[str, Any]) -> dict[str, Any]:
    metadata = sample.get("metadata", {})
    importance_breakdown = metadata.get("importance_breakdown", {})
    return {
        "sample_id": sample["sample_id"],
        "text": sample["text"],
        "metadata": metadata,
        "importance_score": metadata.get("importance_score", 0.0),
        "importance_breakdown": importance_breakdown,
    }
