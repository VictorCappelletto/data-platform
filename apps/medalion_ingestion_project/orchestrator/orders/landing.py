"""Orchestrator — orders landing task (hdl_ingest DAG)."""

from __future__ import annotations

from typing import Any

from medalion_ingestion_project.ingestion.orders.pipeline import run_landing as _run_landing
from orchestrator.base import log_result, run_task

TASK_ID = "landing"


def run(**kwargs: Any) -> str:
    return run_task(TASK_ID, _run_landing, **kwargs)


def main() -> None:
    log_result(TASK_ID, run())


if __name__ == "__main__":
    main()
