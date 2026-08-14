"""Bootstrap env + PYTHONPATH for local app scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dataplatform.config import repo_root


def app_dir(app_id: str | None = None) -> Path:
    app = app_id or os.getenv("DATA_PLATFORM_APP")
    if not app:
        raise ValueError("DATA_PLATFORM_APP required")
    return repo_root() / "apps" / app


def bootstrap(app_id: str | None = None) -> Path:
    root = repo_root()
    app = app_id or os.getenv("DATA_PLATFORM_APP")
    if not app:
        raise ValueError("Set DATA_PLATFORM_APP or pass app_id to bootstrap()")
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(root))
    os.environ.setdefault("DATA_PLATFORM_APP", app)
    os.environ.setdefault("PLATFORM_ENV", "local")
    app_path = app_dir(app)
    for path in (root, app_path):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return root
