"""Airflow DAG — hdl_ingest (project: medalion_ingestion_project)."""

import _bootstrap  # noqa: F401
from factory import build_dag_from_yaml

dag = build_dag_from_yaml("hdl_ingest", project="medalion_ingestion_project")
