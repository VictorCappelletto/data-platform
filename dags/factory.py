"""Build Airflow DAGs from apps/<id>/config/dags/*.yml."""

from __future__ import annotations

import importlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:
    DAG = None  # type: ignore
    PythonOperator = None  # type: ignore

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
os.environ.setdefault("DATA_PLATFORM_ROOT", str(_REPO_ROOT))


def _default_app() -> str | None:
    return os.getenv("DATA_PLATFORM_APP") or os.getenv("DATA_PLATFORM_PROJECT")


def _ensure_app_path(app: str) -> None:
    app_src = _REPO_ROOT / "apps" / app / "src"
    if app_src.is_dir() and str(app_src) not in sys.path:
        sys.path.insert(0, str(app_src))


from dataplatform.config.loader import ConfigLoader, DagConfig  # noqa: E402


def _import_callable(dotted: str):
    module_path, func_name = dotted.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, func_name)


def build_dag(config: DagConfig):
    if DAG is None or PythonOperator is None:
        return None

    default_args: dict = {"owner": config.owner}
    if config.pool:
        default_args["pool"] = config.pool
    if config.retries:
        default_args["retries"] = config.retries
        default_args["retry_delay"] = timedelta(minutes=config.retry_delay_minutes)

    dag_kwargs: dict = {
        "dag_id": config.dag_id,
        "start_date": datetime(2026, 1, 1),
        "schedule": config.schedule,
        "catchup": config.catchup,
        "tags": config.tags,
        "default_args": default_args,
    }
    if config.max_active_runs is not None:
        dag_kwargs["max_active_runs"] = config.max_active_runs
    if config.max_active_tasks is not None:
        dag_kwargs["max_active_tasks"] = config.max_active_tasks

    with DAG(**dag_kwargs) as dag:
        operators = {}
        for task in config.tasks:
            operators[task.task_id] = PythonOperator(
                task_id=task.task_id,
                python_callable=_import_callable(task.callable),
            )
        for task in config.tasks:
            for upstream in task.upstream:
                operators[upstream] >> operators[task.task_id]
    return dag


def build_dag_from_yaml(dag_id: str, app: str | None = None, project: str | None = None):
    app = app or project or _default_app()
    if not app:
        raise ValueError("build_dag_from_yaml requires app= or DATA_PLATFORM_APP")
    os.environ.setdefault("DATA_PLATFORM_APP", app)
    _ensure_app_path(app)
    loader = ConfigLoader(root=_REPO_ROOT, app=app)
    return build_dag(loader.dag(dag_id))
