from __future__ import annotations

from platform_dq.checks import CheckResult
from platform_utils.logging import get_logger

logger = get_logger(__name__)


class DataQualityError(RuntimeError):
    """Raised when one or more DQ checks fail."""


def run_checks(results: list[CheckResult], *, raise_on_fail: bool = True) -> bool:
    failed = [r for r in results if not r.passed]
    for result in results:
        level = "info" if result.passed else "error"
        getattr(logger, level)("%s | %s | %s", result.name, result.passed, result.message)
    if failed and raise_on_fail:
        names = ", ".join(r.name for r in failed)
        raise DataQualityError(f"DQ failed: {names}")
    return not failed
