"""Local workflow run — full brewery chain (ingest → DQ → gold)."""

from __future__ import annotations

TASK_ID = "brewery_demo"


def run(**kwargs: object) -> dict[str, object]:
    from transformation.brewery import run_full_pipeline as _run_full_pipeline
    from workflows.orchestrator_base import run_task

    return run_task(TASK_ID, _run_full_pipeline, **kwargs)


def main() -> None:
    from workflows.orchestrator_base import log_result

    log_result(TASK_ID, run())


if __name__ == "__main__":
    import sys
    from pathlib import Path

    app_root = Path(__file__).resolve().parents[2]
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))
    from runtime import bootstrap

    bootstrap()
    main()
