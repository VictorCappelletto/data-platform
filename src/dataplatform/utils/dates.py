from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def date_window(end: date | None = None, days: int = 1) -> tuple[date, date]:
    """Inclusive start / exclusive end window ending at `end` (default: UTC today)."""
    if days < 1:
        raise ValueError("days must be >= 1")
    end_date = end or utc_today()
    start = end_date - timedelta(days=days - 1)
    return start, end_date
