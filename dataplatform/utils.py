"""Shared platform utilities — logging, dates, retry, secrets."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import TypeVar

T = TypeVar("T")


# --- logging ---


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


# --- dates ---


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def date_window(end: date | None = None, days: int = 1) -> tuple[date, date]:
    if days < 1:
        raise ValueError("days must be >= 1")
    end_date = end or utc_today()
    start = end_date - timedelta(days=days - 1)
    return start, end_date


# --- retry ---


def retry(
    times: int = 3,
    delay_seconds: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    logger = get_logger(__name__)

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


# --- secrets ---


class SecretNotFoundError(KeyError):
    """Raised when a secret cannot be resolved from any backend."""


def get_secret(name: str, *, default: str | None = None) -> str:
    if name in os.environ and os.environ[name]:
        return os.environ[name]

    upper = name.upper()
    if upper in os.environ and os.environ[upper]:
        return os.environ[upper]

    backend = os.getenv("PLATFORM_SECRETS_BACKEND", "env").lower()
    if backend == "aws":
        value = _from_aws_secrets_manager(name)
        if value is not None:
            return value

    if default is not None:
        return default

    raise SecretNotFoundError(f"Secret not found: {name}")


def _from_aws_secrets_manager(name: str) -> str | None:
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("boto3 is required for PLATFORM_SECRETS_BACKEND=aws") from exc

    client = boto3.client(
        "secretsmanager",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    try:
        response = client.get_secret_value(SecretId=name)
    except client.exceptions.ResourceNotFoundException:
        return None

    if "SecretString" not in response:
        return None

    raw = response["SecretString"]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    if isinstance(parsed, dict):
        if name in parsed:
            return str(parsed[name])
        if len(parsed) == 1:
            return str(next(iter(parsed.values())))
    return raw
