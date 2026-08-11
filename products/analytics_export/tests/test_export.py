from analytics_export.pipelines.export import run_export
from hdl_ingest.pipelines.ingest import run_pipeline
from kpi_metrics.pipelines.metrics import run_kpi_pipeline


def test_end_to_end_export(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    monkeypatch.setenv("LAKE_BACKEND", "local")
    run_pipeline()
    run_kpi_pipeline()
    exported = run_export()
    assert len(exported) == 3
    assert {r["kpi_name"] for r in exported} >= {
        "gmv_completed",
        "active_customers",
        "completion_rate",
    }
