"""Orchestrator — full orders chain for local demo (ingest → KPI → export)."""

from __future__ import annotations

from orchestrator.analytics.analytics_export import run as run_export
from orchestrator.analytics.kpi_metrics import run as run_kpi
from orchestrator.base import log_result, run_task
from orchestrator.orders.bronze import run as run_bronze
from orchestrator.orders.landing import run as run_landing
from orchestrator.orders.silver import run as run_silver

TASK_ID = "orders_demo"


def run(**_kwargs: object) -> dict[str, object]:
    from medalion_ingestion_project.ingestion.orders.pipeline import run_pipeline

    stats = run_task(TASK_ID, run_pipeline)
    kpis = run_kpi()
    exported = run_export()
    return {"ingest": stats, "kpis": len(kpis), "export_rows": len(exported)}


def run_step_by_step(**_kwargs: object) -> dict[str, object]:
    run_landing()
    run_bronze()
    run_silver()
    kpis = run_kpi()
    exported = run_export()
    return {"kpis": len(kpis), "export_rows": len(exported)}


def main() -> None:
    log_result(TASK_ID, run())


if __name__ == "__main__":
    main()
