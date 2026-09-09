from pathlib import Path

import pytest

from dataplatform.config import ConfigLoader
from dataplatform.data_quality import DataQualityError
from dataplatform.lake import Layer, LayerPaths
from ingestion.base import PartitionedIngestionBase
from ingestion.brewery import BreweryIngestPipeline, run_ingest_pipeline
from transformation.brewery import BreweryTransformPipeline, run_dq_gold, run_full_pipeline

PROJECT = "medalion_ingestion_project"


def _repo() -> Path:
    return Path(__file__).resolve().parents[3]


def _app_seeds() -> Path:
    return Path(__file__).resolve().parents[1] / "seeds"


def test_partition_key():
    row = {"country": "United States", "state": "Ohio"}
    assert PartitionedIngestionBase.partition_key(row) == ("UNITED STATES", "OHIO")


def test_partition_path_local(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(_repo()))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    loader = ConfigLoader(app=PROJECT)
    paths = LayerPaths.from_settings(loader.platform(), loader.app_settings())
    p = PartitionedIngestionBase.partition_path(
        Layer.BRONZE,
        country="US",
        state="OH",
        load_dt="2026-08-12",
        paths=paths,
    )
    assert "country=US/state=OH/load_date=2026-08-12" in p.replace("\\", "/")


def test_transform_truncates():
    rows = BreweryIngestPipeline().to_bronze(
        [{"id": "x", "name": "n" * 300, "brewery_type": "micro", "longitude": "bad"}]
    )
    assert len(rows[0]["name"]) == 255
    assert rows[0]["longitude"] is None


def test_gold_transform_enriches_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(_repo()))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    pipeline = BreweryTransformPipeline()
    pipeline._current_load_dt = "2026-08-12"
    gold = pipeline.transform(
        [
            {
                "id": "1",
                "name": "MadTree Brewing",
                "brewery_type": "regional",
                "country": "United States",
                "state": "Ohio",
                "city": "Cincinnati",
                "latitude": 39.1,
                "longitude": -84.4,
                "website_url": "http://www.madtreebrewing.com",
                "phone": "5138368733",
            }
        ]
    )
    row = gold[0]
    assert row["load_date"] == "2026-08-12"
    assert row["country_code"] == "US"
    assert row["state_code"] == "OH"
    assert row["has_coordinates"] is True
    assert row["is_craft"] is False


def test_duplicate_ids_fail():
    rows = [{"id": "a"}, {"id": "a"}]
    assert BreweryTransformPipeline().duplicate_ids(rows).passed is False


def test_ingest_pipeline_with_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(_repo()))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    fixture = _app_seeds() / "breweries_sample.json"
    stats = run_ingest_pipeline(fixture_path=str(fixture), load_dt="2026-08-12")
    assert stats["landing_rows"] == 4
    assert stats["silver_rows"] == 3


def test_full_pipeline_dq_passes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(_repo()))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    fixture = _app_seeds() / "breweries_sample.json"
    stats = run_full_pipeline(fixture_path=str(fixture), load_dt="2026-08-12")
    assert stats["gold_rows"] == 3


def test_dq_fails_on_empty_silver(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(_repo()))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    with pytest.raises(DataQualityError):
        run_dq_gold(load_dt="2099-01-01")
