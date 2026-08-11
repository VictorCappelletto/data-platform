"""Airflow DAG — analytics_export (project: medalion_ingestion_project)."""

import _bootstrap  # noqa: F401
from factory import build_dag_from_yaml

dag = build_dag_from_yaml("analytics_export", project="medalion_ingestion_project")
