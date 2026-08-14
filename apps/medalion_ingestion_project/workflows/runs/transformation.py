"""Local run — transformation process (brewery DQ/gold + KPI)."""

from __future__ import annotations

from typing import Any

from orchestrator import transformation


def run_brewery_dq_gold(**kwargs: Any) -> list[dict[str, Any]]:
    return transformation.run_brewery_dq_gold(**kwargs)


def run_kpi(**kwargs: Any) -> list[dict[str, Any]]:
    return transformation.run_kpi(**kwargs)


def main() -> None:
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)
    log_result("kpi", run_kpi())


if __name__ == "__main__":
    main()
