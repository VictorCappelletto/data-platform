.PHONY: help install test lint demo dag-validate up down inspect

help:
	@echo "Targets: install | test | lint | demo | dag-validate | inspect | up | down"

install:
	python -m pip install -U pip
	python -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check src dags scripts tests apps

demo:
	python scripts/run_demo_pipeline.py

brewery-demo:
	python scripts/run_brewery_demo.py

dag-validate:
	python scripts/validate_dags.py

inspect:
	python scripts/inspect_lake.py

up:
	docker compose up -d postgres minio airflow-init airflow-webserver airflow-scheduler

down:
	docker compose down
