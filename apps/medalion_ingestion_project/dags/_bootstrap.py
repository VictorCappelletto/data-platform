"""Bootstrap sys.path for Airflow DAG modules in app subfolder."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ID = "medalion_ingestion_project"
_REPO = Path(__file__).resolve().parents[3]
_APP_ROOT = _REPO / "apps" / APP_ID
_DAGS = _REPO / "dags"

for path in (_REPO / "src", _APP_ROOT / "src", _APP_ROOT, _DAGS):
    if path.is_dir() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("DATA_PLATFORM_ROOT", str(_REPO))
os.environ.setdefault("DATA_PLATFORM_APP", APP_ID)
