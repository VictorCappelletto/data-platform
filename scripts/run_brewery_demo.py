"""Run brewery ETL using project YAML config (fixture or API)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP = "medalion_ingestion_project"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("DATA_PLATFORM_ROOT", str(root))
    os.environ.setdefault("DATA_PLATFORM_APP", APP)
    os.environ.setdefault("PLATFORM_ENV", "local")
    app_src = root / "apps" / APP / "src"
    if str(app_src) not in sys.path:
        sys.path.insert(0, str(app_src))

    from medalion_ingestion_project.brewery_etl.pipelines import run_full_pipeline

    stats = run_full_pipeline()
    print(stats)


if __name__ == "__main__":
    main()
