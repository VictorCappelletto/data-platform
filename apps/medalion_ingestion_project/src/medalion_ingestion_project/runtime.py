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
    app_src = root / "apps" / PROJECT_ID / "src"
    if str(app_src) not in sys.path:
        sys.path.insert(0, str(app_src))
    return root
