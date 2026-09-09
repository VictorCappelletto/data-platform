"""Set default app context for tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ID = "ingestion_azure"
APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]

for path in (REPO_ROOT, APP_ROOT):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture(autouse=True)
def _app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("DATA_PLATFORM_APP", APP_ID)
    monkeypatch.setenv("MSSQL_SERVER", "localhost,1433")
    monkeypatch.setenv("MSSQL_DATABASE", "olist")
    monkeypatch.setenv("MSSQL_USER", "sa")
    monkeypatch.setenv("MSSQL_SA_PASSWORD", "Olist@Dev123!")
    for path in (REPO_ROOT, APP_ROOT):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
