from unittest.mock import patch


def test_knowledge_orchestrator_delegates():
    with patch("orchestrator.knowledge.run_task") as mock_run:
        from orchestrator.knowledge import run_ingest_book

        run_ingest_book()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "ingest_book"


def test_ask_orchestrator_delegates():
    with patch("orchestrator.agent.run_task") as mock_run:
        from orchestrator.agent import run_ask

        run_ask(question="x")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "ask"


def test_note_orchestrator_delegates():
    with patch("orchestrator.agent.run_task") as mock_run:
        from orchestrator.agent import run_note

        run_note(topic="y")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "note"


def test_example_orchestrator_delegates():
    with patch("orchestrator.agent.run_task") as mock_run:
        from orchestrator.agent import run_example

        run_example(topic="z")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "example"


def test_chat_orchestrator_delegates():
    with patch("orchestrator.agent.run_task") as mock_run:
        from orchestrator.agent import run_chat

        run_chat(message="x")
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "chat"
