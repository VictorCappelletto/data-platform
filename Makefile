.PHONY: help install test lint demo dag-validate up down inspect



help:

	@echo "Targets: install | test | lint | demo | brewery-demo | inspect | up | down"



install:

	python -m pip install -U pip

	python -m pip install -e ".[dev]"



test:

	pytest -q



lint:

	ruff check dataplatform apps



demo:

	python apps/medalion_ingestion_project/workflows/runs/orders_demo.py



brewery-demo:

	python apps/medalion_ingestion_project/workflows/runs/brewery_demo.py



inspect:

	python apps/medalion_ingestion_project/orchestrator/quality/inspect_lake.py



up:

	docker compose up -d postgres minio airflow-init airflow-webserver airflow-scheduler



down:

	docker compose down

