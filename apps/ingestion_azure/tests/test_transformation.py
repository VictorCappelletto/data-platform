"""Tests for Olist transformation (Databricks notebook port)."""

from dataplatform.config import ConfigLoader

from transformation.io import OlistLakeMount
from transformation.olist import OlistTransformPipeline


def test_lake_config_in_app_yml():
    raw = ConfigLoader(app="ingestion_azure").read_yaml(
        ConfigLoader(app="ingestion_azure").config_dir / "app.yml"
    )
    lake = raw["lake"]
    assert lake["zones"] == ["landing", "processing", "curated"]
    assert "uri_pattern" in lake["adls"]
    assert "{zone}" in lake["adls"]["zone_uri"]


def test_mount_local_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("OLIST_LAKE_BACKEND", "local")
    mount = OlistLakeMount(lake_prefix="ingestion_azure", environment="test")

    landing = mount.zone_uri("landing")
    assert landing.endswith("ingestion_azure/landing")

    csv_path = mount.file_path("landing", "customers.csv")
    assert csv_path.endswith("customers.csv")


def test_mount_adls_uri(monkeypatch):
    monkeypatch.setenv("OLIST_LAKE_BACKEND", "adls")
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "stolistdev")
    mount = OlistLakeMount()

    assert mount.zone_uri("processing") == (
        "abfss://processing@stolistdev.dfs.core.windows.net/"
    )


def test_mount_rejects_unknown_zone():
    mount = OlistLakeMount(environment="test")
    try:
        mount.zone_uri("bronze")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "Unknown lake zone" in str(exc)


def test_filter_customers_rj():
    pipeline = OlistTransformPipeline()
    rows = [
        {"customer_id": "1", "customer_state": "RJ"},
        {"customer_id": "2", "customer_state": "SP"},
        {"customer_id": "3", "customer_state": "RJ"},
    ]
    filtered = pipeline._apply_filters_local({"customers": rows})
    assert len(filtered["customers_RJ"]) == 2
    assert all(r["customer_state"] == "RJ" for r in filtered["customers_RJ"])


def test_processing_engine_default(monkeypatch):
    monkeypatch.delenv("OLIST_PROCESSING_ENGINE", raising=False)
    assert OlistTransformPipeline().engine == "local"


def test_processing_engine_spark(monkeypatch):
    monkeypatch.setenv("OLIST_PROCESSING_ENGINE", "spark")
    assert OlistTransformPipeline().engine == "spark"


def test_spark_path_local_uri(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    mount = OlistLakeMount(environment="test")
    uri = mount.spark_data_path("landing", "orders.csv")
    assert uri.startswith("file:///")
    assert uri.endswith("orders.csv")


def test_transformation_config_loads():
    cfg = ConfigLoader(app="ingestion_azure").process("transformation", "local")
    tables = cfg["olist"]["tables"]
    assert "customers" in tables
    assert cfg["olist"]["processing"]["engine"] == "local"
