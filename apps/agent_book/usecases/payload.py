"""Parse JSON from LLM text (fences and trailing prose)."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def load_llm_json(text: str) -> Any:
    raw = _strip_fence(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = _OBJECT.search(raw)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def as_object(text: str) -> dict[str, Any] | None:
    payload = load_llm_json(text)
    if not isinstance(payload, dict):
        return None
    return {str(key).lower(): value for key, value in payload.items()}


def _strip_fence(text: str) -> str:
    raw = (text or "").strip()
    fenced = _FENCE.search(raw)
    return fenced.group(1).strip() if fenced else raw
