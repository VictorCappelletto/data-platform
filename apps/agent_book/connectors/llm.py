"""LLM backends — echo (tests/demo) and Azure OpenAI (dev)."""

from __future__ import annotations

import os
from typing import Any, Protocol

from dataplatform.utils import get_logger

logger = get_logger(__name__)


class LlmClient(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


class EchoLlm:
    """Deterministic stand-in so Agent Book runs without cloud credentials."""

    tokens_in: int | None = None
    tokens_out: int | None = None

    def reset_usage(self) -> None:
        self.tokens_in = None
        self.tokens_out = None

    def complete(self, *, system: str, user: str) -> str:
        del system
        return user.strip()


class AzureOpenAiLlm:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        deployment: str,
        api_version: str,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version
        self._client: Any = None
        self.tokens_in: int | None = None
        self.tokens_out: int | None = None

    def reset_usage(self) -> None:
        self.tokens_in = 0
        self.tokens_out = 0

    def complete(self, *, system: str, user: str) -> str:
        from openai import AzureOpenAI

        if self._client is None:
            self._client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
        kwargs: dict[str, Any] = {
            "model": self.deployment,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if _is_reasoning_chat_model(self.deployment):
            kwargs["max_completion_tokens"] = 2048
        else:
            kwargs["temperature"] = 0.2
            kwargs["max_tokens"] = 800
        response = self._client.chat.completions.create(**kwargs)
        usage = getattr(response, "usage", None)
        if usage is not None:
            prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion = int(getattr(usage, "completion_tokens", 0) or 0)
            self.tokens_in = (self.tokens_in or 0) + prompt
            self.tokens_out = (self.tokens_out or 0) + completion
        return (response.choices[0].message.content or "").strip()


def resolve_llm_provider(cfg: dict[str, Any]) -> str:
    return (
        os.getenv("AGENT_BOOK_LLM_PROVIDER") or str(cfg.get("llm_provider", "echo"))
    ).lower()


def build_llm(provider: str, cfg: dict[str, Any]) -> LlmClient:
    name = (provider or "echo").lower()
    if name in {"echo", "local"}:
        return EchoLlm()
    if name in {"azure_openai", "azure"}:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if not endpoint or not api_key:
            logger.warning("Azure OpenAI env missing — falling back to echo LLM")
            return EchoLlm()
        return AzureOpenAiLlm(
            endpoint=endpoint,
            api_key=api_key,
            deployment=str(cfg.get("chat_deployment", "gpt-5-mini")),
            api_version=str(cfg.get("api_version", "2025-04-01-preview")),
        )
    raise ValueError(f"Unknown llm provider: {provider}")


def _is_reasoning_chat_model(deployment: str) -> bool:
    name = deployment.lower()
    return name.startswith("gpt-5") or name.startswith("o1") or name.startswith("o3")
