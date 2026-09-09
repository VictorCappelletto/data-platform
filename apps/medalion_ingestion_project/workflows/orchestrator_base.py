"""Shared helpers for orchestrator entry points."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from dataplatform.bootstrap import bootstrap

APP_ID = "medalion_ingestion_project"


def run_task(
    task_id: str,
    domain_fn: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    """Bootstrap app context and delegate to domain pipeline code."""
    bootstrap(APP_ID)
    return domain_fn(**kwargs)


def log_result(task_id: str, result: Any) -> None:
    print(json.dumps({"task_id": task_id, "result": result}, default=str))
