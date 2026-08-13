from pathlib import Path

from ingestion.orders import OrdersIngestPipeline, run_pipeline

PROJECT = "medalion_ingestion_project"


def test_orders_to_bronze():
    pipeline = OrdersIngestPipeline()
    rows = pipeline.to_bronze(
        [
            {
                "order_id": "o-1",
                "customer_id": "c-1",
                "amount": "10.5",
                "status": "Completed",
                "country": "br",
                "event_ts": "2026-08-11T00:00:00Z",
                "load_at": "2026-08-11",
            }
        ]
    )
    assert rows[0]["status"] == "completed"
    assert rows[0]["country"] == "BR"
    assert rows[0]["amount"] == 10.5


def test_orders_is_current_dedupe():
    pipeline = OrdersIngestPipeline()
    bronze = [
        {
            "order_id": "o-1",
            "customer_id": "c-1",
            "amount": 10.0,
            "status": "pending",
            "country": "BR",
            "event_ts": "t1",
            "load_at": "2026-08-10",
        },
        {
            "order_id": "o-1",
            "customer_id": "c-1",
            "amount": 10.0,
            "status": "completed",
            "country": "BR",
            "event_ts": "t2",
            "load_at": "2026-08-12",
        },
    ]
    silver = pipeline.to_silver(bronze)
    current = [r for r in silver if r["is_current"]]
    assert len(current) == 1
    assert current[0]["status"] == "completed"


def test_run_pipeline(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(repo))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    stats = run_pipeline()
    assert stats["bronze_rows"] == 6
    assert stats["current_rows"] == 5
