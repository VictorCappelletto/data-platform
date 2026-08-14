import pytest

from pathlib import Path

from dataplatform.config import ConfigLoader
from dataplatform.lake import Layer, LayerPaths
from dataplatform.utils import SecretNotFoundError, get_secret
from utils.settings import load_app_settings

APP = "medalion_ingestion_project"


def test_layer_paths_local():
    loader = ConfigLoader(app=APP)
    app = loader.app_settings("local")
    paths = LayerPaths.from_settings(loader.platform("local"), app)
    p = paths.table_path(Layer.SILVER, "orders", "orders")
    assert p.replace("\\", "/").endswith(
        "local/medalion_ingestion_project/silver/orders/orders"
    )


def test_platform_config_from_yaml():
    loader = ConfigLoader(app=APP)
    cfg = loader.platform("local")
    assert cfg.lake.backend == "local"
    app = load_app_settings(loader, "local")
    assert app.orders.domain == "orders"


def test_dag_config_from_yaml():
    loader = ConfigLoader(app=APP)
    dag = loader.dag("ingestion")
    assert dag.dag_id == "ingestion"
    assert len(dag.tasks) >= 4


def test_process_config_from_yaml():
    loader = ConfigLoader(app=APP)
    ingestion = loader.process("ingestion", "local")
    assert ingestion["orders"]["domain"] == "orders"
    assert ingestion["orders"]["seed_path"] == "seeds/orders_raw.csv"
    extraction = loader.process("extraction", "local")
    assert extraction["brewery"]["use_fixture"] is True
    consumption = loader.process("consumption", "local")
    assert consumption["analytics_export"]["target"]["domain"] == "analytics"


def test_orchestration_registry():
    loader = ConfigLoader(app=APP)
    registry = loader.orchestration("ingestion")
    assert registry["workflow_id"] == "ingestion"
    assert (
        registry["tasks"]["orders_landing"]["orchestrator"]
        == "orchestrator.ingestion:run_orders_landing"
    )
    dag = loader.dag("ingestion")
    assert dag.tasks[0].entry_point == "orchestrator.ingestion:run_brewery_ingest"


def test_lake_root_is_absolute():
    loader = ConfigLoader(app=APP)
    cfg = loader.platform("local")
    assert Path(cfg.lake.root).is_absolute()


def test_blocks_root_scaffold_dirs(tmp_path, monkeypatch: pytest.MonkeyPatch):
    from dataplatform.paths import ensure_write_parent

    monkeypatch.setenv("DATA_PLATFORM_ROOT", str(tmp_path))
    with pytest.raises(ValueError, match="seeds"):
        ensure_write_parent(tmp_path / "seeds" / "orders.csv")


def test_get_secret_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_DB_PASSWORD", "s3cret")
    assert get_secret("DEMO_DB_PASSWORD") == "s3cret"


def test_get_secret_missing_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MISSING_SECRET_XYZ", raising=False)
    with pytest.raises(SecretNotFoundError):
        get_secret("MISSING_SECRET_XYZ")
