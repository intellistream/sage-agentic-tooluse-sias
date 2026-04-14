"""Run the minimal tool-use ablation matrix and generate reports."""

from __future__ import annotations

import argparse
import json

from sage_sias.benchmarking import run_minimal_ablation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/tooluse-ablation")
    args = parser.parse_args()
    results = run_minimal_ablation(args.output_dir)
    print(json.dumps([item.to_dict() for item in results], indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
