"""Airflow DAG — Agent Book agent (app: agent_book)."""

import _bootstrap  # noqa: F401

from dataplatform.airflow import build_dag_from_yaml

dag = build_dag_from_yaml("agent", app="agent_book")
