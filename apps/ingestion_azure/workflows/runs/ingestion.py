"""Local run — ingestion process (legacy orders medallion)."""

from __future__ import annotations

from typing import Any

from orchestrator.ingestion import run_orders


def run(**kwargs: Any) -> dict[str, Any]:
    return run_orders(**kwargs)


def main() -> None:
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)
    log_result("orders", run())


if __name__ == "__main__":
    main()
