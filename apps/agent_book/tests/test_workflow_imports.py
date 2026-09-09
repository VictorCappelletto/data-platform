"""Ensure Airflow workflow modules import without a running cluster."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

APP_ID = "agent_book"
APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]


def _load_workflow_module(name: str, path: Path) -> None:
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(REPO_ROOT))
    os.environ.setdefault("DATA_PLATFORM_APP", APP_ID)
    for entry in (REPO_ROOT, APP_ROOT, path.parent):
        if entry.is_dir() and str(entry) not in sys.path:
            sys.path.insert(0, str(entry))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)


def test_workflow_dag_modules_import() -> None:
    workflow_files = sorted((APP_ROOT / "workflows").glob("*_dag.py"))
    assert workflow_files, "expected at least one workflow module"
    for workflow_file in workflow_files:
        _load_workflow_module(workflow_file.stem, workflow_file)


def test_orchestration_registry_loads() -> None:
    from dataplatform.config import ConfigLoader

    loader = ConfigLoader(app=APP_ID)
    for process in ("knowledge", "agent"):
        registry = loader.orchestration(process)
        assert registry["workflow_id"] == process
        assert registry["process"] == process
