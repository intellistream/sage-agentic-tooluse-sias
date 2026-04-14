"""Tests for issue #6 streaming coreset and issue #7 importance scorer."""

from __future__ import annotations

from typing import Any

from sage_sias.continual_learner import OnlineContinualLearner
from sage_sias.coreset_selector import CoresetSelector


def _make_sample(
    sample_id: str,
    text: str,
    *,
    loss: float,
    topic: str | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {"loss": loss}
    if topic is not None:
        metadata["topic"] = topic
    return {"sample_id": sample_id, "text": text, "metadata": metadata}


def test_importance_score_is_monotonic_when_only_loss_changes() -> None:
    selector = CoresetSelector(strategy="hybrid", random_seed=11)
    samples = [
        _make_sample("a", "alpha sample", loss=0.1),
        _make_sample("b", "alpha sample", loss=0.5),
        _make_sample("c", "alpha sample", loss=0.9),
    ]

    breakdowns = selector.score_samples(samples)
    ordered_ids = [item.sample_id for item in breakdowns]

    assert ordered_ids[0] == "c"
    assert ordered_ids[-1] == "a"
    assert breakdowns[0].score >= breakdowns[1].score >= breakdowns[2].score


def test_streaming_selector_handles_empty_duplicates_and_extreme_target_size() -> None:
    selector = CoresetSelector(
        strategy="streaming",
        random_seed=13,
        streaming_window_size=4,
        long_term_pool_size=4,
    )

    assert selector.update_stream([], target_size=3) == []

    batch = [
        _make_sample("a", "weather first version", loss=0.1, topic="weather"),
        _make_sample("a", "weather updated version", loss=0.8, topic="weather"),
        _make_sample("b", "finance unique", loss=0.7, topic="finance"),
    ]
    selected = selector.update_stream(batch, target_size=10)

    selected_ids = [sample["sample_id"] for sample in selected]
    assert len(selected_ids) == len(set(selected_ids))
    assert set(selected_ids) == {"a", "b"}
    assert selector.streaming_pool_sizes["short_term"] <= 4


def test_streaming_selector_attaches_importance_explanations() -> None:
    selector = CoresetSelector(strategy="streaming", random_seed=17, long_term_pool_size=6)
    batch = [
        _make_sample("a", "weather pattern one", loss=0.2, topic="weather"),
        _make_sample("b", "finance pattern one", loss=0.8, topic="finance"),
        _make_sample("c", "travel pattern one", loss=0.5, topic="travel"),
    ]

    selected = selector.update_stream(batch, target_size=2)

    for sample in selected:
        metadata = sample["metadata"]
        assert "importance_score" in metadata
        assert "importance_breakdown" in metadata
        assert metadata["importance_breakdown"]["sample_id"] == sample["sample_id"]


def test_learner_and_selector_share_consistent_scored_retention() -> None:
    selector_for_expected = CoresetSelector(strategy="hybrid", random_seed=19)
    selector_for_learner = CoresetSelector(strategy="hybrid", random_seed=19)
    samples = [
        _make_sample("a", "weather high loss", loss=0.9, topic="weather"),
        _make_sample("b", "finance high loss", loss=0.8, topic="finance"),
        _make_sample("c", "weather low loss", loss=0.1, topic="weather"),
        _make_sample("d", "travel medium loss", loss=0.5, topic="travel"),
        _make_sample("e", "finance low loss", loss=0.2, topic="finance"),
    ]

    expected = selector_for_expected.select(samples=samples, target_size=3)
    learner = OnlineContinualLearner(
        buffer_size=3,
        replay_ratio=0.5,
        selector=selector_for_learner,
        random_seed=19,
    )
    learner.update_buffer(samples)

    expected_ids = [sample["sample_id"] for sample in expected]
    buffer_ids = [sample["sample_id"] for sample in learner.buffer_snapshot()]
    assert buffer_ids == expected_ids
