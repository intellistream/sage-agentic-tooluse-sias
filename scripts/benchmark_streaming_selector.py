"""Run a minimal streaming-vs-batch selector benchmark."""

from __future__ import annotations

import argparse
import json

from sage_sias.benchmarking import benchmark_streaming_vs_batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/streaming-selector-benchmark")
    args = parser.parse_args()
    result = benchmark_streaming_vs_batch(args.output_dir)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
