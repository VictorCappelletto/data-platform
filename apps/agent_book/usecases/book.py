"""Book tools — ask, note, example, quote, feedback from retrieved hits."""

from __future__ import annotations

from typing import Any, Protocol

from entities.issue import KnowledgeChunk
from entities.prompts import PromptCatalog, catalog
from knowledge.retrieve import format_hits
from usecases.admin import NoteAdmin, PreferenceAdmin, parse_note_payload
from usecases.results import (
    AskResult,
    Citation,
    ExampleResult,
    FeedbackResult,
    NoteResult,
    QuoteResult,
    ToolResult,
    citations_of,
)

UNCOVERED = "O livro não cobre este assunto nos trechos indexados."


class _Llm(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


class _Io(Protocol):
    def read_json(self, path: str) -> Any: ...

    def write_json(self, path: str, payload: Any) -> str: ...


class BookTools:
    def __init__(
        self,
        *,
        llm: _Llm,
        notes: NoteAdmin,
        preferences: PreferenceAdmin,
        io: _Io,
        notes_path: str,
        echo: bool,
        prompts: PromptCatalog | None = None,
    ) -> None:
        self.llm = llm
        self.notes = notes
        self.preferences = preferences
        self.io = io
        self.notes_path = notes_path
        self.echo = echo
        self.prompts = prompts or catalog()

    def ask(self, question: str, hits: list[KnowledgeChunk]) -> AskResult:
        missed = self.uncovered("ask", question)
        if not hits and isinstance(missed, AskResult):
            return missed
        prompt = self.prompts.get("ask")
        if self.echo:
            answer = _echo_answer(question, hits)
        else:
            answer = self.llm.complete(
                system=self._system(prompt.body),
                user=(
                    f"Original question: {question}\n\nExcerpts:\n{format_hits(hits)}\n\n"
                    "Answer the original question using only the excerpts. "
                    "If wording differs from the book, map the intent to excerpt terms "
                    "and cite pages. Do not refuse only because of vocabulary mismatch."
                ),
            )
        self._remember("ask", question, answer)
        return AskResult(
            question=question,
            answer=answer,
            citations=citations_of(hits),
            covered=True,
            offer_example=True,
            prompt_id=prompt.id,
            prompt_sha=prompt.sha,
        )

    def note(self, topic: str, hits: list[KnowledgeChunk]) -> NoteResult:
        missed = self.uncovered("note", topic)
        if not hits and isinstance(missed, NoteResult):
            return missed
        prompt = self.prompts.get("note")
        draft = self.notes.build(topic, hits, synthesis=self._note_synthesis(topic, hits))
        raw = self.notes.persist(self.io, self.notes_path, draft)
        self._remember("note", topic, str(raw.get("claim") or ""))
        return NoteResult(
            topic=topic,
            covered=True,
            note_key=str(raw["note_key"]),
            uri=str(raw.get("uri") or ""),
            pages=list(raw.get("pages") or []),
            claim=str(raw.get("claim") or ""),
            evidence=str(raw.get("evidence") or ""),
            prompt_id=prompt.id,
            prompt_sha=prompt.sha,
        )

    def example(self, topic: str, hits: list[KnowledgeChunk]) -> ExampleResult:
        missed = self.uncovered("example", topic)
        if not hits and isinstance(missed, ExampleResult):
            return missed
        prompt = self.prompts.get("example")
        if self.echo:
            scenario = _echo_example(topic, hits)
        else:
            scenario = self.llm.complete(
                system=self._system(prompt.body),
                user=(
                    f"Topic: {topic}\n\nExcerpts:\n{format_hits(hits)}\n\n"
                    "Write the practical day-to-day scenario. Cite pages."
                ),
            )
        self._remember("example", topic, scenario)
        return ExampleResult(
            topic=topic,
            scenario=scenario,
            citations=citations_of(hits),
            covered=True,
            prompt_id=prompt.id,
            prompt_sha=prompt.sha,
        )

    def quote(self, query: str, hits: list[KnowledgeChunk]) -> QuoteResult:
        missed = self.uncovered("quote", query)
        if not hits and isinstance(missed, QuoteResult):
            return missed
        prompt = self.prompts.get("quote")
        passages = [
            {
                "chunk_id": hit.id,
                "page": hit.page,
                "title": hit.title,
                "text": hit.text,
            }
            for hit in hits
        ]
        snippet = passages[0]["text"] if passages else ""
        self._remember("quote", query, snippet)
        return QuoteResult(
            query=query,
            passages=passages,
            citations=citations_of(hits),
            covered=True,
            prompt_id=prompt.id,
            prompt_sha=prompt.sha,
        )

    def feedback(self, *, comment: str = "", positive: bool = True) -> FeedbackResult:
        prompt = self.prompts.get("feedback")
        raw = self.preferences.record(
            comment=comment,
            positive=positive,
            llm=self.llm,
            echo=self.echo,
        )
        return FeedbackResult(
            recorded=bool(raw.get("recorded")),
            positive=bool(raw.get("positive", True)),
            reason=str(raw.get("reason") or ""),
            profile=dict(raw.get("profile") or {}),
            prompt_id=prompt.id,
            prompt_sha=prompt.sha,
        )

    def uncovered(self, task: str, query: str) -> ToolResult:
        name = task if task in {"ask", "note", "example", "quote"} else "ask"
        prompt = self.prompts.get(name)
        empty: list[Citation] = []
        if task == "note":
            return NoteResult(
                topic=query,
                covered=False,
                answer=UNCOVERED,
                prompt_id=prompt.id,
                prompt_sha=prompt.sha,
            )
        if task == "example":
            return ExampleResult(
                topic=query,
                scenario=UNCOVERED,
                citations=empty,
                covered=False,
                prompt_id=prompt.id,
                prompt_sha=prompt.sha,
            )
        if task == "quote":
            return QuoteResult(
                query=query,
                passages=[],
                citations=empty,
                covered=False,
                prompt_id=prompt.id,
                prompt_sha=prompt.sha,
            )
        return AskResult(
            question=query,
            answer=UNCOVERED,
            citations=empty,
            covered=False,
            offer_example=False,
            prompt_id=prompt.id,
            prompt_sha=prompt.sha,
        )

    def _note_synthesis(
        self, topic: str, hits: list[KnowledgeChunk]
    ) -> dict[str, str] | None:
        if self.echo:
            return None
        prompt = self.prompts.get("note")
        raw = self.llm.complete(
            system=self._system(prompt.body),
            user=(
                f"Topic: {topic}\n\nExcerpts:\n{format_hits(hits)}\n\n"
                'Return JSON only: {"claim": "...", "evidence": "..."}'
            ),
        )
        return parse_note_payload(raw)

    def _system(self, prompt: str) -> str:
        style = self.preferences.style_block()
        if not style:
            return prompt
        return f"{prompt}\n\n{style}"

    def _remember(self, task: str, query: str, snippet: str) -> None:
        self.preferences.remember_turn({"task": task, "query": query, "snippet": snippet})


def _echo_answer(question: str, hits: list[KnowledgeChunk]) -> str:
    lines = [f"Pergunta: {question}", "", "Segundo o livro:"]
    for hit in hits:
        snippet = hit.text.replace("\n", " ").strip()
        if len(snippet) > 360:
            snippet = snippet[:360].rstrip() + "…"
        lines.append(f"- p.{hit.page} [{hit.id}]: {snippet}")
    return "\n".join(lines)


def _echo_example(topic: str, hits: list[KnowledgeChunk]) -> str:
    lines = [
        f"Contexto: {topic} no dia a dia de engenharia de dados.",
        "",
        "Situação: um time aplica o conceito do livro neste cenário:",
    ]
    for hit in hits:
        snippet = hit.text.replace("\n", " ").strip()
        if len(snippet) > 280:
            snippet = snippet[:280].rstrip() + "…"
        lines.append(f"- p.{hit.page}: {snippet}")
    return "\n".join(lines)
