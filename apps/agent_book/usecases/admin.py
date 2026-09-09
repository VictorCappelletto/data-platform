"""Gold persistence — notes (YAML template) and preference profile."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import yaml

from entities.issue import KnowledgeChunk, NoteDraft
from entities.system import FEEDBACK_PROMPT
from usecases.payload import as_object

_MAX_LIKES = 8


class _Io(Protocol):
    def read_json(self, path: str) -> Any: ...

    def write_json(self, path: str, payload: Any) -> str: ...


class _Llm(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


class NoteAdmin:
    def __init__(self, templates_dir: Path) -> None:
        self.templates_dir = templates_dir

    def build(
        self,
        topic: str,
        hits: list[KnowledgeChunk],
        *,
        synthesis: dict[str, str] | None = None,
    ) -> NoteDraft:
        pages = sorted({hit.page for hit in hits if hit.page})
        chunk_ids = [hit.id for hit in hits]
        claim, evidence = _claim_and_evidence(topic, hits, synthesis)
        return NoteDraft(
            topic=topic,
            claim=claim,
            evidence=evidence,
            pages=pages,
            chunk_ids=chunk_ids,
        )

    def render(self, draft: NoteDraft) -> dict:
        path = self.templates_dir / "note.yml"
        with path.open(encoding="utf-8") as fh:
            template = yaml.safe_load(fh) or {}
        pages = ", ".join(str(page) for page in draft.pages) or "n/a"
        values = {
            "claim": draft.claim,
            "evidence": draft.evidence,
            "pages": pages,
            "topic": draft.topic,
        }
        return {key: _fill(str(value), values) for key, value in template.items()}

    def persist(self, io: _Io, path: str, draft: NoteDraft) -> dict[str, Any]:
        try:
            existing = io.read_json(path)
        except FileNotFoundError:
            existing = []
        if not isinstance(existing, list):
            existing = []
        note_key = f"NOTE-{len(existing) + 1:04d}"
        record = draft.to_record(note_key)
        record["template"] = self.render(draft)
        existing.append(record)
        written = io.write_json(path, existing)
        return {
            "topic": draft.topic,
            "covered": True,
            "note_key": note_key,
            "uri": written,
            "pages": record["pages"],
            "claim": record["claim"],
            "evidence": record["evidence"],
        }


class PreferenceAdmin:
    def __init__(
        self,
        io: _Io,
        *,
        profile_path: str,
        session_path: str,
        trace_path: str = "",
    ) -> None:
        self.io = io
        self.profile_path = profile_path
        self.session_path = session_path
        self.trace_path = trace_path

    def load(self) -> dict[str, Any]:
        profile = default_profile()
        profile.update(_read_object(self.io, self.profile_path))
        likes = profile.get("likes")
        if not isinstance(likes, list):
            profile["likes"] = []
        return profile

    def remember_turn(self, turn: dict[str, Any]) -> None:
        payload = {
            "task": turn.get("task"),
            "query": turn.get("query"),
            "snippet": str(turn.get("snippet") or "")[:800],
            "at": _now(),
        }
        self.io.write_json(self.session_path, [payload])

    def last_turn(self) -> dict[str, Any]:
        return _read_object(self.io, self.session_path)

    def remember_trace(self, trace: dict[str, Any]) -> None:
        if not self.trace_path:
            return
        self.io.write_json(self.trace_path, [{**trace, "at": _now()}])

    def record_positive(
        self,
        *,
        comment: str,
        llm: _Llm | None = None,
        echo: bool = True,
    ) -> dict[str, Any]:
        profile = self.load()
        profile["positive_count"] = int(profile.get("positive_count") or 0) + 1
        profile["updated_at"] = _now()
        extracted = None if echo else _extract_style(llm, comment, self.last_turn())
        if extracted:
            if extracted.get("length") in {"short", "medium", "long"}:
                profile["length"] = extracted["length"]
            if extracted.get("tone"):
                profile["tone"] = extracted["tone"]
            like = str(extracted.get("like") or "").strip()
            if like:
                _push_like(profile, like)
        elif comment.strip():
            _push_like(profile, comment.strip()[:160])
        self.io.write_json(self.profile_path, [profile])
        return profile

    def record(
        self,
        *,
        comment: str = "",
        positive: bool = True,
        llm: _Llm | None = None,
        echo: bool = True,
    ) -> dict[str, Any]:
        if not positive:
            return {
                "recorded": False,
                "reason": "only_positive",
                "profile": self.load(),
            }
        profile = self.record_positive(comment=comment, llm=llm, echo=echo)
        return {"recorded": True, "positive": True, "profile": profile}

    def style_block(self) -> str:
        profile = self.load()
        if int(profile.get("positive_count") or 0) <= 0:
            return ""
        lines = ["User style (from positive feedback — follow this):"]
        lines.append(f"- length: {profile.get('length') or 'medium'}")
        if profile.get("tone"):
            lines.append(f"- tone: {profile['tone']}")
        if profile.get("language"):
            lines.append(f"- language: {profile['language']}")
        if profile.get("cite_pages"):
            lines.append("- always cite pages")
        for like in list(profile.get("likes") or [])[-5:]:
            text = str(like).strip()
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines)


def parse_note_payload(text: str) -> dict[str, str] | None:
    payload = as_object(text)
    if payload is None:
        return None
    claim = str(payload.get("claim") or "").strip()
    evidence = payload.get("evidence")
    if isinstance(evidence, list):
        evidence = "\n".join(str(item).strip() for item in evidence if str(item).strip())
    else:
        evidence = str(evidence or "").strip()
    if not claim:
        return None
    return {"claim": claim, "evidence": evidence}


def default_profile() -> dict[str, Any]:
    return {
        "length": "medium",
        "tone": "practical",
        "cite_pages": True,
        "language": "",
        "likes": [],
        "positive_count": 0,
        "updated_at": "",
    }


def _claim_and_evidence(
    topic: str,
    hits: list[KnowledgeChunk],
    synthesis: dict[str, str] | None,
) -> tuple[str, str]:
    fallback_evidence = _evidence_from_hits(hits)
    if synthesis and synthesis.get("claim"):
        claim = synthesis["claim"].strip()
        evidence = (synthesis.get("evidence") or "").strip() or fallback_evidence
        return claim, evidence
    if not hits:
        return topic, ""
    snippet = hits[0].text.replace("\n", " ").strip()
    if len(snippet) > 220:
        snippet = snippet[:220].rstrip() + "…"
    return f"{topic}: {snippet}", fallback_evidence


def _evidence_from_hits(hits: list[KnowledgeChunk]) -> str:
    return "\n\n".join(f"[p.{hit.page}] {hit.text}" for hit in hits)


def _fill(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def _push_like(profile: dict[str, Any], like: str) -> None:
    likes = [str(item) for item in profile.get("likes") or [] if str(item).strip()]
    if like not in likes:
        likes.append(like)
    profile["likes"] = likes[-_MAX_LIKES:]


def _extract_style(
    llm: _Llm | None, comment: str, last_turn: dict[str, Any]
) -> dict[str, str] | None:
    if llm is None:
        return None
    raw = llm.complete(
        system=FEEDBACK_PROMPT,
        user=(
            f"User comment: {comment}\n\n"
            f"Last turn: {json.dumps(last_turn, ensure_ascii=False)[:1200]}\n\n"
            'Return JSON only: {"length": "...", "tone": "...", "like": "..."}'
        ),
    )
    payload = as_object(raw)
    if payload is None:
        return None
    return {
        "length": str(payload.get("length") or "").strip().lower(),
        "tone": str(payload.get("tone") or "").strip().lower(),
        "like": str(payload.get("like") or "").strip(),
    }


def _read_object(io: _Io, path: str) -> dict[str, Any]:
    try:
        payload = io.read_json(path)
    except FileNotFoundError:
        return {}
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return payload[0]
    return payload if isinstance(payload, dict) else {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
