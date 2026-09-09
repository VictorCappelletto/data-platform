"""Local run — ingestion process (brewery + orders)."""

from __future__ import annotations

from typing import Any

from orchestrator import ingestion


def run_brewery(**kwargs: Any) -> dict[str, Any]:
    return ingestion.run_brewery_ingest(**kwargs)


def run_orders(**kwargs: Any) -> dict[str, int]:
    return ingestion.run_orders_pipeline(**kwargs)


def main() -> None:
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)
    log_result("orders_pipeline", run_orders())


if __name__ == "__main__":
    main()
