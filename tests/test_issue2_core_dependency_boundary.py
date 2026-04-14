"""Regression tests for issue #2 core/external dependency boundary cleanup."""

from __future__ import annotations

from pathlib import Path

import pytest
from sage_sias.continual_learner import OnlineContinualLearner
from sage_sias.coreset_selector import CoresetSelector


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src_pkg() -> Path:
    return _repo_root() / "src" / "sage_sias"


def test_no_compatibility_alias_in_core_types_module() -> None:
    content = (_src_pkg() / "types.py").read_text(encoding="utf-8")

    assert "Sample = SIASSample" not in content
    assert "Backward compatibility alias" not in content


def test_legacy_root_modules_removed() -> None:
    assert not (_repo_root() / "core_types.py").exists()
    assert not (_repo_root() / "continual_learner.py").exists()
    assert not (_repo_root() / "coreset_selector.py").exists()
    assert not (_repo_root() / "__init__.py").exists()
    assert not (_repo_root() / "types.py").exists()


def test_no_dialog_id_fallback_in_core_modules() -> None:
    coreset = (_src_pkg() / "coreset_selector.py").read_text(encoding="utf-8")
    learner = (_src_pkg() / "continual_learner.py").read_text(encoding="utf-8")

    assert "dialog_id" not in coreset
    assert "dialog_id" not in learner


def test_coreset_selector_requires_sample_id() -> None:
    selector = CoresetSelector(strategy="loss_topk")
    bad_samples = [{"text": "no id"}, {"sample_id": "ok", "text": "x"}]

    with pytest.raises(ValueError, match="sample_id"):
        selector.select(samples=bad_samples, target_size=1)


def test_continual_learner_requires_sample_id() -> None:
    learner = OnlineContinualLearner(buffer_size=8, replay_ratio=0.25)

    with pytest.raises(ValueError, match="sample_id"):
        learner.update_buffer(new_samples=[{"text": "no id"}])
