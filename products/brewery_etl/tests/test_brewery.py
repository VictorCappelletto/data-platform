from pathlib import Path

import pytest
from brewery_etl.partition import partition_key, partition_path
from brewery_etl.pipelines import duplicate_ids, run_dq_gold, run_full_pipeline, run_ingest_pipeline
from brewery_etl.transform import transform_breweries
from platform_dbutils import Layer, LayerPaths
from platform_dq.runner import DataQualityError


def test_partition_key():
    row = {"country": "United States", "state": "Ohio"}
    assert partition_key(row) == ("UNITED STATES", "OHIO")


def test_partition_path_local(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    paths = LayerPaths()
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
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    monkeypatch.setenv("LAKE_BACKEND", "local")
    root = Path(__file__).resolve().parents[3]
    fixture = root / "seeds" / "breweries_sample.json"
    stats = run_ingest_pipeline(fixture_path=str(fixture), load_dt="2026-08-12")
    assert stats["landing_rows"] == 4
    assert stats["silver_rows"] == 3  # deduped


def test_full_pipeline_dq_passes(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    monkeypatch.setenv("LAKE_BACKEND", "local")
    root = Path(__file__).resolve().parents[3]
    fixture = root / "seeds" / "breweries_sample.json"
    stats = run_full_pipeline(fixture_path=str(fixture), load_dt="2026-08-12")
    assert stats["gold_rows"] == 3


def test_dq_fails_on_empty_silver(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    with pytest.raises(DataQualityError):
        run_dq_gold(load_dt="2099-01-01", min_volume=1)
