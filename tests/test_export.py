from pathlib import Path

from medalion_ingestion_project.ingestion.orders.pipeline import run_pipeline
from medalion_ingestion_project.transformation.export import run_export
from medalion_ingestion_project.transformation.kpi import run_kpi_pipeline

PROJECT = "medalion_ingestion_project"


def test_end_to_end_export(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(repo))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    run_pipeline()
    run_kpi_pipeline()
    exported = run_export()
    assert len(exported) == 3
    assert {r["kpi_name"] for r in exported} >= {
        "gmv_completed",
        "active_customers",
        "completion_rate",
    }
