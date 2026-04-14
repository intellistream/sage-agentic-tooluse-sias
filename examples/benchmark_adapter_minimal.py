"""Minimal benchmark-facing adapter example for SIAS contract v1."""

from __future__ import annotations

import json

from sage_sias.benchmarking import build_benchmark_contract_example


def main() -> None:
    result = build_benchmark_contract_example()
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
