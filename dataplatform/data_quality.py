"""Data quality checks and runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dataplatform.utils import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    message: str
    metrics: dict[str, Any]


def null_rate(rows: list[dict[str, Any]], column: str, max_rate: float = 0.0) -> CheckResult:
    if not rows:
        return CheckResult("null_rate", False, "empty dataset", {"rows": 0})
    nulls = sum(1 for r in rows if r.get(column) is None)
    rate = nulls / len(rows)
    ok = rate <= max_rate
    return CheckResult(
        name=f"null_rate:{column}",
        passed=ok,
        message=f"null rate={rate:.3f} max={max_rate:.3f}",
        metrics={"rows": len(rows), "nulls": nulls, "rate": rate},
    )


def range_check(
    rows: list[dict[str, Any]],
    column: str,
    *,
    min_value: float | None = None,
    max_value: float | None = None,
) -> CheckResult:
    violations = 0
    for row in rows:
        value = row.get(column)
        if value is None:
            continue
        if min_value is not None and value < min_value:
            violations += 1
        elif max_value is not None and value > max_value:
            violations += 1
    ok = violations == 0
    return CheckResult(
        name=f"range:{column}",
        passed=ok,
        message=f"violations={violations}",
        metrics={"violations": violations},
    )


def volume_vs_baseline(
    actual_count: int,
    baseline_count: int,
    *,
    max_variance_pct: float = 20.0,
) -> CheckResult:
    if baseline_count <= 0:
        return CheckResult(
            "volume_vs_baseline",
            False,
            "baseline must be > 0",
            {"actual": actual_count, "baseline": baseline_count},
        )
    variance = abs(actual_count - baseline_count) / baseline_count * 100
    ok = variance <= max_variance_pct
    return CheckResult(
        name="volume_vs_baseline",
        passed=ok,
        message=f"variance={variance:.2f}% max={max_variance_pct:.2f}%",
        metrics={
            "actual": actual_count,
            "baseline": baseline_count,
            "variance_pct": variance,
        },
    )


class DataQualityError(RuntimeError):
    """Raised when one or more data quality checks fail."""


def run_checks(results: list[CheckResult], *, raise_on_fail: bool = True) -> bool:
    failed = [r for r in results if not r.passed]
    for result in results:
        level = "info" if result.passed else "error"
        getattr(logger, level)("%s | %s | %s", result.name, result.passed, result.message)
    if failed and raise_on_fail:
        names = ", ".join(r.name for r in failed)
        raise DataQualityError(f"Data quality failed: {names}")
    return not failed
