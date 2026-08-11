"""KPI metrics DAG — depends conceptually on silver layer."""

from __future__ import annotations

from datetime import datetime

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    DAG = None  # type: ignore
    PythonOperator = None  # type: ignore


def _run_kpis():
    from kpi_metrics.pipelines.metrics import run_kpi_pipeline

    return run_kpi_pipeline()


if DAG is not None:
    with DAG(
        dag_id="kpi_metrics",
        start_date=datetime(2026, 1, 1),
        schedule="@daily",
        catchup=False,
        tags=["kpi", "gold"],
        default_args={"owner": "data-platform"},
    ) as dag:
        PythonOperator(task_id="compute_kpis", python_callable=_run_kpis)
