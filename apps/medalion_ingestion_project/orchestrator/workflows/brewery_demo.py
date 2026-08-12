"""Orchestrator — full brewery chain for local demo (ingest → DQ → gold)."""

from __future__ import annotations

from medalion_ingestion_project.transformation.brewery.pipeline import (
    run_full_pipeline as _run_full_pipeline,
)
from orchestrator.base import log_result, run_task

TASK_ID = "brewery_demo"


def run(**kwargs: object) -> dict[str, object]:
    return run_task(TASK_ID, _run_full_pipeline, **kwargs)


def main() -> None:
    log_result(TASK_ID, run())


if __name__ == "__main__":
    main()
