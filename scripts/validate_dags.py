"""Validate DAG modules import without requiring a running Airflow cluster."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

APP_ID = "medalion_ingestion_project"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    root = _repo_root()
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(root))
    os.environ.setdefault("DATA_PLATFORM_APP", APP_ID)
    src = root / "src"
    app_src = root / "apps" / APP_ID / "src"
    dags = root / "dags"
    for entry in (src, app_src, dags, path.parent):
        if str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    root = _repo_root()
    dag_files = sorted(root.glob("apps/*/dags/*_dag.py"))
    for dag_file in dag_files:
        _load(dag_file.stem, dag_file)
        print(f"ok: {dag_file.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
