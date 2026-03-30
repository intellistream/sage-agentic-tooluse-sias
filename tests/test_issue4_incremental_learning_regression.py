"""Regression and baseline tests for issue #4 incremental learning coverage."""

from __future__ import annotations

import time
from typing import Any

from sage_sias.continual_learner import OnlineContinualLearner
from sage_sias.coreset_selector import CoresetSelector


def _make_sample(sample_id: str, text: str, loss: float = 0.0) -> dict[str, Any]:
    return {
        "sample_id": sample_id,
        "text": text,
        "metadata": {"loss": loss},
    }


def _build_dataset(size: int, *, prefix: str = "s") -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index in range(size):
        topic = "weather" if index % 3 == 0 else ("finance" if index % 3 == 1 else "travel")
        text = f"{topic} sample number {index}"
        loss = float(index) / float(max(size, 1))
        samples.append(_make_sample(sample_id=f"{prefix}{index}", text=text, loss=loss))
    return samples


def test_loss_topk_selection_is_deterministic_with_metrics() -> None:
    selector = CoresetSelector(strategy="loss_topk", random_seed=42)
    samples = _build_dataset(30)

    metrics = {sample["sample_id"]: float(i) for i, sample in enumerate(samples)}
    selected = selector.select(samples=samples, target_size=5, metrics=metrics)

    selected_ids = [sample["sample_id"] for sample in selected]
    assert selected_ids == ["s29", "s28", "s27", "s26", "s25"]


def test_online_continual_learner_prunes_to_buffer_size() -> None:
    selector = CoresetSelector(strategy="loss_topk", random_seed=7)
    learner = OnlineContinualLearner(
        buffer_size=10,
        replay_ratio=0.5,
        selector=selector,
        random_seed=7,
    )

    first_batch = _build_dataset(8, prefix="a")
    second_batch = _build_dataset(12, prefix="b")

    learner.update_buffer(first_batch)
    training_batch = learner.update_buffer(second_batch)

    assert learner.buffer_len == 10
    second_ids = {sample["sample_id"] for sample in second_batch}
    available_for_replay = [
        sample for sample in learner.buffer if sample["sample_id"] not in second_ids
    ]
    expected_replay = min(max(1, int(len(second_batch) * 0.5)), len(available_for_replay))
    assert len(training_batch) == len(second_batch) + expected_replay


def test_replay_samples_exclude_current_batch_ids() -> None:
    learner = OnlineContinualLearner(buffer_size=20, replay_ratio=0.5, random_seed=11)
    seed_batch = _build_dataset(15)
    learner.update_buffer(seed_batch)

    new_batch = _build_dataset(6)
    training_batch = learner.update_buffer(new_batch)

    new_ids = {sample["sample_id"] for sample in new_batch}
    replay_ids = {sample["sample_id"] for sample in training_batch[len(new_batch) :]}
    assert not replay_ids & new_ids


def test_coreset_hybrid_baseline_runtime() -> None:
    selector = CoresetSelector(strategy="hybrid", random_seed=13)
    samples = _build_dataset(900)

    start = time.perf_counter()
    selected = selector.select(samples=samples, target_size=90)
    elapsed = time.perf_counter() - start

    assert len(selected) == 90
    assert elapsed < 10.0


def test_continual_update_baseline_runtime() -> None:
    learner = OnlineContinualLearner(
        buffer_size=512,
        replay_ratio=0.25,
        selector=CoresetSelector(strategy="loss_topk", random_seed=17),
        random_seed=17,
    )

    start = time.perf_counter()
    for round_id in range(8):
        batch = [
            _make_sample(
                sample_id=f"r{round_id}_s{idx}",
                text=f"batch {round_id} text {idx}",
                loss=float(idx) / 128.0,
            )
            for idx in range(128)
        ]
        learner.update_buffer(batch)
    elapsed = time.perf_counter() - start

    assert learner.buffer_len == 512
    assert elapsed < 8.0
