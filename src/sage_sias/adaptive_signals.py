"""Adaptive signal helpers for online continual learning."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BatchProfile:
    topic_distribution: dict[str, float]
    token_distribution: dict[str, float]
    mean_loss: float
    batch_size: int


@dataclass(slots=True)
class AdaptiveSignalSummary:
    drift_score: float
    forgetting_score: float
    topic_shift: float
    token_shift: float
    loss_shift: float


@dataclass(slots=True)
class TraceRecord:
    round_id: int
    drift_score: float
    forgetting_score: float
    adaptive_replay_ratio: float
    selector_strategy: str
    buffer_size: int
    new_batch_size: int
    replay_size: int
    selected_ids: list[str]
    replay_ids: list[str]


def build_batch_profile(
    samples: list[Any],
    *,
    metric_key: str,
    metrics: dict[str, float] | None,
    get_sample_id: callable,
    get_text: callable,
    get_metadata: callable,
) -> BatchProfile:
    topic_counts: Counter[str] = Counter()
    token_counts: Counter[str] = Counter()
    losses: list[float] = []

    for sample in samples:
        sample_id = get_sample_id(sample)
        text = get_text(sample)
        metadata = get_metadata(sample)

        topic_counts[_extract_topic(text, metadata)] += 1
        token_counts.update(_extract_tokens(text))

        if metrics and sample_id in metrics:
            losses.append(float(metrics[sample_id]))
        else:
            metric_value = metadata.get(metric_key)
            if isinstance(metric_value, (int, float)):
                losses.append(float(metric_value))

    return BatchProfile(
        topic_distribution=_normalize_counts(topic_counts),
        token_distribution=_normalize_counts(token_counts),
        mean_loss=(sum(losses) / len(losses)) if losses else 0.0,
        batch_size=len(samples),
    )


def compare_profiles(
    previous: BatchProfile | None,
    current: BatchProfile,
    *,
    running_loss_mean: float | None,
) -> AdaptiveSignalSummary:
    if previous is None:
        return AdaptiveSignalSummary(
            drift_score=0.0,
            forgetting_score=0.0,
            topic_shift=0.0,
            token_shift=0.0,
            loss_shift=0.0,
        )

    topic_shift = _distribution_distance(
        previous.topic_distribution,
        current.topic_distribution,
    )
    token_shift = _distribution_distance(
        previous.token_distribution,
        current.token_distribution,
    )
    loss_shift = min(
        1.0,
        abs(current.mean_loss - previous.mean_loss) / (1.0 + abs(previous.mean_loss)),
    )
    drift_score = min(1.0, (topic_shift + token_shift + loss_shift) / 3.0)

    if running_loss_mean is None:
        forgetting_score = 0.0
    else:
        forgetting_score = min(
            1.0,
            max(0.0, current.mean_loss - running_loss_mean) / (1.0 + abs(running_loss_mean)),
        )

    return AdaptiveSignalSummary(
        drift_score=drift_score,
        forgetting_score=forgetting_score,
        topic_shift=topic_shift,
        token_shift=token_shift,
        loss_shift=loss_shift,
    )


def update_running_loss_mean(
    current_value: float | None,
    new_value: float,
    *,
    momentum: float = 0.8,
) -> float:
    if current_value is None:
        return new_value
    return (momentum * current_value) + ((1.0 - momentum) * new_value)


def write_config_snapshot(file_path: Path, payload: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in payload.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=True)}")
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_metrics_jsonl(file_path: Path, record: TraceRecord) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=True) + "\n")


def _extract_topic(text: str, metadata: dict[str, Any]) -> str:
    topic = metadata.get("topic")
    if isinstance(topic, str) and topic:
        return topic.lower()
    tokens = _extract_tokens(text)
    if tokens:
        return tokens[0]
    return "unknown"


def _extract_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 2]


def _normalize_counts(counter: Counter[str]) -> dict[str, float]:
    total = float(sum(counter.values()))
    if total <= 0:
        return {}
    return {key: counter[key] / total for key in sorted(counter)}


def _distribution_distance(left: dict[str, float], right: dict[str, float]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    return min(1.0, sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys) / 2.0)
