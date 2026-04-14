"""Tests for issue #9 cross-repo integration contract."""

from __future__ import annotations

from sage_sias.contract import SIASConfig
from sage_sias.integration import select_samples_for_agentic_tooluse


class MockAgentTrainer:
    def train(self, trajectories: list[dict[str, object]]) -> dict[str, object]:
        return {
            "trained_ids": [item["sample_id"] for item in trajectories],
            "trained_count": len(trajectories),
        }


def test_agentic_tooluse_integration_contract_is_runnable() -> None:
    samples = [
        {"sample_id": "t1", "text": "weather tool trace", "metadata": {"loss": 0.3}},
        {"sample_id": "t2", "text": "finance tool trace", "metadata": {"loss": 0.9}},
        {"sample_id": "t3", "text": "travel tool trace", "metadata": {"loss": 0.6}},
    ]
    payload = select_samples_for_agentic_tooluse(
        samples,
        target_size=2,
        config=SIASConfig(selector_strategy="hybrid", random_seed=5),
    )
    trainer = MockAgentTrainer()
    train_result = trainer.train(payload["selected"])

    assert payload["version"] == "sias-benchmark-v1"
    assert train_result["trained_count"] == 2
    assert train_result["trained_ids"] == [item["sample_id"] for item in payload["selected"]]
