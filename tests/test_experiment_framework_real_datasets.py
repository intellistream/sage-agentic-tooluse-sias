"""Tests for the real-dataset experiment framework."""

from __future__ import annotations

import json
from pathlib import Path

from sage_sias.experiment_framework import (
    RealBenchmarkConfig,
    build_continual_phases,
    load_real_dataset,
    materialize_real_benchmark,
)


def test_bfcl_adapter_and_manifest_generation(tmp_path: Path) -> None:
    dataset_path = tmp_path / "bfcl.jsonl"
    rows = [
        {
            "id": "bfcl_1",
            "question": "weather api request",
            "functions": [{"name": "weather.lookup"}],
            "answer": {"name": "weather.lookup"},
            "test_category": "simple",
        },
        {
            "id": "bfcl_2",
            "question": "currency api request",
            "functions": [{"name": "fx.lookup"}],
            "answer": {"name": "fx.lookup"},
            "test_category": "parallel_function",
        },
    ]
    dataset_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    samples = load_real_dataset("bfcl", dataset_path)
    phases = build_continual_phases(samples, dataset_name="bfcl", phase_field="phase_source")

    assert len(phases) == 2

    manifests = materialize_real_benchmark(
        RealBenchmarkConfig(
            dataset_name="bfcl",
            input_path=str(dataset_path),
            output_dir=str(tmp_path / "bfcl_out"),
            phase_field="phase_source",
            methods=["sequential_ft", "sias"],
        )
    )

    assert manifests
    assert (tmp_path / "bfcl_out" / "manifest_index.csv").exists()


def test_agentbench_fc_adapter_and_manifest_generation(tmp_path: Path) -> None:
    dataset_path = tmp_path / "agentbench_fc.json"
    rows = [
        {
            "id": "ab_1",
            "prompt": "use db tool to query city temperature",
            "tools": [{"name": "db.query"}],
            "reward": 1.0,
            "environment": "dbbench",
            "split": "dev",
        },
        {
            "id": "ab_2",
            "prompt": "use os tool to list directory",
            "tools": [{"name": "os.exec"}],
            "reward": 0.0,
            "environment": "os_interaction",
            "split": "test",
        },
    ]
    dataset_path.write_text(json.dumps(rows), encoding="utf-8")

    manifests = materialize_real_benchmark(
        RealBenchmarkConfig(
            dataset_name="agentbench_fc",
            input_path=str(dataset_path),
            output_dir=str(tmp_path / "agentbench_out"),
            phase_field="phase_source",
            eval_split_field="split",
            methods=["fixed_replay", "joint_oracle"],
        )
    )

    assert manifests
    assert (tmp_path / "agentbench_out" / "README.generated.md").exists()
