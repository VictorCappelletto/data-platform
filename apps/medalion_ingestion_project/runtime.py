"""Bootstrap env + PYTHONPATH for local scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ID = "medalion_ingestion_project"
PROJECT_ID = APP_ID


def app_root() -> Path:
    return Path(__file__).resolve().parent


def repo_root() -> Path:
    return app_root().parents[1]


def bootstrap() -> Path:
    root = repo_root()
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(root))
    os.environ.setdefault("DATA_PLATFORM_APP", APP_ID)
    os.environ.setdefault("PLATFORM_ENV", "local")
    app = app_root()
    for path in (root, app):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return root
