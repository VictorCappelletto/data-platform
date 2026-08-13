"""Medalion app settings — typed config built on top of the global ConfigLoader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dataplatform.config import ConfigLoader


@dataclass(frozen=True)
class BrewerySettings:
    api_url: str
    per_page: int
    max_pages: int
    use_fixture: bool
    fixture_path: str
    retry_attempts: int
    api_timeout: int


@dataclass(frozen=True)
class OrdersSettings:
    seed_path: str
    domain: str
    table: str


@dataclass(frozen=True)
class MedalionAppSettings:
    app_id: str
    name: str
    lake_prefix: str
    brewery: BrewerySettings
    orders: OrdersSettings


def load_app_settings(
    loader: ConfigLoader,
    environment: str | None = None,
) -> MedalionAppSettings:
    """Load medalion-specific app.yml + extraction/ingestion process config."""
    if not loader.app_dir:
        raise ValueError("load_app_settings() requires DATA_PLATFORM_APP or app= argument")
    env = (environment or os.getenv("PLATFORM_ENV", "local")).lower()
    raw = loader.read_yaml(loader.config_dir / "app.yml")
    app_id = raw.get("app_id") or raw.get("project_id") or loader.app
    extraction = loader.process("extraction", env)
    ingestion = loader.process("ingestion", env)
    brewery_raw = extraction.get("brewery", raw.get("brewery", {}))
    orders_raw = ingestion.get("orders", raw.get("orders", {}))
    return MedalionAppSettings(
        app_id=app_id,
        name=raw.get("name", app_id),
        lake_prefix=raw.get("lake_prefix", app_id),
        brewery=BrewerySettings(
            api_url=os.getenv("BREWERY_API_URL", brewery_raw["api_url"]),
            per_page=int(os.getenv("BREWERY_PER_PAGE", brewery_raw["per_page"])),
            max_pages=int(os.getenv("BREWERY_MAX_PAGES", brewery_raw["max_pages"])),
            use_fixture=os.getenv("BREWERY_USE_FIXTURE", str(brewery_raw["use_fixture"])) == "1"
            if "BREWERY_USE_FIXTURE" in os.environ
            else bool(brewery_raw["use_fixture"]),
            fixture_path=os.getenv("BREWERY_FIXTURE_PATH", brewery_raw["fixture_path"]),
            retry_attempts=int(
                os.getenv("BREWERY_RETRY_ATTEMPTS", brewery_raw["retry_attempts"])
            ),
            api_timeout=int(os.getenv("BREWERY_API_TIMEOUT", brewery_raw["api_timeout"])),
        ),
        orders=OrdersSettings(
            seed_path=os.getenv("ORDERS_SEED_PATH", orders_raw["seed_path"]),
            domain=orders_raw["domain"],
            table=orders_raw["table"],
        ),
    )
