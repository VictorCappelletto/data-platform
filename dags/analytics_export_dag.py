"""Analytics export DAG with DQ gate."""

from __future__ import annotations

from datetime import datetime

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    DAG = None  # type: ignore
    PythonOperator = None  # type: ignore


def _run_export():
    from analytics_export.pipelines.export import run_export

    return run_export()


if DAG is not None:
    with DAG(
        dag_id="analytics_export",
        start_date=datetime(2026, 1, 1),
        schedule="@daily",
        catchup=False,
        tags=["analytics", "dq"],
        default_args={"owner": "data-platform"},
    ) as dag:
        PythonOperator(task_id="export_with_dq", python_callable=_run_export)
