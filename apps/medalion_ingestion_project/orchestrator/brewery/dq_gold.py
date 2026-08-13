"""Orchestrator — brewery DQ + gold task (brewery_dq_gold workflow)."""

from __future__ import annotations

from typing import Any

from transformation.brewery import run_dq_gold as _run_dq_gold
from workflows.orchestrator_base import log_result, run_task

TASK_ID = "dq_and_gold"


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_task(TASK_ID, _run_dq_gold, **kwargs)


def main() -> None:
    rows = run()
    log_result(TASK_ID, {"rows": len(rows)})


if __name__ == "__main__":
    main()
