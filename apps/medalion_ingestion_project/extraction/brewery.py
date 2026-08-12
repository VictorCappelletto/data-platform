"""Brewery extraction — Open Brewery API or local JSON fixture."""

from __future__ import annotations

from typing import Any

from dataplatform.utils import get_secret
from extraction.base import ExtractionBase


class BreweryExtractor(ExtractionBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("brewery", environment)

    @property
    def _cfg(self):
        return self.app.brewery

    def _required_api_fields(self) -> set[str]:
        return set(self.constants.get("brewery", {}).get("required_api_fields", []))

    def extract_from_api(self, **filters: Any) -> list[dict[str, Any]]:
        cfg = self._cfg
        url = get_secret("BREWERY_API_URL", default=cfg.api_url)
        session = self.http_session(retry_attempts=cfg.retry_attempts, api_timeout=cfg.api_timeout)
        timeout = getattr(session, "request_timeout", cfg.api_timeout)
        return self.paginated_api_get(
            url=url,
            per_page=cfg.per_page,
            max_pages=cfg.max_pages,
            timeout=timeout,
            retry_attempts=cfg.retry_attempts,
            required_fields=self._required_api_fields(),
            session=session,
            **filters,
        )

    def extract(self, *, fixture_path: str | None = None) -> list[dict[str, Any]]:
        cfg = self._cfg
        required = self._required_api_fields()
        if fixture_path:
            return self.read_json_fixture(
                cfg.fixture_path,
                path=fixture_path,
                required_fields=required,
            )
        if cfg.use_fixture:
            return self.read_json_fixture(cfg.fixture_path, required_fields=required)
        return self.extract_from_api()
