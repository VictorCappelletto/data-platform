from __future__ import annotations

import os
from typing import Any

import requests
from platform_secrets import get_secret
from platform_utils.logging import get_logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = get_logger(__name__)

DEFAULT_API_URL = "https://api.openbrewerydb.org/v1/breweries"


class ExtractionError(RuntimeError):
    """Raised when API extraction fails."""


def _api_url() -> str:
    return get_secret("BREWERY_API_URL", default=os.getenv("BREWERY_API_URL", DEFAULT_API_URL))


def _session() -> requests.Session:
    retries = int(os.getenv("BREWERY_RETRY_ATTEMPTS", "3"))
    timeout = int(os.getenv("BREWERY_API_TIMEOUT", "30"))
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def extract_breweries(
    *,
    per_page: int | None = None,
    max_pages: int | None = None,
    session: requests.Session | None = None,
    **filters: Any,
) -> list[dict[str, Any]]:
    """
    Paginated extract from Open Brewery API.

    Persists nothing — caller writes landing. Limits pages via BREWERY_MAX_PAGES.
    """
    per_page = per_page or int(os.getenv("BREWERY_PER_PAGE", "50"))
    max_pages = max_pages or int(os.getenv("BREWERY_MAX_PAGES", "3"))
    url = _api_url()
    http = session or _session()
    timeout = getattr(http, "request_timeout", 30)

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
        if not _validate_batch(batch):
            raise ExtractionError("API response validation failed")
        all_rows.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    logger.info("extracted %s breweries (%s pages)", len(all_rows), page)
    return all_rows


def extract_from_fixture(path: str) -> list[dict[str, Any]]:
    """Load seed JSON for tests/demo without HTTP."""
    import json
    from pathlib import Path

    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ExtractionError("Fixture must be a JSON list")
    return data


def _validate_batch(batch: list[dict[str, Any]]) -> bool:
    if not batch:
        return True
    required = {"id", "name", "brewery_type"}
    first = batch[0]
    return required.issubset(first.keys())
