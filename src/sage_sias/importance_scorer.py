"""Unified importance scorer for SIAS selection decisions."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ImportanceWeights:
    loss: float = 0.5
    diversity: float = 0.3
    novelty: float = 0.2


@dataclass(slots=True)
class ImportanceScoreBreakdown:
    sample_id: str
    score: float
    loss_component: float
    diversity_component: float
    novelty_component: float

    def as_dict(self) -> dict[str, float | str]:
        return {
            "sample_id": self.sample_id,
            "score": self.score,
            "loss_component": self.loss_component,
            "diversity_component": self.diversity_component,
            "novelty_component": self.novelty_component,
        }


class ImportanceScorer:
    """Compute interpretable loss+diversity+novelty scores."""

    def __init__(
        self,
        *,
        metric_key: str = "loss",
        weights: ImportanceWeights | None = None,
    ) -> None:
        self.metric_key = metric_key
        self.weights = weights or ImportanceWeights()

    def score_samples(
        self,
        samples: Sequence[Any],
        *,
        metrics: dict[str, float] | None,
        get_sample_id: callable,
        get_text: callable,
        get_metadata: callable,
        reference_samples: Sequence[Any] | None = None,
    ) -> dict[str, ImportanceScoreBreakdown]:
        if not samples:
            return {}

        features = {get_sample_id(sample): self._text_features(get_text(sample)) for sample in samples}
        reference_features = {
            get_sample_id(sample): self._text_features(get_text(sample))
            for sample in (reference_samples or [])
        }

        raw_loss: dict[str, float] = {}
        raw_diversity: dict[str, float] = {}
        raw_novelty: dict[str, float] = {}

        for sample in samples:
            sample_id = get_sample_id(sample)
            metadata = get_metadata(sample)
            raw_loss[sample_id] = self._loss_value(sample_id, metadata, metrics)
            raw_diversity[sample_id] = self._diversity_value(sample_id, features)
            raw_novelty[sample_id] = self._novelty_value(
                sample_id,
                features,
                reference_features,
            )

        normalized_loss = self._normalize(raw_loss)
        normalized_diversity = self._normalize(raw_diversity)
        normalized_novelty = self._normalize(raw_novelty)

        breakdowns: dict[str, ImportanceScoreBreakdown] = {}
        for sample in samples:
            sample_id = get_sample_id(sample)
            loss_component = normalized_loss[sample_id]
            diversity_component = normalized_diversity[sample_id]
            novelty_component = normalized_novelty[sample_id]
            score = (
                (self.weights.loss * loss_component)
                + (self.weights.diversity * diversity_component)
                + (self.weights.novelty * novelty_component)
            )
            breakdowns[sample_id] = ImportanceScoreBreakdown(
                sample_id=sample_id,
                score=score,
                loss_component=loss_component,
                diversity_component=diversity_component,
                novelty_component=novelty_component,
            )
        return breakdowns

    def _loss_value(
        self,
        sample_id: str,
        metadata: dict[str, Any],
        metrics: dict[str, float] | None,
    ) -> float:
        if metrics and sample_id in metrics:
            return float(metrics[sample_id])
        metric_value = metadata.get(self.metric_key)
        if isinstance(metric_value, (int, float)):
            return float(metric_value)
        return 0.0

    def _diversity_value(self, sample_id: str, features: dict[str, Counter[str]]) -> float:
        feature = features[sample_id]
        others = [other_id for other_id in features if other_id != sample_id]
        if not others:
            return 1.0
        max_similarity = max(
            self._cosine_similarity(feature, features[other_id]) for other_id in others
        )
        return 1.0 - max_similarity

    def _novelty_value(
        self,
        sample_id: str,
        features: dict[str, Counter[str]],
        reference_features: dict[str, Counter[str]],
    ) -> float:
        feature = features[sample_id]
        if not reference_features:
            return self._feature_norm(feature)
        max_similarity = max(
            self._cosine_similarity(feature, ref_feature)
            for ref_feature in reference_features.values()
        )
        return 1.0 - max_similarity

    def _normalize(self, values: dict[str, float]) -> dict[str, float]:
        if not values:
            return {}
        min_value = min(values.values())
        max_value = max(values.values())
        if math.isclose(min_value, max_value):
            return {key: 1.0 for key in values}
        return {
            key: (value - min_value) / (max_value - min_value)
            for key, value in values.items()
        }

    def _text_features(self, text: str) -> Counter[str]:
        tokens = [token for token in text.lower().split() if len(token) > 2]
        counts = Counter(tokens)
        total = sum(counts.values()) or 1.0
        for key in counts:
            counts[key] /= total
        return counts

    def _feature_norm(self, features: Counter[str]) -> float:
        return math.sqrt(sum(value * value for value in features.values()))

    def _cosine_similarity(self, left: Counter[str], right: Counter[str]) -> float:
        keys = left.keys() & right.keys()
        if not keys:
            return 0.0
        return sum(left[key] * right[key] for key in keys)
