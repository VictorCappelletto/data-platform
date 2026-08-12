"""Set default app context for tests."""

from __future__ import annotations

from pathlib import Path

import pytest

APP_ID = "medalion_ingestion_project"
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(REPO_ROOT))
    monkeypatch.setenv("DATA_PLATFORM_APP", APP_ID)
