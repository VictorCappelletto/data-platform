"""Validate DAG modules import without requiring a running Airflow cluster."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    dags_dir = Path(__file__).resolve().parents[1] / "dags"
    for dag_file in sorted(dags_dir.glob("*_dag.py")):
        _load(dag_file.stem, dag_file)
        print(f"ok: {dag_file.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
