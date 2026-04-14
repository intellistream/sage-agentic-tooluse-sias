"""Minimal cross-repo integration example for sage-agentic-tooluse."""

from __future__ import annotations

import json

from sage_sias.contract import SIASConfig
from sage_sias.integration import select_samples_for_agentic_tooluse


class MockAgentTrainer:
    def train(self, trajectories: list[dict[str, object]]) -> dict[str, object]:
        return {
            "trained_count": len(trajectories),
            "trained_ids": [item["sample_id"] for item in trajectories],
        }


def main() -> None:
    samples = [
        {"sample_id": "t1", "text": "weather tool trace", "metadata": {"loss": 0.3}},
        {"sample_id": "t2", "text": "finance tool trace", "metadata": {"loss": 0.9}},
        {"sample_id": "t3", "text": "travel tool trace", "metadata": {"loss": 0.6}},
    ]
    payload = select_samples_for_agentic_tooluse(
        samples,
        target_size=2,
        config=SIASConfig(selector_strategy="hybrid"),
    )
    trainer = MockAgentTrainer()
    training_result = trainer.train(payload["selected"])
    print(json.dumps({"selection": payload, "training": training_result}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
