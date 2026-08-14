"""Airflow DAG — ingestion (app: medalion_ingestion_project)."""

import _bootstrap  # noqa: F401

from dataplatform.airflow import build_dag_from_yaml

dag = build_dag_from_yaml("ingestion", app="medalion_ingestion_project")
