"""Run KPI transformation locally."""

from __future__ import annotations

from medalion_ingestion_project.runtime import bootstrap
from medalion_ingestion_project.transformation.kpi import run_kpi_pipeline


def main() -> None:
    bootstrap()
    kpis = run_kpi_pipeline()
    print({"kpis": len(kpis)})


if __name__ == "__main__":
    main()
