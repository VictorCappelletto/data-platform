import pytest

from dataplatform.config.loader import ConfigLoader
from dataplatform.dbutils import Layer, LayerPaths
from dataplatform.secrets import SecretNotFoundError, get_secret

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
    app = loader.app_settings("local")
    assert app.orders.domain == "orders"


def test_dag_config_from_yaml():
    loader = ConfigLoader(app=APP)
    dag = loader.dag("hdl_ingest")
    assert dag.dag_id == "hdl_ingest"
    assert len(dag.tasks) == 3


def test_process_config_from_yaml():
    loader = ConfigLoader(app=APP)
    ingestion = loader.process("ingestion", "local")
    assert ingestion["orders"]["domain"] == "orders"
    extraction = loader.process("extraction", "local")
    assert extraction["brewery"]["use_fixture"] is True
    product = loader.product("hdl_ingest", "local")
    assert product["seed_path"] == "seeds/orders_raw.csv"


def test_orchestration_registry():
    loader = ConfigLoader(app=APP)
    registry = loader.orchestration("hdl_ingest")
    assert registry["workflow_id"] == "hdl_ingest"
    assert registry["tasks"]["landing"]["orchestrator"] == "orchestrator.orders.landing:run"
    dag = loader.dag("hdl_ingest")
    assert dag.tasks[0].entry_point == "orchestrator.orders.landing:run"


def test_get_secret_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DEMO_DB_PASSWORD", "s3cret")
    assert get_secret("DEMO_DB_PASSWORD") == "s3cret"


def test_get_secret_missing_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MISSING_SECRET_XYZ", raising=False)
    with pytest.raises(SecretNotFoundError):
        get_secret("MISSING_SECRET_XYZ")
