"""Tests for issue #10 benchmark-facing contract v1."""

from __future__ import annotations

from sage_sias.contract import SIASConfig, SIAS_CONTRACT_VERSION, run_selection_contract


def test_sias_config_roundtrip_and_version() -> None:
    config = SIASConfig(selector_strategy="streaming", replay_ratio=0.4)
    payload = config.to_dict()
    restored = SIASConfig.from_dict(payload)

    assert restored.version == SIAS_CONTRACT_VERSION
    assert restored.selector_strategy == "streaming"
    assert restored.replay_ratio == 0.4


def test_sias_config_rejects_unknown_version() -> None:
    try:
        SIASConfig.from_dict({"version": "sias-benchmark-v2"})
    except ValueError as exc:
        assert "Unsupported SIAS contract version" in str(exc)
    else:
        raise AssertionError("Expected unsupported contract version to raise ValueError")


def test_run_selection_contract_returns_v1_schema_with_explanations() -> None:
    config = SIASConfig(selector_strategy="hybrid", random_seed=7)
    samples = [
        {"sample_id": "a", "text": "weather trace", "metadata": {"loss": 0.2}},
        {"sample_id": "b", "text": "finance trace", "metadata": {"loss": 0.9}},
        {"sample_id": "c", "text": "travel trace", "metadata": {"loss": 0.6}},
    ]

    result = run_selection_contract(config=config, samples=samples, target_size=2)

    assert result["version"] == SIAS_CONTRACT_VERSION
    assert result["config"]["selector_strategy"] == "hybrid"
    assert len(result["selected"]) == 2
    for item in result["selected"]:
        assert {"sample_id", "text", "metadata", "importance_score", "importance_breakdown"} <= set(
            item.keys()
        )
