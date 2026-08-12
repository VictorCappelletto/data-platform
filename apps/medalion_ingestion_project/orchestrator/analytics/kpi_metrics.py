"""Orchestrator — KPI metrics task (kpi_metrics DAG)."""

from __future__ import annotations

from typing import Any

from medalion_ingestion_project.transformation.kpi import run_kpi_pipeline as _run_kpi_pipeline
from orchestrator.base import log_result, run_task

TASK_ID = "compute_kpis"


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_task(TASK_ID, _run_kpi_pipeline, **kwargs)


def main() -> None:
    kpis = run()
    log_result(TASK_ID, {"metrics": len(kpis)})


if __name__ == "__main__":
    main()
