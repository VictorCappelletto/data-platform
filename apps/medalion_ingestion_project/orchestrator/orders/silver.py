"""Orchestrator — orders silver task (hdl_ingest DAG)."""

from __future__ import annotations

from typing import Any

from medalion_ingestion_project.ingestion.orders.pipeline import run_silver as _run_silver
from orchestrator.base import log_result, run_task

TASK_ID = "silver"


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_task(TASK_ID, _run_silver, **kwargs)


def main() -> None:
    rows = run()
    log_result(TASK_ID, {"rows": len(rows)})


if __name__ == "__main__":
    main()
