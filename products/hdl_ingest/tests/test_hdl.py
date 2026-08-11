from hdl_ingest.pipelines.ingest import run_pipeline
from hdl_ingest.tables.orders import OrdersTable


def test_orders_to_bronze():
    table = OrdersTable()
    rows = table.to_bronze(
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
    table = OrdersTable()
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
    silver = table.to_silver(bronze)
    current = [r for r in silver if r["is_current"]]
    assert len(current) == 1
    assert current[0]["status"] == "completed"


def test_run_pipeline(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    monkeypatch.setenv("LAKE_BACKEND", "local")
    stats = run_pipeline()
    assert stats["bronze_rows"] == 6
    assert stats["current_rows"] == 5
