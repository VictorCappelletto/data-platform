.PHONY: help install test lint clean-pycache clean-empty-dirs clean demo dag-validate up down inspect sql-up sql-init sql-down \
	secrets-init secrets-set secrets-add secrets-decrypt secrets-edit secrets-status secrets-export secrets-build \
	env-prepare azure-verify-rg azure-verify-storage azure-verify-adf azure-infra-deploy azure-sql-seed \
	azure-adf-publish azure-adf-trigger azure-olist-full azure-shir-setup azure-olist-transform azure-olist-publish-sql \
	olist-spark-catalog olist-publish-sql \
	azure-oidc-setup azure-oidc-verify azure-oidc-push



help:

	@echo "Targets: install | test | lint | clean-pycache | clean-empty-dirs | clean | demo | brewery-demo | inspect | up | down"
	@echo "         sql-up | sql-init | sql-down"
	@echo "         env-prepare | secrets-* | azure-verify-rg | azure-verify-storage | azure-verify-adf"
	@echo "         azure-infra-deploy | azure-sql-seed | azure-adf-publish | azure-adf-trigger | azure-olist-full"
	@echo "         azure-shir-setup (legacy local SQL) | azure-olist-transform | azure-olist-publish-sql"



install:

	python -m pip install -U pip

	python -m pip install -e ".[dev]"



clean-pycache:

	python -c "from pathlib import Path; from dataplatform.devtools import clean_pycache; print('removed', clean_pycache(Path('.')), 'cache paths')"



clean-empty-dirs:

	python -c "from pathlib import Path; from dataplatform.devtools import clean_empty_dirs; print('removed', clean_empty_dirs(Path('.')), 'empty dirs')"



clean: clean-pycache clean-empty-dirs



test: clean

	pytest apps/medalion_ingestion_project/tests -q

	pytest apps/ingestion_azure/tests -q



lint:

	ruff check dataplatform apps



demo:

	python apps/medalion_ingestion_project/workflows/runs/medalion_demo.py --mode orders_full



demo-bulk:

	python apps/medalion_ingestion_project/workflows/runs/medalion_demo.py --mode orders_full --bulk



brewery-demo:

	python apps/medalion_ingestion_project/workflows/runs/medalion_demo.py --mode brewery_full



brewery-demo-bulk:

	python apps/medalion_ingestion_project/workflows/runs/medalion_demo.py --mode brewery_full --bulk



inspect:

	python apps/medalion_ingestion_project/quality/inspect_lake.py



env-prepare: secrets-build

	docker compose --profile secrets run --rm secrets prepare



up: env-prepare

	docker compose up -d postgres minio airflow-init airflow-webserver airflow-scheduler



down:

	docker compose down



sql-up: env-prepare

	docker compose up -d sqlserver



sql-init: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/sql/setup.ps1 -UseDocker



sql-down:

	docker compose stop sqlserver



azure-verify-rg: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/verify-rg.ps1



azure-verify-storage: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/verify-storage.ps1



azure-verify-adf: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/verify-adf.ps1



azure-adf-publish: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/publish-adf.ps1



azure-adf-trigger: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/trigger-adf-landing.ps1 -PipelineName pl_olist_landing_copy



azure-olist-full: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/trigger-adf-landing.ps1 -PipelineName pl_olist_end_to_end



azure-olist-transform: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/run-adls-transform.ps1



azure-olist-publish-sql: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/publish-curated-sql.ps1



olist-publish-sql: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/consumption/publish-curated-sql.ps1



olist-spark-catalog: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/run-spark-sql-catalog.ps1



azure-shir-setup: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/setup-shir.ps1



azure-shir-repair:

	powershell -ExecutionPolicy Bypass -File docker/azure/repair-shir-admin.ps1



azure-infra-deploy: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/deploy-infra.ps1



azure-sql-seed: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/seed-azure-sql.ps1



azure-oidc-setup: env-prepare

	powershell -ExecutionPolicy Bypass -File docker/azure/setup-oidc.ps1



azure-oidc-verify:

	docker compose --profile azure run --rm --entrypoint verify-oidc azure



azure-oidc-push:

	powershell -ExecutionPolicy Bypass -File docker/azure/push-github-secrets.ps1



secrets-build:

	docker compose --profile secrets build secrets



secrets-init: secrets-build

	docker compose --profile secrets run --rm secrets init



secrets-set: secrets-build

	docker compose --profile secrets run --rm secrets set $(ARGS)



secrets-add: secrets-build

	docker compose --profile secrets run --rm secrets add $(FILE)



secrets-decrypt: secrets-build

	docker compose --profile secrets run --rm secrets decrypt



secrets-edit: secrets-build

	docker compose --profile secrets run --rm secrets edit



secrets-status: secrets-build

	docker compose --profile secrets run --rm secrets status



secrets-export: secrets-build

	docker compose --profile secrets run --rm secrets export
