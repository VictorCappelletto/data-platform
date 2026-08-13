"""Local helper to run the full orders demo without Airflow."""

from __future__ import annotations


def main() -> None:
    from medalion_ingestion_project.ingestion.orders.pipeline import run_pipeline
    from medalion_ingestion_project.runtime import bootstrap
    from medalion_ingestion_project.transformation.export import run_export
    from medalion_ingestion_project.transformation.kpi import run_kpi_pipeline

    bootstrap()
    stats = run_pipeline()
    kpis = run_kpi_pipeline()
    exported = run_export()
    print({"ingest": stats, "kpis": len(kpis), "export_rows": len(exported)})


if __name__ == "__main__":
    main()
