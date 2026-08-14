from dataplatform.config import ConfigLoader

APP_ID = "ingestion_azure"


def test_app_config_loads():
    loader = ConfigLoader(app=APP_ID)
    app = loader.app_settings("local")
    assert app.app_id == "ingestion_azure"
    ingestion = loader.process("ingestion", "local")
    assert ingestion["orders"]["source_table"] == "dbo.orders"
