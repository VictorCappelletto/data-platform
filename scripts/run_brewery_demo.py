"""Local helper to run the full brewery demo without Airflow."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP = "medalion_ingestion_project"


def _bootstrap_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(root))
    os.environ.setdefault("DATA_PLATFORM_APP", APP)
    os.environ.setdefault("PLATFORM_ENV", "local")
    app_root = root / "apps" / APP
    for path in (app_root / "src", app_root):
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


def main() -> None:
    _bootstrap_paths()
    from orchestrator.workflows.brewery_demo import main as run_brewery_demo

    run_brewery_demo()


if __name__ == "__main__":
    main()
