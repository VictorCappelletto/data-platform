"""Local workflow run — full orders chain (ingest → KPI → export)."""

from __future__ import annotations

TASK_ID = "orders_demo"


def run(**_kwargs: object) -> dict[str, object]:
    from ingestion.orders import run_pipeline
    from orchestrator.analytics.analytics_export import run as run_export
    from orchestrator.analytics.kpi_metrics import run as run_kpi
    from workflows.orchestrator_base import run_task

    stats = run_task(TASK_ID, run_pipeline)
    kpis = run_kpi()
    exported = run_export()
    return {"ingest": stats, "kpis": len(kpis), "export_rows": len(exported)}


def run_step_by_step(**_kwargs: object) -> dict[str, object]:
    from orchestrator.analytics.analytics_export import run as run_export
    from orchestrator.analytics.kpi_metrics import run as run_kpi
    from orchestrator.orders.bronze import run as run_bronze
    from orchestrator.orders.landing import run as run_landing
    from orchestrator.orders.silver import run as run_silver

    run_landing()
    run_bronze()
    run_silver()
    kpis = run_kpi()
    exported = run_export()
    return {"kpis": len(kpis), "export_rows": len(exported)}


def main() -> None:
    from workflows.orchestrator_base import log_result

    log_result(TASK_ID, run())


if __name__ == "__main__":
    import sys
    from pathlib import Path

    app_root = Path(__file__).resolve().parents[2]
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    from runtime import bootstrap

    bootstrap()
    main()
