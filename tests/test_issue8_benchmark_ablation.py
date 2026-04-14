"""Tests for issue #8 benchmark and ablation generation."""

from __future__ import annotations

from pathlib import Path

from sage_sias.benchmarking import benchmark_streaming_vs_batch, run_minimal_ablation


def test_streaming_benchmark_generates_csv(tmp_path: Path) -> None:
    result = benchmark_streaming_vs_batch(tmp_path / "streaming")

    assert "streaming_seconds" in result
    assert "batch_recompute_seconds" in result
    assert (tmp_path / "streaming" / "streaming_selector_benchmark.csv").exists()


def test_ablation_runner_generates_markdown_and_csv(tmp_path: Path) -> None:
    results = run_minimal_ablation(tmp_path / "ablation")

    assert len(results) >= 5
    assert (tmp_path / "ablation" / "ablation_results.csv").exists()
    assert (tmp_path / "ablation" / "ablation_report.md").exists()
