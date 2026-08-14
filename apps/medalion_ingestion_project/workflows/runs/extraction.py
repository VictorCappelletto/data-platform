"""Local run — extraction process (brewery API / fixture)."""

from __future__ import annotations

from typing import Any

from orchestrator.extraction import run_brewery_extract


def run(**kwargs: Any) -> list[dict[str, Any]]:
    return run_brewery_extract(**kwargs)


def main() -> None:
    from dataplatform.bootstrap import bootstrap
    from workflows.orchestrator_base import APP_ID, log_result

    bootstrap(APP_ID)
    log_result("brewery_extract", run())


if __name__ == "__main__":
    main()
