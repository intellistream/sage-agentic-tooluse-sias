"""
Online Continual Learning with Experience Replay

Implements an experience replay buffer for online/incremental training that
prevents catastrophic forgetting. The buffer is managed using coreset selection
to retain the most valuable samples.

This is a core component of SIAS (Streaming Importance-Aware Agent System).
"""

from __future__ import annotations

import csv
import random
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .adaptive_signals import (
    AdaptiveSignalSummary,
    BatchProfile,
    TraceRecord,
    append_metrics_jsonl,
    build_batch_profile,
    compare_profiles,
    update_running_loss_mean,
    write_config_snapshot,
)
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
        min_replay_ratio: float | None = None,
        max_replay_ratio: float = 0.75,
        enable_adaptive_replay: bool = True,
        enable_strategy_switch: bool = True,
        metric_key: str = "loss",
        trace_dir: str | Path | None = None,
        trace_selected_id_limit: int = 10,
    ) -> None:
        self.buffer_size = buffer_size
        self.base_replay_ratio = replay_ratio
        self.replay_ratio = replay_ratio
        self.min_replay_ratio = replay_ratio if min_replay_ratio is None else min_replay_ratio
        self.max_replay_ratio = max_replay_ratio
        self.enable_adaptive_replay = enable_adaptive_replay
        self.enable_strategy_switch = enable_strategy_switch
        self.metric_key = metric_key
        self.selector = selector or CoresetSelector(strategy="hybrid")
        self._default_selector_strategy = self.selector.strategy
        self._buffer: list[SampleT] = []
        self._metrics: dict[str, float] = {}
        self._rng = random.Random(random_seed)
        self._random_seed = random_seed
        self._last_batch_profile: BatchProfile | None = None
        self._running_loss_mean: float | None = None
        self._last_signal_summary = AdaptiveSignalSummary(
            drift_score=0.0,
            forgetting_score=0.0,
            topic_shift=0.0,
            token_shift=0.0,
            loss_shift=0.0,
        )
        self._adaptive_replay_ratio = replay_ratio
        self._trace_history: list[TraceRecord] = []
        self._round_id = 0
        self._trace_selected_id_limit = trace_selected_id_limit
        self._trace_dir = Path(trace_dir) if trace_dir is not None else None
        self._metrics_file = self._trace_dir / "metrics.jsonl" if self._trace_dir else None
        self._summary_file = self._trace_dir / "summary.csv" if self._trace_dir else None
        self._config_file = self._trace_dir / "config.snapshot.yaml" if self._trace_dir else None
        if self._config_file is not None:
            write_config_snapshot(
                self._config_file,
                {
                    "buffer_size": self.buffer_size,
                    "base_replay_ratio": self.base_replay_ratio,
                    "min_replay_ratio": self.min_replay_ratio,
                    "max_replay_ratio": self.max_replay_ratio,
                    "enable_adaptive_replay": self.enable_adaptive_replay,
                    "enable_strategy_switch": self.enable_strategy_switch,
                    "metric_key": self.metric_key,
                    "random_seed": self._random_seed,
                    "default_selector_strategy": self._default_selector_strategy,
                },
            )

    @property
    def buffer(self) -> list[SampleT]:
        return list(self._buffer)

    @property
    def buffer_len(self) -> int:
        return len(self._buffer)

    @property
    def drift_score(self) -> float:
        return self._last_signal_summary.drift_score

    @property
    def forgetting_score(self) -> float:
        return self._last_signal_summary.forgetting_score

    @property
    def adaptive_replay_ratio(self) -> float:
        return self._adaptive_replay_ratio

    @property
    def trace_history(self) -> list[dict[str, Any]]:
        return [asdict(record) for record in self._trace_history]

    def update_buffer(
        self,
        new_samples: Sequence[SampleT],
        metrics: dict[str, float] | None = None,
    ) -> list[SampleT]:
        if not new_samples:
            return list(self._buffer)

        # Fail-fast: SIAS core requires canonical sample_id for all samples.
        # No compatibility fallback is allowed in core algorithms.
        for sample in new_samples:
            self._get_sample_id(sample)

        if metrics:
            self._metrics.update(metrics)

        signal_summary = self._analyze_batch(list(new_samples), metrics=metrics)
        self._last_signal_summary = signal_summary
        self._apply_adaptive_policy(signal_summary)

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
        training_batch = self._assemble_training_batch(new_samples)
        self._record_trace(list(new_samples), training_batch)
        self._round_id += 1
        return training_batch

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
        replay_ratio = self._adaptive_replay_ratio if self.enable_adaptive_replay else self.replay_ratio
        if not self._buffer or replay_ratio <= 0:
            return []

        exclude = set(exclude or [])
        available = [
            sample for sample in self._buffer if self._get_sample_id(sample) not in exclude
        ]
        if not available:
            return []

        replay_size = max(1, int(new_batch_size * replay_ratio))
        replay_size = min(replay_size, len(available))
        if self.selector.strategy != "random":
            ranked = self.selector.score_samples(
                available,
                metrics=self._metrics,
            )
            ranked_ids = [item.sample_id for item in ranked[:replay_size]]
            ranked_set = set(ranked_ids)
            prioritized = [sample for sample in available if self._get_sample_id(sample) in ranked_set]
            prioritized.sort(key=lambda sample: ranked_ids.index(self._get_sample_id(sample)))
            return prioritized[:replay_size]
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
        self._last_batch_profile = None
        self._running_loss_mean = None
        self._last_signal_summary = AdaptiveSignalSummary(
            drift_score=0.0,
            forgetting_score=0.0,
            topic_shift=0.0,
            token_shift=0.0,
            loss_shift=0.0,
        )
        self._adaptive_replay_ratio = self.base_replay_ratio
        self._trace_history = []
        self._round_id = 0

    def update_metrics(self, metrics: dict[str, float]) -> None:
        self._metrics.update(metrics)

    def _analyze_batch(
        self,
        new_samples: list[SampleT],
        *,
        metrics: dict[str, float] | None,
    ) -> AdaptiveSignalSummary:
        profile = build_batch_profile(
            new_samples,
            metric_key=self.metric_key,
            metrics=metrics,
            get_sample_id=self._get_sample_id,
            get_text=self._get_text,
            get_metadata=self._get_metadata,
        )
        signal_summary = compare_profiles(
            self._last_batch_profile,
            profile,
            running_loss_mean=self._running_loss_mean,
        )
        self._last_batch_profile = profile
        self._running_loss_mean = update_running_loss_mean(
            self._running_loss_mean,
            profile.mean_loss,
        )
        return signal_summary

    def _apply_adaptive_policy(self, signal_summary: AdaptiveSignalSummary) -> None:
        if self.enable_adaptive_replay:
            intensity = max(signal_summary.drift_score, signal_summary.forgetting_score)
            if intensity < 0.15:
                self._adaptive_replay_ratio = self.base_replay_ratio
            else:
                candidate = self.base_replay_ratio + (0.5 * intensity)
                self._adaptive_replay_ratio = min(
                    self.max_replay_ratio,
                    max(self.min_replay_ratio, candidate),
                )
        else:
            self._adaptive_replay_ratio = self.base_replay_ratio

        if self.enable_strategy_switch:
            # Priority rule: when forgetting/loss spike is detected, bias toward loss-driven
            # replay/selection regardless of topic drift (fail-fast over exploration).
            if signal_summary.forgetting_score >= 0.2 or signal_summary.loss_shift >= 0.4:
                self.selector.strategy = "loss_topk"
            elif signal_summary.drift_score >= 0.45 and signal_summary.topic_shift >= signal_summary.loss_shift:
                self.selector.strategy = "diversity"
            else:
                self.selector.strategy = "hybrid"
        else:
            self.selector.strategy = self._default_selector_strategy

    def _record_trace(
        self,
        new_samples: list[SampleT],
        training_batch: list[SampleT],
    ) -> None:
        replay_ids = [self._get_sample_id(sample) for sample in training_batch[len(new_samples) :]]
        selected_ids = [self._get_sample_id(sample) for sample in self._buffer[: self._trace_selected_id_limit]]
        record = TraceRecord(
            round_id=self._round_id,
            drift_score=self.drift_score,
            forgetting_score=self.forgetting_score,
            adaptive_replay_ratio=self.adaptive_replay_ratio,
            selector_strategy=self.selector.strategy,
            buffer_size=self.buffer_len,
            new_batch_size=len(new_samples),
            replay_size=len(replay_ids),
            selected_ids=selected_ids,
            replay_ids=replay_ids,
        )
        self._trace_history.append(record)
        if self._metrics_file is not None:
            append_metrics_jsonl(self._metrics_file, record)
        if self._summary_file is not None:
            self._append_summary_csv(record)

    def _append_summary_csv(self, record: TraceRecord) -> None:
        assert self._summary_file is not None
        self._summary_file.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self._summary_file.exists()
        with self._summary_file.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "round_id",
                    "drift_score",
                    "forgetting_score",
                    "adaptive_replay_ratio",
                    "selector_strategy",
                    "buffer_size",
                    "new_batch_size",
                    "replay_size",
                ],
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(
                {
                    "round_id": record.round_id,
                    "drift_score": record.drift_score,
                    "forgetting_score": record.forgetting_score,
                    "adaptive_replay_ratio": record.adaptive_replay_ratio,
                    "selector_strategy": record.selector_strategy,
                    "buffer_size": record.buffer_size,
                    "new_batch_size": record.new_batch_size,
                    "replay_size": record.replay_size,
                }
            )

    def _get_sample_id(self, sample: SampleT) -> str:
        # Canonical contract: sample_id is required.
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
            metadata = sample.get("metadata", {})
        else:
            metadata = getattr(sample, "metadata", {})
        return metadata if isinstance(metadata, dict) else {}
