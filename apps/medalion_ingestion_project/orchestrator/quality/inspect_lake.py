"""Orchestrator — lake inspection (quality validation)."""

from __future__ import annotations

from typing import Any

TASK_ID = "inspect_lake"


def run(**kwargs: Any) -> dict[str, Any]:
    from quality.inspect_lake import format_report, run_inspect_lake
    from workflows.orchestrator_base import run_task

    report = run_task(TASK_ID, run_inspect_lake, **kwargs)
    print(format_report(report))
    return report


def main() -> None:
    from workflows.orchestrator_base import log_result

    report = run()
    log_result(TASK_ID, {
        "files": len(report["files"]),
        "orders_layers_ok": sum(
            1 for layer in report["orders"]["layers"].values() if layer["exists"]
        ),
        "brewery_partitions": sum(
            stats["partitions"] for stats in report["brewery"].values()
        ),
    })


if __name__ == "__main__":
    import sys
    from pathlib import Path

    app_root = Path(__file__).resolve().parents[2]
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    from runtime import bootstrap

    bootstrap()
    main()
