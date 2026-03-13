"""
Coreset Selection for Efficient Training

Implements lightweight coreset selection strategies that identify the most
valuable samples for training, reducing computational cost while maintaining
model quality.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True)
class SelectionSummary:
    total_samples: int
    selected_samples: int
    strategy: str


@runtime_checkable
class SampleProtocol(Protocol):
    @property
    def sample_id(self) -> str: ...

    @property
    def text(self) -> str: ...

    @property
    def metadata(self) -> dict[str, Any]: ...


SampleT = Any


class CoresetSelector:
    STRATEGIES = ("loss_topk", "diversity", "hybrid", "random")

    def __init__(
        self,
        strategy: str = "loss_topk",
        metric_key: str = "loss",
        diversity_temperature: float = 0.7,
        random_seed: int = 13,
    ) -> None:
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}. Choose from {self.STRATEGIES}")

        self.strategy = strategy
        self.metric_key = metric_key
        self.diversity_temperature = diversity_temperature
        self._rng = random.Random(random_seed)

    def select(
        self,
        samples: Sequence[SampleT],
        *,
        target_size: int | None,
        metrics: dict[str, float] | None = None,
    ) -> list[SampleT]:
        if target_size is None or target_size <= 0 or target_size >= len(samples):
            return list(samples)

        if self.strategy == "loss_topk":
            return self._select_loss(samples, target_size, metrics)
        if self.strategy == "diversity":
            return self._select_diversity(samples, target_size)
        if self.strategy == "hybrid":
            return self._select_hybrid(samples, target_size, metrics)
        return self._select_random(samples, target_size)

    def summary(self, original_size: int, selected_size: int) -> SelectionSummary:
        return SelectionSummary(
            total_samples=original_size,
            selected_samples=selected_size,
            strategy=self.strategy,
        )

    def _select_loss(
        self,
        samples: Sequence[SampleT],
        target_size: int,
        metrics: dict[str, float] | None,
    ) -> list[SampleT]:
        def score(sample: SampleT) -> float:
            sample_id = self._get_sample_id(sample)
            if metrics and sample_id in metrics:
                return metrics[sample_id]
            meta = self._get_metadata(sample)
            meta_val = meta.get(self.metric_key)
            if isinstance(meta_val, (int, float)):
                return float(meta_val)
            return 0.0

        ranked = sorted(samples, key=score, reverse=True)
        return list(ranked[:target_size])

    def _select_random(
        self,
        samples: Sequence[SampleT],
        target_size: int,
    ) -> list[SampleT]:
        return self._rng.sample(list(samples), target_size)

    def _select_hybrid(
        self,
        samples: Sequence[SampleT],
        target_size: int,
        metrics: dict[str, float] | None,
    ) -> list[SampleT]:
        loss_portion = int(target_size * 0.6)
        div_portion = target_size - loss_portion

        top_loss = self._select_loss(samples, loss_portion or 1, metrics)
        top_loss_ids = {self._get_sample_id(s) for s in top_loss}

        remaining = [s for s in samples if self._get_sample_id(s) not in top_loss_ids]
        if not remaining:
            return top_loss

        diversity = self._select_diversity(remaining, max(div_portion, 1))
        merged = (top_loss + diversity)[:target_size]
        return merged

    def _select_diversity(
        self,
        samples: Sequence[SampleT],
        target_size: int,
    ) -> list[SampleT]:
        if not samples:
            return []

        features = {
            self._get_sample_id(sample): self._text_features(self._get_text(sample))
            for sample in samples
        }

        selected: list[SampleT] = []
        candidates = list(samples)

        scores = {
            self._get_sample_id(sample): self._feature_norm(features[self._get_sample_id(sample)])
            for sample in samples
        }
        first = max(candidates, key=lambda s: scores.get(self._get_sample_id(s), 0.0))
        selected.append(first)
        candidates = [s for s in candidates if self._get_sample_id(s) != self._get_sample_id(first)]

        while candidates and len(selected) < target_size:
            best_candidate = max(
                candidates,
                key=lambda sample: self._min_distance(sample, selected, features),
            )
            selected.append(best_candidate)
            candidates = [
                s
                for s in candidates
                if self._get_sample_id(s) != self._get_sample_id(best_candidate)
            ]

        return selected

    def _text_features(self, text: str) -> Counter:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        filtered = [token for token in tokens if len(token) > 2]
        counts = Counter(filtered)
        total = sum(counts.values()) or 1.0
        for key in counts:
            counts[key] /= total
        return counts

    def _feature_norm(self, features: Counter) -> float:
        return math.sqrt(sum(value * value for value in features.values()))

    def _cosine_similarity(self, left: Counter, right: Counter) -> float:
        keys = left.keys() & right.keys()
        if not keys:
            return 0.0
        return sum(left[key] * right[key] for key in keys)

    def _min_distance(
        self,
        candidate: SampleT,
        selected: Sequence[SampleT],
        features: dict[str, Counter],
    ) -> float:
        cand_feat = features[self._get_sample_id(candidate)]
        if not selected:
            return 1.0
        sims = [
            self._cosine_similarity(cand_feat, features[self._get_sample_id(item)])
            for item in selected
        ]
        similarity = max(sims) if sims else 0.0
        return 1.0 - similarity

    def _get_sample_id(self, sample: SampleT) -> str:
        if isinstance(sample, dict):
            return sample.get("sample_id", sample.get("dialog_id", str(id(sample))))
        return getattr(sample, "sample_id", getattr(sample, "dialog_id", str(id(sample))))

    def _get_text(self, sample: SampleT) -> str:
        if isinstance(sample, dict):
            return sample.get("text", "")
        return getattr(sample, "text", "")

    def _get_metadata(self, sample: SampleT) -> dict[str, Any]:
        if isinstance(sample, dict):
            return sample.get("metadata", {})
        return getattr(sample, "metadata", {})
