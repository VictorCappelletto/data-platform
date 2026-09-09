"""Ensure orchestrator entry points delegate to domain modules."""

from __future__ import annotations

from unittest.mock import patch


def test_ingestion_orchestrator_delegates():
    with patch("orchestrator.ingestion.run_task") as mock_run:
        from orchestrator.ingestion import run_orders_pipeline

        run_orders_pipeline()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "orders_pipeline"


def test_transformation_orchestrator_delegates():
    with patch("orchestrator.transformation.run_task") as mock_run:
        from orchestrator.transformation import run_kpi

        run_kpi()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "kpi"


def test_consumption_orchestrator_delegates():
    with patch("orchestrator.consumption.run_task") as mock_run:
        from orchestrator.consumption import run_analytics_export

        run_analytics_export()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "analytics_export"
