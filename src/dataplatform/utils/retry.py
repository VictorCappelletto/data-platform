from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from dataplatform.utils.logging import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


def retry(
    times: int = 3,
    delay_seconds: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Simple retry decorator for transient IO / network failures."""

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            while True:
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    attempt += 1
                    if attempt >= times:
                        raise
                    logger.warning(
                        "retry %s/%s for %s: %s",
                        attempt,
                        times,
                        fn.__name__,
                        exc,
                    )
                    time.sleep(delay_seconds * attempt)

        return wrapper

    return decorator
