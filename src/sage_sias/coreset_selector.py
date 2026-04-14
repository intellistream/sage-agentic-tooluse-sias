"""Coreset selection strategies, including streaming selection and scoring."""

from __future__ import annotations

import math
import random
import re
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .importance_scorer import ImportanceScoreBreakdown, ImportanceScorer


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
    STRATEGIES = ("loss_topk", "diversity", "hybrid", "random", "streaming")

    def __init__(
        self,
        strategy: str = "loss_topk",
        metric_key: str = "loss",
        diversity_temperature: float = 0.7,
        random_seed: int = 13,
        importance_scorer: ImportanceScorer | None = None,
        streaming_window_size: int = 128,
        replacement_temperature: float = 0.5,
        long_term_pool_size: int | None = None,
    ) -> None:
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}. Choose from {self.STRATEGIES}")

        self.strategy = strategy
        self.metric_key = metric_key
        self.diversity_temperature = diversity_temperature
        self.importance_scorer = importance_scorer or ImportanceScorer(metric_key=metric_key)
        self.streaming_window_size = streaming_window_size
        self.replacement_temperature = replacement_temperature
        self.long_term_pool_size = long_term_pool_size
        self._rng = random.Random(random_seed)
        self._short_term_pool: list[SampleT] = []
        self._long_term_pool: list[SampleT] = []

    @property
    def streaming_pool_sizes(self) -> dict[str, int]:
        return {
            "short_term": len(self._short_term_pool),
            "long_term": len(self._long_term_pool),
        }

    def select(
        self,
        samples: Sequence[SampleT],
        *,
        target_size: int | None,
        metrics: dict[str, float] | None = None,
    ) -> list[SampleT]:
        for sample in samples:
            self._get_sample_id(sample)

        if self.strategy == "streaming":
            return self.update_stream(samples=samples, target_size=target_size, metrics=metrics)

        if target_size is None or target_size <= 0 or target_size >= len(samples):
            selected = list(samples)
        elif self.strategy == "loss_topk":
            selected = self._select_loss(samples, target_size, metrics)
        elif self.strategy == "diversity":
            selected = self._select_diversity(samples, target_size)
        elif self.strategy == "hybrid":
            selected = self._select_hybrid(samples, target_size, metrics)
        else:
            selected = self._select_random(samples, target_size)

        self._attach_importance_explanations(selected, samples=samples, metrics=metrics)
        return selected

    def update_stream(
        self,
        samples: Sequence[SampleT],
        *,
        target_size: int | None,
        metrics: dict[str, float] | None = None,
    ) -> list[SampleT]:
        incoming = self._dedupe_latest(samples)
        if target_size is None or target_size <= 0:
            self._short_term_pool = self._update_short_term_pool(incoming)
            return list(incoming)

        self._short_term_pool = self._update_short_term_pool(incoming)
        candidate_pool = self._dedupe_latest(self._long_term_pool + self._short_term_pool)

        long_capacity = self.long_term_pool_size or max(target_size * 2, target_size)
        ranked_candidates = self._rank_by_importance(
            candidate_pool,
            metrics=metrics,
            reference_samples=self._long_term_pool,
        )
        self._long_term_pool = [sample for sample, _ in ranked_candidates[:long_capacity]]

        selected = self._select_hybrid(
            self._long_term_pool,
            min(target_size, len(self._long_term_pool)),
            metrics,
        )
        self._attach_importance_explanations(
            selected,
            samples=self._long_term_pool,
            metrics=metrics,
            reference_samples=self._short_term_pool,
        )
        return selected

    def score_samples(
        self,
        samples: Sequence[SampleT],
        *,
        metrics: dict[str, float] | None = None,
        reference_samples: Sequence[SampleT] | None = None,
    ) -> list[ImportanceScoreBreakdown]:
        breakdowns = self.importance_scorer.score_samples(
            samples,
            metrics=metrics,
            get_sample_id=self._get_sample_id,
            get_text=self._get_text,
            get_metadata=self._get_metadata,
            reference_samples=reference_samples,
        )
        ordered = sorted(
            breakdowns.values(),
            key=lambda item: (item.score, item.loss_component, item.diversity_component),
            reverse=True,
        )
        return ordered

    def summary(self, original_size: int, selected_size: int) -> SelectionSummary:
        return SelectionSummary(
            total_samples=original_size,
            selected_samples=selected_size,
            strategy=self.strategy,
        )

    def benchmark_streaming(
        self,
        stream_batches: Sequence[Sequence[SampleT]],
        *,
        target_size: int,
        metrics: dict[str, float] | None = None,
    ) -> dict[str, float]:
        start = time.perf_counter()
        selected_count = 0
        for batch in stream_batches:
            selected = self.update_stream(batch, target_size=target_size, metrics=metrics)
            selected_count = len(selected)
        elapsed = time.perf_counter() - start
        total_seen = sum(len(batch) for batch in stream_batches)
        throughput = total_seen / elapsed if elapsed > 0 else float(total_seen)
        return {
            "total_seen": float(total_seen),
            "selected": float(selected_count),
            "elapsed_seconds": elapsed,
            "throughput_samples_per_sec": throughput,
            "short_term_pool": float(len(self._short_term_pool)),
            "long_term_pool": float(len(self._long_term_pool)),
        }

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

    def _select_random(self, samples: Sequence[SampleT], target_size: int) -> list[SampleT]:
        return self._rng.sample(list(samples), target_size)

    def _select_hybrid(
        self,
        samples: Sequence[SampleT],
        target_size: int,
        metrics: dict[str, float] | None,
    ) -> list[SampleT]:
        if not samples:
            return []

        loss_portion = int(target_size * 0.6)
        div_portion = target_size - loss_portion

        top_scored = self._select_importance(samples, loss_portion or 1, metrics)
        top_scored_ids = {self._get_sample_id(s) for s in top_scored}

        remaining = [s for s in samples if self._get_sample_id(s) not in top_scored_ids]
        if not remaining:
            return top_scored[:target_size]

        diversity = self._select_diversity(remaining, max(div_portion, 1))
        merged = self._dedupe_latest(top_scored + diversity)
        return merged[:target_size]

    def _select_importance(
        self,
        samples: Sequence[SampleT],
        target_size: int,
        metrics: dict[str, float] | None,
        *,
        reference_samples: Sequence[SampleT] | None = None,
    ) -> list[SampleT]:
        ranked = self._rank_by_importance(
            samples,
            metrics=metrics,
            reference_samples=reference_samples,
        )
        return [sample for sample, _ in ranked[:target_size]]

    def _rank_by_importance(
        self,
        samples: Sequence[SampleT],
        *,
        metrics: dict[str, float] | None,
        reference_samples: Sequence[SampleT] | None = None,
    ) -> list[tuple[SampleT, ImportanceScoreBreakdown]]:
        breakdowns = self.importance_scorer.score_samples(
            samples,
            metrics=metrics,
            get_sample_id=self._get_sample_id,
            get_text=self._get_text,
            get_metadata=self._get_metadata,
            reference_samples=reference_samples,
        )
        ranked = sorted(
            ((sample, breakdowns[self._get_sample_id(sample)]) for sample in samples),
            key=lambda item: (
                item[1].score,
                item[1].loss_component,
                item[1].diversity_component,
                item[1].novelty_component,
            ),
            reverse=True,
        )
        return ranked

    def _attach_importance_explanations(
        self,
        selected: Sequence[SampleT],
        *,
        samples: Sequence[SampleT],
        metrics: dict[str, float] | None,
        reference_samples: Sequence[SampleT] | None = None,
    ) -> None:
        if not selected:
            return
        breakdowns = self.importance_scorer.score_samples(
            samples,
            metrics=metrics,
            get_sample_id=self._get_sample_id,
            get_text=self._get_text,
            get_metadata=self._get_metadata,
            reference_samples=reference_samples,
        )
        for sample in selected:
            sample_id = self._get_sample_id(sample)
            breakdown = breakdowns.get(sample_id)
            if breakdown is None:
                continue
            metadata = self._get_metadata(sample)
            metadata["importance_score"] = breakdown.score
            metadata["importance_breakdown"] = breakdown.as_dict()

    def _update_short_term_pool(self, incoming: Sequence[SampleT]) -> list[SampleT]:
        pool = list(self._short_term_pool)
        for sample in incoming:
            pool = [item for item in pool if self._get_sample_id(item) != self._get_sample_id(sample)]
            if len(pool) < self.streaming_window_size:
                pool.append(sample)
                continue
            replace_index = self._rng.randrange(len(pool))
            if self._rng.random() < self.replacement_temperature:
                pool[replace_index] = sample
        return self._dedupe_latest(pool)

    def _dedupe_latest(self, samples: Sequence[SampleT]) -> list[SampleT]:
        deduped: dict[str, SampleT] = {}
        for sample in samples:
            deduped[self._get_sample_id(sample)] = sample
        return list(deduped.values())

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

    def _text_features(self, text: str) -> Counter[str]:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        filtered = [token for token in tokens if len(token) > 2]
        counts = Counter(filtered)
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

    def _min_distance(
        self,
        candidate: SampleT,
        selected: Sequence[SampleT],
        features: dict[str, Counter[str]],
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
            sample_id = sample.get("sample_id")
            if isinstance(sample_id, str) and sample_id:
                return sample_id
            raise ValueError("Sample dictionary must contain non-empty 'sample_id'")

        sample_id = getattr(sample, "sample_id", None)
        if isinstance(sample_id, str) and sample_id:
            return sample_id
        raise ValueError("Sample object must provide non-empty 'sample_id'")

    def _get_text(self, sample: SampleT) -> str:
        if isinstance(sample, dict):
            return sample.get("text", "")
        return getattr(sample, "text", "")

    def _get_metadata(self, sample: SampleT) -> dict[str, Any]:
        if isinstance(sample, dict):
            metadata = sample.setdefault("metadata", {})
        else:
            metadata = getattr(sample, "metadata", {})
        return metadata if isinstance(metadata, dict) else {}
