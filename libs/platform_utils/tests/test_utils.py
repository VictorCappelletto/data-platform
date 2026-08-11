from datetime import date

from platform_utils.dates import date_window
from platform_utils.retry import retry


def test_date_window_single_day():
    start, end = date_window(end=date(2026, 8, 12), days=1)
    assert start == date(2026, 8, 12)
    assert end == date(2026, 8, 12)


def test_date_window_multi_day():
    start, end = date_window(end=date(2026, 8, 12), days=3)
    assert start == date(2026, 8, 10)
    assert end == date(2026, 8, 12)


def test_retry_succeeds_after_failure():
    calls = {"n": 0}

    @retry(times=3, delay_seconds=0)
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 2
