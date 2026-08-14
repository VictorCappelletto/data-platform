"""Local run — extraction process (SQL → landing CSV)."""

from __future__ import annotations

from typing import Any

from orchestrator.extraction import run_landing_export


def run(**kwargs: Any) -> dict[str, int]:
    return run_landing_export(**kwargs)


def main() -> None:
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)
    log_result("landing_export", run())


if __name__ == "__main__":
    main()
