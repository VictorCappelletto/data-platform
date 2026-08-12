"""Orchestrator — analytics export task (analytics_export workflow)."""

from __future__ import annotations

from typing import Any

from transformation.export import run_export as _run_export
from workflows.orchestrator_base import log_result, run_task

TASK_ID = "export_kpis"


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_task(TASK_ID, _run_export, **kwargs)


def main() -> None:
    rows = run()
    log_result(TASK_ID, {"rows": len(rows)})


if __name__ == "__main__":
    main()
