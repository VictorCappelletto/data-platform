"""Ensure orchestrator entry points delegate to domain modules."""

from __future__ import annotations

from unittest.mock import patch


def test_extraction_orchestrator_delegates():
    with patch("orchestrator.extraction.run_task") as mock_run:
        from orchestrator.extraction import run_landing_export

        run_landing_export()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "landing_export"


def test_consumption_orchestrator_delegates():
    with patch("orchestrator.consumption.run_task") as mock_run:
        from orchestrator.consumption import run_publish_sql

        run_publish_sql()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "publish_sql"
