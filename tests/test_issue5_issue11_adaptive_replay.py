"""Tests for issue #5 adaptive replay and issue #11 reproducibility traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sage_sias.continual_learner import OnlineContinualLearner
from sage_sias.coreset_selector import CoresetSelector


def _make_sample(
    sample_id: str,
    text: str,
    *,
    loss: float = 0.0,
    topic: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"loss": loss}
    if topic is not None:
        metadata["topic"] = topic
    return {"sample_id": sample_id, "text": text, "metadata": metadata}


def _read_jsonl(file_path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line]


def test_no_drift_keeps_baseline_ratio_and_hybrid_strategy() -> None:
    learner = OnlineContinualLearner(
        buffer_size=16,
        replay_ratio=0.25,
        selector=CoresetSelector(strategy="hybrid", random_seed=3),
        random_seed=3,
    )
    first_batch = [
        _make_sample(f"a{i}", f"weather stable sample {i}", loss=0.1, topic="weather")
        for i in range(8)
    ]
    second_batch = [
        _make_sample(f"b{i}", f"weather stable sample {i}", loss=0.1, topic="weather")
        for i in range(8)
    ]

    learner.update_buffer(first_batch)
    learner.update_buffer(second_batch)

    assert learner.drift_score < 0.15
    assert learner.forgetting_score == 0.0
    assert learner.adaptive_replay_ratio == 0.25
    assert learner.selector.strategy == "hybrid"


def test_drift_and_forgetting_raise_replay_ratio_and_switch_strategy() -> None:
    learner = OnlineContinualLearner(
        buffer_size=20,
        replay_ratio=0.2,
        selector=CoresetSelector(strategy="hybrid", random_seed=5),
        random_seed=5,
    )
    stable_batch = [
        _make_sample(f"s{i}", f"weather routine sample {i}", loss=0.05, topic="weather")
        for i in range(10)
    ]
    shifted_batch = [
        _make_sample(
            f"n{i}",
            f"finance anomaly alert sample {i}",
            loss=0.95,
            topic="finance",
        )
        for i in range(10)
    ]

    learner.update_buffer(stable_batch)
    learner.update_buffer(shifted_batch)

    assert learner.drift_score > 0.45
    assert learner.forgetting_score > 0.2
    assert learner.adaptive_replay_ratio > 0.2
    assert learner.selector.strategy == "loss_topk"


def test_trace_artifacts_and_same_seed_are_stable(tmp_path: Path) -> None:
    trace_dir_a = tmp_path / "run_a"
    trace_dir_b = tmp_path / "run_b"
    batches = [
        [_make_sample(f"a{i}", f"weather report {i}", loss=0.1, topic="weather") for i in range(6)],
        [_make_sample(f"b{i}", f"travel digest {i}", loss=0.6, topic="travel") for i in range(6)],
        [_make_sample(f"c{i}", f"travel digest {i}", loss=0.6, topic="travel") for i in range(6)],
    ]

    learner_a = OnlineContinualLearner(
        buffer_size=12,
        replay_ratio=0.25,
        selector=CoresetSelector(strategy="hybrid", random_seed=9),
        random_seed=9,
        trace_dir=trace_dir_a,
    )
    learner_b = OnlineContinualLearner(
        buffer_size=12,
        replay_ratio=0.25,
        selector=CoresetSelector(strategy="hybrid", random_seed=9),
        random_seed=9,
        trace_dir=trace_dir_b,
    )

    outputs_a: list[list[str]] = []
    outputs_b: list[list[str]] = []
    for batch in batches:
        outputs_a.append([sample["sample_id"] for sample in learner_a.update_buffer(batch)])
        outputs_b.append([sample["sample_id"] for sample in learner_b.update_buffer(batch)])

    assert outputs_a == outputs_b
    assert learner_a.trace_history == learner_b.trace_history

    metrics_a = _read_jsonl(trace_dir_a / "metrics.jsonl")
    metrics_b = _read_jsonl(trace_dir_b / "metrics.jsonl")
    assert metrics_a == metrics_b
    assert len(metrics_a) == len(batches)

    summary_content = (trace_dir_a / "summary.csv").read_text(encoding="utf-8")
    assert "round_id,drift_score,forgetting_score,adaptive_replay_ratio" in summary_content

    config_snapshot = (trace_dir_a / "config.snapshot.yaml").read_text(encoding="utf-8")
    assert "buffer_size: 12" in config_snapshot
    assert 'default_selector_strategy: "hybrid"' in config_snapshot
