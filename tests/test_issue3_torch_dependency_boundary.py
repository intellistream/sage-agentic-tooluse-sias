"""Regression tests for issue #3 torch dependency minimization."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_no_torch_imports_in_python_modules() -> None:
    root = _repo_root()

    python_files = [
        root / "__init__.py",
        root / "continual_learner.py",
        root / "core_types.py",
        root / "coreset_selector.py",
    ]

    for file_path in python_files:
        content = file_path.read_text(encoding="utf-8")
        assert "import torch" not in content
        assert "from torch" not in content


def test_pyproject_has_no_torch_dependency_declaration() -> None:
    pyproject = (_repo_root() / "pyproject.toml").read_text(encoding="utf-8")

    assert "torch>=" not in pyproject
    assert "[project.optional-dependencies]\ntorch" not in pyproject
    assert "[torch]" not in pyproject


def _run_all() -> None:
    test_no_torch_imports_in_python_modules()
    test_pyproject_has_no_torch_dependency_declaration()


if __name__ == "__main__":
    _run_all()
