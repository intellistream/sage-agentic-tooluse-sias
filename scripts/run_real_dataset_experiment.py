"""Materialize BFCL or AgentBench FC continual experiment manifests."""

from __future__ import annotations

import argparse
import json

from sage_sias.experiment_framework import RealBenchmarkConfig, materialize_real_benchmark


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["bfcl", "agentbench_fc"], required=True)
    parser.add_argument("--input-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--phase-field", required=True)
    parser.add_argument("--eval-split-field", default=None)
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["sequential_ft", "fixed_replay", "sias", "joint_oracle"],
    )
    parser.add_argument("--buffer-size", type=int, default=256)
    parser.add_argument("--replay-ratio", type=float, default=0.25)
    parser.add_argument("--random-seed", type=int, default=17)
    args = parser.parse_args()

    config = RealBenchmarkConfig(
        dataset_name=args.dataset,
        input_path=args.input_path,
        output_dir=args.output_dir,
        phase_field=args.phase_field,
        eval_split_field=args.eval_split_field,
        methods=args.methods,
        buffer_size=args.buffer_size,
        replay_ratio=args.replay_ratio,
        random_seed=args.random_seed,
    )
    manifests = materialize_real_benchmark(config)
    print(json.dumps([manifest.__dict__ for manifest in manifests], indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
