"""Local run — consumption process (lake → SQL Server olist_dw)."""

from __future__ import annotations

from typing import Any

from orchestrator.consumption import run_publish_sql


def run(**kwargs: Any) -> dict[str, Any]:
    return run_publish_sql(**kwargs)


def main() -> None:
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)
    log_result("publish_sql", run())


if __name__ == "__main__":
    main()
