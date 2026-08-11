"""Local helper to run the full demo pipeline without Airflow."""

from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("LAKE_ROOT", str(root / "data" / "lake"))
    os.environ.setdefault("PLATFORM_ENV", "local")
    os.environ.setdefault("LAKE_BACKEND", "local")

    from analytics_export.pipelines.export import run_export
    from hdl_ingest.pipelines.ingest import run_pipeline
    from kpi_metrics.pipelines.metrics import run_kpi_pipeline

    stats = run_pipeline()
    kpis = run_kpi_pipeline()
    exported = run_export()
    print({"ingest": stats, "kpis": kpis, "export_rows": len(exported)})


if __name__ == "__main__":
    main()
