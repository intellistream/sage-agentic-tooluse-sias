"""Minimal benchmark and ablation helpers for SIAS."""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .continual_learner import OnlineContinualLearner
from .contract import SIASConfig, run_selection_contract
from .coreset_selector import CoresetSelector


@dataclass(slots=True)
class AblationResult:
    scenario: str
    replay_mode: str
    coreset_mode: str
    success_proxy: float
    sample_efficiency: float
    forgetting_rate: float
    runtime_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "replay_mode": self.replay_mode,
            "coreset_mode": self.coreset_mode,
            "success_proxy": self.success_proxy,
            "sample_efficiency": self.sample_efficiency,
            "forgetting_rate": self.forgetting_rate,
            "runtime_seconds": self.runtime_seconds,
        }


def benchmark_streaming_vs_batch(output_dir: str | Path) -> dict[str, float]:
    output_path = Path(output_dir)
    batches = [_build_dataset(64, prefix=f"b{round_id}_") for round_id in range(8)]

    batch_selector = CoresetSelector(strategy="hybrid", random_seed=7)
    cumulative: list[dict[str, Any]] = []
    batch_start = time.perf_counter()
    for batch in batches:
        cumulative.extend(batch)
        batch_selector.select(cumulative, target_size=64)
    batch_elapsed = time.perf_counter() - batch_start

    streaming_selector = CoresetSelector(strategy="streaming", random_seed=7)
    streaming_result = streaming_selector.benchmark_streaming(batches, target_size=64)

    result = {
        "batch_recompute_seconds": batch_elapsed,
        "streaming_seconds": streaming_result["elapsed_seconds"],
        "speedup": batch_elapsed / max(streaming_result["elapsed_seconds"], 1e-9),
    }
    output_path.mkdir(parents=True, exist_ok=True)
    csv_path = output_path / "streaming_selector_benchmark.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result.keys()))
        writer.writeheader()
        writer.writerow(result)
    return result


def run_minimal_ablation(output_dir: str | Path) -> list[AblationResult]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    stream = [_build_dataset(48, prefix=f"r{round_id}_") for round_id in range(6)]

    scenarios = [
        ("no_replay_no_coreset", "none", "none"),
        ("fixed_replay_batch_coreset", "fixed", "batch"),
        ("dynamic_replay_batch_coreset", "dynamic", "batch"),
        ("fixed_replay_streaming_coreset", "fixed", "streaming"),
        ("dynamic_replay_streaming_coreset", "dynamic", "streaming"),
    ]
    results: list[AblationResult] = []

    for scenario_name, replay_mode, coreset_mode in scenarios:
        start = time.perf_counter()
        learner = _build_learner_for_scenario(replay_mode, coreset_mode)
        forgetting_scores: list[float] = []
        total_seen = 0

        for batch in stream:
            total_seen += len(batch)
            learner.update_buffer(batch)
            forgetting_scores.append(learner.forgetting_score)

        final_buffer = learner.buffer_snapshot()
        losses = [
            float(sample.get("metadata", {}).get("loss", 0.0))
            for sample in final_buffer
            if isinstance(sample, dict)
        ]
        success_proxy = (sum(losses) / len(losses)) if losses else 0.0
        retention_ratio = len(final_buffer) / float(max(total_seen, 1))
        sample_efficiency = success_proxy / max(retention_ratio, 1e-9)
        forgetting_rate = sum(forgetting_scores) / max(len(forgetting_scores), 1)
        runtime_seconds = time.perf_counter() - start
        results.append(
            AblationResult(
                scenario=scenario_name,
                replay_mode=replay_mode,
                coreset_mode=coreset_mode,
                success_proxy=success_proxy,
                sample_efficiency=sample_efficiency,
                forgetting_rate=forgetting_rate,
                runtime_seconds=runtime_seconds,
            )
        )

    _write_ablation_csv(output_path / "ablation_results.csv", results)
    _write_ablation_markdown(output_path / "ablation_report.md", results)
    return results


def build_benchmark_contract_example() -> dict[str, Any]:
    config = SIASConfig(selector_strategy="streaming", enable_adaptive_replay=True)
    samples = _build_dataset(12, prefix="bench_")
    return run_selection_contract(config=config, samples=samples, target_size=4)


def _build_learner_for_scenario(replay_mode: str, coreset_mode: str) -> OnlineContinualLearner:
    if coreset_mode == "none":
        selector = CoresetSelector(strategy="random", random_seed=23)
        buffer_size = 1024
    elif coreset_mode == "streaming":
        selector = CoresetSelector(strategy="streaming", random_seed=23)
        buffer_size = 96
    else:
        selector = CoresetSelector(strategy="hybrid", random_seed=23)
        buffer_size = 96

    if replay_mode == "none":
        replay_ratio = 0.0
        adaptive = False
    elif replay_mode == "dynamic":
        replay_ratio = 0.25
        adaptive = True
    else:
        replay_ratio = 0.25
        adaptive = False

    return OnlineContinualLearner(
        buffer_size=buffer_size,
        replay_ratio=replay_ratio,
        selector=selector,
        random_seed=23,
        enable_adaptive_replay=adaptive,
        enable_strategy_switch=adaptive,
    )


def _write_ablation_csv(file_path: Path, results: list[AblationResult]) -> None:
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].to_dict().keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(result.to_dict())


def _write_ablation_markdown(file_path: Path, results: list[AblationResult]) -> None:
    lines = [
        "# Minimal Tool-Use Ablation Report",
        "",
        "| scenario | replay_mode | coreset_mode | success_proxy | sample_efficiency | forgetting_rate | runtime_seconds |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            f"| {result.scenario} | {result.replay_mode} | {result.coreset_mode} | "
            f"{result.success_proxy:.4f} | {result.sample_efficiency:.4f} | "
            f"{result.forgetting_rate:.4f} | {result.runtime_seconds:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Success proxy uses mean retained loss on the final buffer as a synthetic importance signal.",
            "- Sample efficiency divides success proxy by the retained-sample ratio.",
            "- Forgetting rate aggregates learner-side forgetting scores across rounds.",
        ]
    )
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_dataset(size: int, *, prefix: str) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index in range(size):
        topic = "weather" if index % 3 == 0 else ("finance" if index % 3 == 1 else "travel")
        samples.append(
            {
                "sample_id": f"{prefix}{index}",
                "text": f"{topic} benchmark sample {index}",
                "metadata": {"loss": float(index % 10) / 10.0, "topic": topic},
            }
        )
    return samples
