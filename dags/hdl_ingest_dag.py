"""Airflow DAGs — thin orchestration over product pipelines."""

from __future__ import annotations

from datetime import datetime

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:  # Allow repo checkout without Airflow installed
    DAG = None  # type: ignore
    PythonOperator = None  # type: ignore


def _task_landing():
    from hdl_ingest.pipelines.ingest import run_landing

    return run_landing()


def _task_bronze():
    from hdl_ingest.pipelines.ingest import run_bronze

    return len(run_bronze())


def _task_silver():
    from hdl_ingest.pipelines.ingest import run_silver

    return len(run_silver())


if DAG is not None:
    with DAG(
        dag_id="hdl_ingest",
        start_date=datetime(2026, 1, 1),
        schedule="@daily",
        catchup=False,
        tags=["hdl", "medallion", "orders"],
        default_args={"owner": "data-platform"},
    ) as dag:
        landing = PythonOperator(task_id="landing", python_callable=_task_landing)
        bronze = PythonOperator(task_id="bronze", python_callable=_task_bronze)
        silver = PythonOperator(task_id="silver", python_callable=_task_silver)
        landing >> bronze >> silver
