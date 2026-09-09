"""Airflow DAG — transformation (app: ingestion_azure)."""

import _bootstrap  # noqa: F401

from dataplatform.airflow import build_dag_from_yaml

dag = build_dag_from_yaml("transformation", app="ingestion_azure")
