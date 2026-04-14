"""Experiment framework for BFCL and AgentBench FC continual evaluation."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .continual_learner import OnlineContinualLearner
from .coreset_selector import CoresetSelector


SupportedDataset = Literal["bfcl", "agentbench_fc"]
SupportedMethod = Literal["sequential_ft", "joint_oracle", "fixed_replay", "sias"]


@dataclass(slots=True)
class ExperimentSample:
    sample_id: str
    text: str
    metadata: dict[str, Any]
    raw_input: dict[str, Any] = field(default_factory=dict)
    ground_truth: dict[str, Any] = field(default_factory=dict)

    def to_selector_sample(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "text": self.text,
            "metadata": dict(self.metadata),
            "raw_input": dict(self.raw_input),
            "ground_truth": dict(self.ground_truth),
        }


@dataclass(slots=True)
class ContinualPhase:
    phase_id: str
    dataset_name: SupportedDataset
    phase_order: int
    train_samples: list[ExperimentSample]
    eval_samples: list[ExperimentSample]


@dataclass(slots=True)
class ManifestRecord:
    method: SupportedMethod
    dataset_name: SupportedDataset
    phase_id: str
    phase_order: int
    train_count: int
    replay_count: int
    eval_count: int
    train_manifest: str
    eval_manifest: str


@dataclass(slots=True)
class RealBenchmarkConfig:
    dataset_name: SupportedDataset
    input_path: str
    output_dir: str
    phase_field: str
    eval_split_field: str | None = None
    methods: list[SupportedMethod] = field(
        default_factory=lambda: ["sequential_ft", "fixed_replay", "sias", "joint_oracle"]
    )
    buffer_size: int = 256
    replay_ratio: float = 0.25
    random_seed: int = 17


def load_real_dataset(
    dataset_name: SupportedDataset,
    input_path: str | Path,
) -> list[ExperimentSample]:
    path = Path(input_path)
    if path.suffix == ".jsonl":
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    elif path.suffix == ".json":
        records = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Unsupported dataset file format: {path.suffix}")

    if dataset_name == "bfcl":
        return [_normalize_bfcl_record(record) for record in records]
    if dataset_name == "agentbench_fc":
        return [_normalize_agentbench_fc_record(record) for record in records]
    raise ValueError(f"Unsupported dataset name: {dataset_name}")


def build_continual_phases(
    samples: list[ExperimentSample],
    *,
    dataset_name: SupportedDataset,
    phase_field: str,
    eval_split_field: str | None = None,
) -> list[ContinualPhase]:
    grouped: dict[str, list[ExperimentSample]] = {}
    for sample in samples:
        phase_id = str(sample.metadata.get(phase_field, "phase_0"))
        grouped.setdefault(phase_id, []).append(sample)

    phases: list[ContinualPhase] = []
    for order, phase_id in enumerate(sorted(grouped)):
        phase_samples = grouped[phase_id]
        if eval_split_field is None:
            split_index = max(1, int(len(phase_samples) * 0.8))
            train_samples = phase_samples[:split_index]
            eval_samples = phase_samples[split_index:] or phase_samples[:1]
        else:
            train_samples = [
                sample for sample in phase_samples if sample.metadata.get(eval_split_field) != "test"
            ]
            eval_samples = [
                sample for sample in phase_samples if sample.metadata.get(eval_split_field) == "test"
            ]
            if not train_samples:
                train_samples = phase_samples
            if not eval_samples:
                eval_samples = phase_samples[: max(1, len(phase_samples) // 5)]

        phases.append(
            ContinualPhase(
                phase_id=phase_id,
                dataset_name=dataset_name,
                phase_order=order,
                train_samples=train_samples,
                eval_samples=eval_samples,
            )
        )
    return phases


def materialize_real_benchmark(
    config: RealBenchmarkConfig,
) -> list[ManifestRecord]:
    samples = load_real_dataset(config.dataset_name, config.input_path)
    phases = build_continual_phases(
        samples,
        dataset_name=config.dataset_name,
        phase_field=config.phase_field,
        eval_split_field=config.eval_split_field,
    )
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifests: list[ManifestRecord] = []
    for method in config.methods:
        manifests.extend(
            _materialize_method(
                method=method,
                phases=phases,
                output_dir=output_dir,
                buffer_size=config.buffer_size,
                replay_ratio=config.replay_ratio,
                random_seed=config.random_seed,
            )
        )

    _write_manifest_index(output_dir / "manifest_index.csv", manifests)
    write_dataset_readme(config, phases, output_dir / "README.generated.md")
    return manifests


def write_dataset_readme(
    config: RealBenchmarkConfig,
    phases: list[ContinualPhase],
    file_path: str | Path,
) -> None:
    lines = [
        "# Generated Real Benchmark Layout",
        "",
        f"- dataset_name: `{config.dataset_name}`",
        f"- input_path: `{config.input_path}`",
        f"- phase_field: `{config.phase_field}`",
        f"- eval_split_field: `{config.eval_split_field}`",
        f"- methods: `{', '.join(config.methods)}`",
        "",
        "## Phases",
        "",
        "| order | phase_id | train_count | eval_count |",
        "| --- | --- | --- | --- |",
    ]
    for phase in phases:
        lines.append(
            f"| {phase.phase_order} | {phase.phase_id} | {len(phase.train_samples)} | {len(phase.eval_samples)} |"
        )
    Path(file_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _materialize_method(
    *,
    method: SupportedMethod,
    phases: list[ContinualPhase],
    output_dir: Path,
    buffer_size: int,
    replay_ratio: float,
    random_seed: int,
) -> list[ManifestRecord]:
    method_dir = output_dir / method
    method_dir.mkdir(parents=True, exist_ok=True)

    manifests: list[ManifestRecord] = []
    learner: OnlineContinualLearner | None = None
    replay_buffer: list[dict[str, Any]] = []

    if method == "sias":
        learner = OnlineContinualLearner(
            buffer_size=buffer_size,
            replay_ratio=replay_ratio,
            selector=CoresetSelector(strategy="streaming", random_seed=random_seed),
            random_seed=random_seed,
        )

    for phase in phases:
        train_selector_samples = [sample.to_selector_sample() for sample in phase.train_samples]
        eval_selector_samples = [sample.to_selector_sample() for sample in phase.eval_samples]

        if method == "sequential_ft":
            train_payload = train_selector_samples
            replay_count = 0
        elif method == "joint_oracle":
            train_payload = [
                sample.to_selector_sample()
                for prior_phase in phases[: phase.phase_order + 1]
                for sample in prior_phase.train_samples
            ]
            replay_count = len(train_payload) - len(train_selector_samples)
        elif method == "fixed_replay":
            replay_slice = replay_buffer[-min(len(replay_buffer), max(1, int(len(train_selector_samples) * replay_ratio))):]
            train_payload = train_selector_samples + replay_slice
            replay_buffer.extend(train_selector_samples)
            replay_count = len(replay_slice)
        elif method == "sias":
            assert learner is not None
            train_payload = learner.update_buffer(train_selector_samples)
            replay_count = max(0, len(train_payload) - len(train_selector_samples))
        else:
            raise ValueError(f"Unsupported method: {method}")

        train_file = method_dir / f"{phase.phase_order:02d}_{phase.phase_id}_train.jsonl"
        eval_file = method_dir / f"{phase.phase_order:02d}_{phase.phase_id}_eval.jsonl"
        _write_jsonl(train_file, train_payload)
        _write_jsonl(eval_file, eval_selector_samples)

        manifests.append(
            ManifestRecord(
                method=method,
                dataset_name=phase.dataset_name,
                phase_id=phase.phase_id,
                phase_order=phase.phase_order,
                train_count=len(train_payload),
                replay_count=replay_count,
                eval_count=len(eval_selector_samples),
                train_manifest=str(train_file),
                eval_manifest=str(eval_file),
            )
        )

    return manifests


def _write_manifest_index(file_path: Path, manifests: list[ManifestRecord]) -> None:
    with file_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(manifests[0]).keys()))
        writer.writeheader()
        for record in manifests:
            writer.writerow(asdict(record))


def _write_jsonl(file_path: Path, rows: list[dict[str, Any]]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def _normalize_bfcl_record(record: dict[str, Any]) -> ExperimentSample:
    sample_id = _pick_first(record, "id", "sample_id", "question_id", default=None)
    if not isinstance(sample_id, str) or not sample_id:
        sample_id = f"bfcl_{abs(hash(json.dumps(record, sort_keys=True, ensure_ascii=True)))}"
    question = _pick_first(record, "question", "user_query", "prompt", default="")
    tools = _pick_first(record, "functions", "tools", "tool_definitions", default=[])
    answer = _pick_first(record, "answer", "ground_truth", "expected_output", default={})
    metadata = {
        "dataset_name": "bfcl",
        "phase_group": _pick_first(record, "test_category", "category", "domain", default="bfcl_default"),
        "language": _pick_first(record, "language", default="python"),
        "tool_count": len(tools) if isinstance(tools, list) else 0,
        "phase_source": _pick_first(record, "test_category", "category", "domain", default="bfcl_default"),
    }
    return ExperimentSample(
        sample_id=sample_id,
        text=str(question),
        metadata=metadata,
        raw_input={"question": question, "tools": tools},
        ground_truth={"answer": answer},
    )


def _normalize_agentbench_fc_record(record: dict[str, Any]) -> ExperimentSample:
    sample_id = _pick_first(record, "id", "sample_id", "task_id", default=None)
    if not isinstance(sample_id, str) or not sample_id:
        sample_id = f"agentbench_fc_{abs(hash(json.dumps(record, sort_keys=True, ensure_ascii=True)))}"
    prompt = _pick_first(record, "prompt", "instruction", "user_query", "question", default="")
    tools = _pick_first(record, "tools", "functions", default=[])
    reward = _pick_first(record, "reward", "success", "score", default=0.0)
    environment = _pick_first(record, "env_name", "environment", "task_name", default="agentbench_fc")
    split = _pick_first(record, "split", default="dev")
    metadata = {
        "dataset_name": "agentbench_fc",
        "phase_group": environment,
        "environment": environment,
        "split": split,
        "loss": 1.0 - float(reward) if isinstance(reward, (int, float)) else 0.0,
        "phase_source": environment,
    }
    return ExperimentSample(
        sample_id=sample_id,
        text=str(prompt),
        metadata=metadata,
        raw_input={"prompt": prompt, "tools": tools},
        ground_truth={"reward": reward},
    )


def _pick_first(record: dict[str, Any], *keys: str, default: Any) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return default
