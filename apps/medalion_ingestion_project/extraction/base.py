"""Shared helpers for extraction stage pipelines (API, fixtures, external sources)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from base import ProjectProcessBase


class ExtractionError(RuntimeError):
    """Raised when API or fixture extraction fails."""


class ExtractionBase(ProjectProcessBase, ABC):
    """Base for extraction-stage jobs (API, fixtures, external sources)."""

    PROCESS = "extraction"

    def __init__(self, domain_key: str, environment: str | None = None) -> None:
        super().__init__(self.PROCESS, domain_key, environment)

    def http_session(self, *, retry_attempts: int, api_timeout: int) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=retry_attempts,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        session.mount("http://", HTTPAdapter(max_retries=retry))
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.request_timeout = api_timeout  # type: ignore[attr-defined]
        return session

    def resolve_fixture_path(self, default_path: str, path: str | None = None) -> str:
        fixture = path or default_path
        return str(self.loader.resolve_project_path(fixture))

    def read_json_fixture(
        self,
        default_path: str,
        *,
        path: str | None = None,
        required_fields: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        fixture = self.resolve_fixture_path(default_path, path)
        with Path(fixture).open(encoding="utf-8") as fh:
            data = json.load(fh)
        return self.validate_list_payload(data, required_fields)

    def validate_list_payload(
        self,
        data: Any,
        required_fields: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(data, list):
            raise ExtractionError("Payload must be a JSON list")
        if data and required_fields and not required_fields.issubset(data[0].keys()):
            raise ExtractionError("Payload validation failed — missing required fields")
        return data

    def paginated_api_get(
        self,
        *,
        url: str,
        per_page: int,
        max_pages: int,
        timeout: int,
        retry_attempts: int = 3,
        required_fields: set[str] | None = None,
        session: requests.Session | None = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        http = session or self.http_session(retry_attempts=retry_attempts, api_timeout=timeout)
        required = required_fields or set()
        all_rows: list[dict[str, Any]] = []
        page = 1
        while page <= max_pages:
            params = {k: v for k, v in filters.items() if v is not None}
            params.update({"per_page": per_page, "page": page})
            self.logger.info("extract page=%s url=%s", page, url)
            try:
                response = http.get(url, params=params, timeout=timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                raise ExtractionError(f"API request failed on page {page}: {exc}") from exc

            batch = self.validate_list_payload(response.json(), required)
            if not batch:
                break
            all_rows.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        self.logger.info("extracted %s rows (%s pages)", len(all_rows), page)
        return all_rows

    @abstractmethod
    def extract(self, *, fixture_path: str | None = None) -> list[dict[str, Any]]:
        """Pull records from the configured source."""

    def run(self, *, fixture_path: str | None = None) -> list[dict[str, Any]]:
        rows = self.extract(fixture_path=fixture_path)
        self.logger.info("%s extraction complete: %s rows", self.domain_key, len(rows))
        return rows
