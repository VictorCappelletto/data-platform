"""Embedding backends — hashed tokens (tests) and Azure OpenAI (vector search)."""

from __future__ import annotations

import hashlib
import math
import os
from typing import Any, Protocol

from dataplatform.utils import get_logger

logger = get_logger(__name__)


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashedTokenEmbedding:
    """Deterministic bag-of-tokens vector. Tests the cosine path without Azure."""

    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_vector(text, self.dimensions) for text in texts]


def _embed_with_retry(client: object, deployment: str, batch: list[str]):
    import time

    from openai import RateLimitError

    last_error: Exception | None = None
    for attempt in range(8):
        try:
            return client.embeddings.create(model=deployment, input=batch)
        except RateLimitError as exc:
            last_error = exc
            time.sleep(min(15 * (attempt + 1), 90))
    assert last_error is not None
    raise last_error


class AzureOpenAiEmbeddings:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str,
        dimensions: int,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 16):
            batch = texts[start : start + 16]
            response = _embed_with_retry(client, self.deployment, batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([list(item.embedding) for item in ordered])
        return vectors


def build_embeddings(provider: str, cfg: dict[str, Any]) -> EmbeddingClient:
    name = (provider or "local").lower()
    dimensions = int(cfg.get("embedding_dimensions", 1536))
    if name in {"echo", "local", "hash"}:
        return HashedTokenEmbedding(dimensions=32)
    if name in {"azure_openai", "azure", "azure_search"}:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if not endpoint or not api_key:
            logger.warning("Azure OpenAI env missing — falling back to hashed embeddings")
            return HashedTokenEmbedding(dimensions=32)
        return AzureOpenAiEmbeddings(
            endpoint=endpoint,
            api_key=api_key,
            deployment=str(cfg.get("embedding_deployment", "text-embedding-3-small")),
            api_version=str(cfg.get("api_version", "2024-10-21")),
            dimensions=dimensions,
        )
    raise ValueError(f"Unknown embedding provider: {provider}")


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    norm_l = math.sqrt(sum(a * a for a in left)) or 1.0
    norm_r = math.sqrt(sum(b * b for b in right)) or 1.0
    return dot / (norm_l * norm_r)


def _hash_vector(text: str, dimensions: int) -> list[float]:
    vec = [0.0] * dimensions
    for token in text.lower().replace("/", " ").split():
        if len(token) <= 2:
            continue
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        vec[int(digest, 16) % dimensions] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
