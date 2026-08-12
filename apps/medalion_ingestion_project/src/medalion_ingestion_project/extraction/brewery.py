from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from dataplatform.secrets import get_secret
from dataplatform.utils.logging import get_logger
from medalion_ingestion_project.base import ProjectProcessBase

logger = get_logger(__name__)


class ExtractionError(RuntimeError):
    """Raised when API extraction fails."""


class BreweryExtractor(ProjectProcessBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("extraction", "brewery", environment)

    def _session(self) -> requests.Session:
        cfg = self.project.brewery
        session = requests.Session()
        retry = Retry(
            total=cfg.retry_attempts,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        session.mount("http://", HTTPAdapter(max_retries=retry))
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.request_timeout = cfg.api_timeout  # type: ignore[attr-defined]
        return session

    def extract_breweries(
        self,
        *,
        per_page: int | None = None,
        max_pages: int | None = None,
        session: requests.Session | None = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        cfg = self.project.brewery
        per_page = per_page or cfg.per_page
        max_pages = max_pages or cfg.max_pages
        url = get_secret("BREWERY_API_URL", default=cfg.api_url)
        required = set(self.constants["brewery"]["required_api_fields"])
        http = session or self._session()
        timeout = getattr(http, "request_timeout", cfg.api_timeout)

        all_rows: list[dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            params = {k: v for k, v in filters.items() if v is not None}
            params.update({"per_page": per_page, "page": page})
            logger.info("extract page=%s url=%s", page, url)
            try:
                response = http.get(url, params=params, timeout=timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ExtractionError(f"API request failed on page {page}: {exc}") from exc

            batch = response.json()
            if not isinstance(batch, list):
                raise ExtractionError("API response is not a list")
            if not batch:
                break
            if not required.issubset(batch[0].keys()):
                raise ExtractionError("API response validation failed")
            all_rows.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        logger.info("extracted %s breweries (%s pages)", len(all_rows), page)
        return all_rows

    def extract_from_fixture(self, path: str | None = None) -> list[dict[str, Any]]:
        fixture = path or str(
            self.loader.resolve_project_path(self.project.brewery.fixture_path)
        )
        with Path(fixture).open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ExtractionError("Fixture must be a JSON list")
        return data

    def extract(self, *, fixture_path: str | None = None) -> list[dict[str, Any]]:
        if fixture_path:
            return self.extract_from_fixture(fixture_path)
        if self.project.brewery.use_fixture:
            return self.extract_from_fixture()
        return self.extract_breweries()


def extract_breweries(**kwargs: Any) -> list[dict[str, Any]]:
    return BreweryExtractor().extract_breweries(**kwargs)


def extract_from_fixture(path: str) -> list[dict[str, Any]]:
    return BreweryExtractor().extract_from_fixture(path)
