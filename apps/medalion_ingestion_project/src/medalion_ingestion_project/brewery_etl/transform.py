from __future__ import annotations

from typing import Any

from dataplatform.utils.logging import get_logger

logger = get_logger(__name__)


def transform_breweries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize brewery records for lake layers."""
    if not rows:
        return []
    out = [_transform_one(row) for row in rows]
    logger.info("transformed %s records", len(out))
    return out


def _transform_one(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": _safe_str(record.get("id"), 200),
        "name": _safe_str(record.get("name"), 255),
        "brewery_type": _safe_str(record.get("brewery_type"), 100),
        "address_1": _safe_str(record.get("address_1"), 255),
        "address_2": _safe_str(record.get("address_2"), 255),
        "address_3": _safe_str(record.get("address_3"), 255),
        "city": _safe_str(record.get("city"), 100),
        "state_province": _safe_str(record.get("state_province"), 100),
        "postal_code": _safe_str(record.get("postal_code"), 50),
        "country": _safe_str(record.get("country"), 100),
        "longitude": _safe_float(record.get("longitude")),
        "latitude": _safe_float(record.get("latitude")),
        "phone": _safe_str(record.get("phone"), 50),
        "website_url": _safe_str(record.get("website_url"), 500),
        "state": _safe_str(record.get("state"), 100),
        "street": _safe_str(record.get("street"), 255),
    }


def _safe_str(value: Any, max_len: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
