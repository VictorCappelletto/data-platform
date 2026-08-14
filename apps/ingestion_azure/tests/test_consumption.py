"""Tests for consumption layer (SQL Server medallion publish)."""

import pytest

from consumption.sql_server_publish import SqlServerPublisher


def test_publish_rejects_invalid_identifier():
    publisher = SqlServerPublisher()
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        publisher.publish_table("bronze", "customers; DROP TABLE")


def test_publisher_config():
    publisher = SqlServerPublisher()
    transform = publisher.transform_config
    base_tables = list(transform.get("tables", []))
    filtered = [
        rule["output"]
        for rules in transform.get("filters", {}).values()
        for rule in rules
    ]

    assert publisher.consumption_database == "olist_dw"
    assert "customers" in base_tables
    assert "customers_RJ" in filtered
    assert set(publisher.product_config.get("layers", {})) == {"bronze", "silver", "gold"}


def test_consumption_config_loads():
    from dataplatform.config import ConfigLoader

    cfg = ConfigLoader(app="ingestion_azure").process("consumption", "local")
    assert cfg["olist"]["database"] == "olist_dw"
    assert cfg["olist"]["sql"]["column_type"] == "NVARCHAR(MAX)"
    assert cfg["olist"]["layers"]["bronze"]["lake_zone"] == "landing"
    assert cfg["olist"]["layers"]["silver"]["lake_zone"] == "processing"
    assert cfg["olist"]["layers"]["gold"]["lake_zone"] == "curated"
