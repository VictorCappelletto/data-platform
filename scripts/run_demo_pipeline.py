"""Local helper to run the full demo pipeline without Airflow."""

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

    from medalion_ingestion_project.analytics_export.pipelines.export import run_export
    from medalion_ingestion_project.hdl_ingest.pipelines.ingest import run_pipeline
    from medalion_ingestion_project.kpi_metrics.pipelines.metrics import run_kpi_pipeline

    stats = run_pipeline()
    kpis = run_kpi_pipeline()
    exported = run_export()
    print({"ingest": stats, "kpis": kpis, "export_rows": len(exported)})


if __name__ == "__main__":
    main()
