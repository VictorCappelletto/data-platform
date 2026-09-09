"""Golden eval over the test fixture (or a book ingest already in the lake)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from agent.agent_book import invoke_agent_book
from knowledge.ingest import run_ingest
from usecases.book import UNCOVERED

GOLDEN_PATH = Path(__file__).with_name("golden.yml")
REPO_ROOT = Path(__file__).resolve().parents[2]


def azure_ready() -> bool:
    load_dotenv(REPO_ROOT / ".env")
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"))


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    raw = yaml.safe_load((path or GOLDEN_PATH).read_text(encoding="utf-8")) or {}
    return list(raw.get("cases") or [])


def run_golden(*, ingest: bool = True, require_llm: bool = False) -> list[dict[str, Any]]:
    if ingest:
        run_ingest()
    report = []
    for case in load_cases():
        _clear_session()
        result = invoke_agent_book(task=case["task"], query=case["query"])
        report.append(evaluate_case(case, result, require_llm=require_llm))
    return report


def _clear_session() -> None:
    from agent.agent_book import AgentBook

    agent = AgentBook()
    agent.io.write_json(agent.book.preferences.session_path, [])


def evaluate_case(
    case: dict[str, Any], result: dict[str, Any], *, require_llm: bool = False
) -> dict[str, Any]:
    errors: list[str] = []
    expected_covered = bool(case.get("covered"))
    if bool(result.get("covered")) != expected_covered:
        errors.append(f"covered={result.get('covered')} expected {expected_covered}")
    expected_pages = {int(page) for page in case.get("pages") or []}
    if expected_pages:
        got = {int(item["page"]) for item in result.get("citations") or []}
        missing = expected_pages - got
        if missing:
            errors.append(f"missing pages {sorted(missing)} in {sorted(got)}")
    body = _body(case.get("task") or "ask", result)
    if expected_covered:
        terms = [str(term).lower() for term in case.get("terms") or []]
        lowered = body.lower()
        if terms and not any(term in lowered for term in terms):
            errors.append(f"missing terms {terms} in answer")
        if case.get("cite_pages") and "p." not in lowered:
            errors.append("answer missing page citation (p.N)")
        if require_llm and (case.get("task") or "ask") == "ask":
            if body.lstrip().startswith("Pergunta:"):
                errors.append("echo template — LLM did not synthesize")
            if body.strip() == UNCOVERED:
                errors.append("LLM refused a covered topic")
    elif (case.get("task") or "ask") == "ask" and body.strip() != UNCOVERED:
        errors.append("uncovered topic must use the uncovered string")
    return {
        "id": case.get("id"),
        "ok": not errors,
        "errors": errors,
        "prompt_id": result.get("prompt_id"),
        "elapsed_ms": (result.get("trace") or {}).get("elapsed_ms"),
        "tokens_in": (result.get("trace") or {}).get("tokens_in"),
    }


def _body(task: str, result: dict[str, Any]) -> str:
    if task == "example":
        return str(result.get("scenario") or "")
    if task == "note":
        return f"{result.get('claim') or ''} {result.get('evidence') or ''}"
    if task == "quote":
        return " ".join(str(item.get("text") or "") for item in result.get("passages") or [])
    return str(result.get("answer") or "")
