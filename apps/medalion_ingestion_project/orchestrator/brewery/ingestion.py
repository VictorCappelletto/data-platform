"""Orchestrator — brewery ingest task (brewery_ingest workflow)."""

from __future__ import annotations

from typing import Any

from ingestion.brewery import run_ingest_pipeline as _run_ingest_pipeline
from workflows.orchestrator_base import log_result, run_task

TASK_ID = "ingest_landing_bronze_silver"


def run(**kwargs: Any) -> dict[str, Any]:
    return run_task(TASK_ID, _run_ingest_pipeline, **kwargs)


def main() -> None:
    log_result(TASK_ID, run())


if __name__ == "__main__":
    main()
