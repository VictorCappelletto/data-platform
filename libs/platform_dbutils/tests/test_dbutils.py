from platform_dbutils.io import LakeIO
from platform_dbutils.paths import Layer, LayerPaths


def test_layer_paths_local(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("LAKE_BACKEND", "local")
    monkeypatch.setenv("PLATFORM_ENV", "local")
    paths = LayerPaths()
    p = paths.table_path(Layer.BRONZE, "orders", "orders")
    assert "bronze/orders/orders" in p.replace("\\", "/")
    assert str(tmp_path).replace("\\", "/") in p.replace("\\", "/")


def test_layer_paths_s3(monkeypatch):
    monkeypatch.setenv("LAKE_BACKEND", "s3")
    monkeypatch.setenv("LAKE_BUCKET", "my-lake")
    monkeypatch.setenv("PLATFORM_ENV", "dev")
    paths = LayerPaths()
    assert paths.table_path("gold", "kpi", "daily") == "s3a://my-lake/dev/gold/kpi/daily"


def test_lake_io_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("LAKE_ROOT", str(tmp_path))
    monkeypatch.setenv("PLATFORM_ENV", "local")
    paths = LayerPaths()
    io = LakeIO(paths)
    base = paths.table_path(Layer.SILVER, "demo", "t1")
    rows = [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}]
    written = io.write_json(base, rows)
    assert io.read_json(written) == rows
