"""Orchestrator — orders silver task (hdl_ingest workflow)."""

from __future__ import annotations

from typing import Any

from ingestion.orders import run_silver as _run_silver
from workflows.orchestrator_base import log_result, run_task

TASK_ID = "silver"


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_task(TASK_ID, _run_silver, **kwargs)


def main() -> None:
    log_result(TASK_ID, {"rows": len(run())})


if __name__ == "__main__":
    main()
