from transformation.kpi import KpiTransformPipeline


def test_compute_kpis():
    silver = [
        {
            "order_id": "o-1",
            "customer_id": "c-1",
            "amount": 100.0,
            "status": "completed",
            "is_current": True,
        },
        {
            "order_id": "o-2",
            "customer_id": "c-2",
            "amount": 50.0,
            "status": "pending",
            "is_current": True,
        },
        {
            "order_id": "o-1-old",
            "customer_id": "c-1",
            "amount": 100.0,
            "status": "completed",
            "is_current": False,
        },
    ]
    kpis = {k["kpi_name"]: k["kpi_value"] for k in KpiTransformPipeline().transform(silver)}
    assert kpis["gmv_completed"] == 100.0
    assert kpis["active_customers"] == 2.0
    assert kpis["completion_rate"] == 0.5
