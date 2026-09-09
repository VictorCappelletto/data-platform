"""Airflow DAG — knowledge ingest (app: agent_book)."""

import _bootstrap  # noqa: F401

from dataplatform.airflow import build_dag_from_yaml

dag = build_dag_from_yaml("knowledge", app="agent_book")
