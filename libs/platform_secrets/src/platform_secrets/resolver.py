from __future__ import annotations

import json
import os


class SecretNotFoundError(KeyError):
    """Raised when a secret cannot be resolved from any backend."""


def get_secret(name: str, *, default: str | None = None) -> str:
    """
    Resolve a secret by name.

    Order:
    1. Environment variable (exact name, then uppercased)
    2. AWS Secrets Manager when PLATFORM_SECRETS_BACKEND=aws
    3. Optional default
    """
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
        raise RuntimeError(
            "boto3 is required for PLATFORM_SECRETS_BACKEND=aws"
        ) from exc

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
