from pathlib import Path

import pytest

from dataplatform.config.loader import ConfigLoader
from dataplatform.dbutils import Layer, LayerPaths
from dataplatform.dq.runner import DataQualityError
from medalion_ingestion_project.ingestion.brewery.partition import partition_key, partition_path
from medalion_ingestion_project.ingestion.brewery.pipeline import run_ingest_pipeline
from medalion_ingestion_project.ingestion.brewery.transform import transform_breweries
from medalion_ingestion_project.transformation.brewery.pipeline import (
    duplicate_ids,
    run_dq_gold,
    run_full_pipeline,
)

PROJECT = "medalion_ingestion_project"


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def _app_seeds() -> Path:
    return _repo() / "apps" / PROJECT / "seeds"


def test_partition_key():
    row = {"country": "United States", "state": "Ohio"}
    assert partition_key(row) == ("UNITED STATES", "OHIO")


def test_partition_path_local(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(_repo()))
    monkeypatch.setenv("DATA_PLATFORM_APP", PROJECT)
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    loader = ConfigLoader(app=PROJECT)
    paths = LayerPaths.from_settings(loader.platform(), loader.app_settings())
    p = partition_path(
        Layer.BRONZE,
        country="US",
        state="OH",
        load_dt="2026-08-12",
        paths=paths,
    )
    assert "country=US/state=OH/load_date=2026-08-12" in p.replace("\\", "/")


def test_transform_truncates():
    rows = transform_breweries(
        [{"id": "x", "name": "n" * 300, "brewery_type": "micro", "longitude": "bad"}]
    )
    assert len(rows[0]["name"]) == 255
    assert rows[0]["longitude"] is None


def test_duplicate_ids_fail():
    rows = [{"id": "a"}, {"id": "a"}]
    assert duplicate_ids(rows).passed is False


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
