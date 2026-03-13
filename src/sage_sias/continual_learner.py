"""
Online Continual Learning with Experience Replay

Implements an experience replay buffer for online/incremental training that
prevents catastrophic forgetting. The buffer is managed using coreset selection
to retain the most valuable samples.

This is a core component of SIAS (Streaming Importance-Aware Agent System).
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence

from .coreset_selector import CoresetSelector, SampleT, SelectionSummary


class OnlineContinualLearner:
    """
    Maintain a replay buffer for online continual learning.

    Implements experience replay to prevent catastrophic forgetting during
    incremental/online training. The buffer is managed using coreset selection
    to keep the most valuable samples.
    """

    def __init__(
        self,
        buffer_size: int = 2048,
        replay_ratio: float = 0.3,
        selector: CoresetSelector | None = None,
        random_seed: int = 17,
    ) -> None:
        self.buffer_size = buffer_size
        self.replay_ratio = replay_ratio
        self.selector = selector or CoresetSelector(strategy="hybrid")
        self._buffer: list[SampleT] = []
        self._metrics: dict[str, float] = {}
        self._rng = random.Random(random_seed)

    @property
    def buffer(self) -> list[SampleT]:
        return list(self._buffer)

    @property
    def buffer_len(self) -> int:
        return len(self._buffer)

    def update_buffer(
        self,
        new_samples: Sequence[SampleT],
        metrics: dict[str, float] | None = None,
    ) -> list[SampleT]:
        if not new_samples:
            return list(self._buffer)

        if metrics:
            self._metrics.update(metrics)

        combined = list(self._buffer) + list(new_samples)

        if len(combined) > self.buffer_size:
            combined = self.selector.select(
                combined,
                target_size=self.buffer_size,
                metrics=self._metrics,
            )
            combined_ids = {self._get_sample_id(sample) for sample in combined}
            self._metrics = {k: v for k, v in self._metrics.items() if k in combined_ids}

        self._buffer = combined
        return self._assemble_training_batch(new_samples)

    def _assemble_training_batch(
        self,
        new_samples: Sequence[SampleT],
    ) -> list[SampleT]:
        new_ids = {self._get_sample_id(s) for s in new_samples}
        replay = self.sample_replay(len(new_samples), exclude=new_ids)
        return list(new_samples) + replay

    def sample_replay(
        self,
        new_batch_size: int,
        *,
        exclude: Iterable[str] | None = None,
    ) -> list[SampleT]:
        if not self._buffer or self.replay_ratio <= 0:
            return []

        exclude = set(exclude or [])
        available = [
            sample for sample in self._buffer if self._get_sample_id(sample) not in exclude
        ]
        if not available:
            return []

        replay_size = max(1, int(new_batch_size * self.replay_ratio))
        replay_size = min(replay_size, len(available))
        return self._rng.sample(available, replay_size)

    def buffer_snapshot(self) -> list[SampleT]:
        return list(self._buffer)

    def buffer_summary(self) -> SelectionSummary:
        return SelectionSummary(
            total_samples=len(self._buffer),
            selected_samples=len(self._buffer),
            strategy=f"buffer:{self.selector.strategy}",
        )

    def clear(self) -> None:
        self._buffer = []
        self._metrics = {}

    def update_metrics(self, metrics: dict[str, float]) -> None:
        self._metrics.update(metrics)

    def _get_sample_id(self, sample: SampleT) -> str:
        if isinstance(sample, dict):
            return sample.get("sample_id", sample.get("dialog_id", str(id(sample))))
        return getattr(sample, "sample_id", getattr(sample, "dialog_id", str(id(sample))))
