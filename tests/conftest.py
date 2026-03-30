from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _bootstrap_package() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    if "sage_sias" in sys.modules:
        return

    spec = importlib.util.spec_from_file_location(
        "sage_sias",
        repo_root / "__init__.py",
        submodule_search_locations=[str(repo_root)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to initialize sage_sias package for tests")

    module = importlib.util.module_from_spec(spec)
    sys.modules["sage_sias"] = module
    spec.loader.exec_module(module)


_bootstrap_package()
