"""Thin Airflow/CLI front door — same convention as the other apps.

Product surface is MCP + `workflows/runs/agent.py`. This module exists so
`config/orchestration/agent.yml` can stay config-driven.
"""

from __future__ import annotations

from typing import Any

from workflows.orchestrator_base import run_task


def _run(task_id: str, **kwargs: Any) -> dict[str, Any]:
    from agent import agent_book as domain

    return run_task(task_id, getattr(domain, f"run_{task_id}"), **kwargs)


def run_ask(**kwargs: Any) -> dict[str, Any]:
    return _run("ask", **kwargs)


def run_note(**kwargs: Any) -> dict[str, Any]:
    return _run("note", **kwargs)


def run_example(**kwargs: Any) -> dict[str, Any]:
    return _run("example", **kwargs)


def run_quote(**kwargs: Any) -> dict[str, Any]:
    return _run("quote", **kwargs)


def run_chat(**kwargs: Any) -> dict[str, Any]:
    return _run("chat", **kwargs)


def run_feedback(**kwargs: Any) -> dict[str, Any]:
    return _run("feedback", **kwargs)
