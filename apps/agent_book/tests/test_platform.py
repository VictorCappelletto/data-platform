from pathlib import Path

from dataplatform.config import ConfigLoader
from dataplatform.lake import Layer, LayerPaths

APP = "agent_book"


def test_layer_paths_local():
    loader = ConfigLoader(app=APP)
    app = loader.app_settings("local")
    paths = LayerPaths.from_settings(loader.platform("local"), app)
    p = paths.table_path(Layer.GOLD, "agent", "notes")
    assert p.replace("\\", "/").endswith("local/agent_book/gold/agent/notes")


def test_process_config_from_yaml():
    loader = ConfigLoader(app=APP)
    knowledge = loader.process("knowledge", "local")
    assert knowledge["book"]["domain"] == "knowledge"
    assert knowledge["book"]["path"].endswith(".txt")
    assert knowledge["book"]["search_provider"] == "local"
    assert knowledge["book"]["search_index"] == "agent_book-knowledge"
    agent = loader.process("agent", "local")
    assert agent["agent_book"]["llm_provider"] == "echo"
    assert agent["agent_book"]["table"] == "notes"


def test_dev_overrides_azure_providers():
    loader = ConfigLoader(app=APP)
    knowledge = loader.process("knowledge", "dev")
    assert knowledge["book"]["search_provider"] == "azure_search"
    agent = loader.process("agent", "dev")
    assert agent["agent_book"]["llm_provider"] == "azure_openai"
    assert agent["agent_book"]["search_provider"] == "azure_search"


def test_orchestration_registry():
    loader = ConfigLoader(app=APP)
    knowledge = loader.orchestration("knowledge")
    entry = knowledge["tasks"]["ingest_book"]["orchestrator"]
    assert entry == "orchestrator.knowledge:run_ingest_book"
    agent = loader.orchestration("agent")
    assert agent["tasks"]["ask"]["domain_module"] == "agent.agent_book:run_ask"
    assert agent["tasks"]["note"]["domain_module"] == "agent.agent_book:run_note"
    assert agent["tasks"]["example"]["domain_module"] == "agent.agent_book:run_example"
    assert agent["tasks"]["quote"]["domain_module"] == "agent.agent_book:run_quote"
    assert agent["tasks"]["chat"]["domain_module"] == "agent.agent_book:run_chat"
    assert agent["tasks"]["feedback"]["domain_module"] == "agent.agent_book:run_feedback"


def test_dag_config_from_yaml():
    loader = ConfigLoader(app=APP)
    dag = loader.dag("knowledge")
    assert dag.dag_id == "knowledge"
    assert dag.tasks[0].entry_point == "orchestrator.knowledge:run_ingest_book"


def test_lake_root_is_absolute():
    loader = ConfigLoader(app=APP)
    assert Path(loader.platform("local").lake.root).is_absolute()
