"""Orchestrator — orders bronze task (hdl_ingest workflow)."""

from __future__ import annotations

from typing import Any

from ingestion.orders import run_bronze as _run_bronze
from workflows.orchestrator_base import log_result, run_task

TASK_ID = "bronze"


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_task(TASK_ID, _run_bronze, **kwargs)


def main() -> None:
    log_result(TASK_ID, {"rows": len(run())})


if __name__ == "__main__":
    main()
