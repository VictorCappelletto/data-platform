"""Bootstrap env + PYTHONPATH for local scripts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from medalion_ingestion_project import PROJECT_ID


def bootstrap() -> Path:
    root = Path(__file__).resolve().parents[4]
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(root))
    os.environ.setdefault("DATA_PLATFORM_APP", PROJECT_ID)
    os.environ.setdefault("PLATFORM_ENV", "local")
    app_root = root / "apps" / PROJECT_ID
    for path in (app_root / "src", app_root):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return root
