.PHONY: help install test lint demo dag-validate up down

help:
	@echo "Targets: install | test | lint | demo | dag-validate | up | down"

install:
	python -m pip install -U pip pytest ruff python-dotenv
	python -m pip install -e libs/platform_utils
	python -m pip install -e libs/platform_secrets
	python -m pip install -e libs/platform_dbutils
	python -m pip install -e libs/platform_dq
	python -m pip install -e products/hdl_ingest
	python -m pip install -e products/kpi_metrics
	python -m pip install -e products/analytics_export
	python -m pip install -e products/brewery_etl

test:
	pytest -q

lint:
	ruff check libs products dags scripts

demo:
	python scripts/run_demo_pipeline.py

brewery-demo:
	python scripts/run_brewery_demo.py

dag-validate:
	python scripts/validate_dags.py

up:
	docker compose up -d postgres minio airflow-init airflow-webserver airflow-scheduler

down:
	docker compose down
