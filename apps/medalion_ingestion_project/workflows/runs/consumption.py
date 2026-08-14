"""Local run — consumption process (analytics export)."""

from __future__ import annotations

from typing import Any

from orchestrator.consumption import run_analytics_export


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_analytics_export(**kwargs)


def main() -> None:
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)
    log_result("analytics_export", run())


if __name__ == "__main__":
    main()
