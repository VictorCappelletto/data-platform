"""Agent Book agent — wire connectors, LangGraph order, book tools."""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any, Literal, TypedDict

from agent.router import RouteDecision, bind_followup_query, is_book_tool, route_message
from connectors.llm import EchoLlm, build_llm, resolve_llm_provider
from connectors.search import build_search, resolve_search_provider
from dataplatform.lake import Layer
from dataplatform.process_base import ProjectProcessBase
from entities.issue import KnowledgeChunk
from entities.prompts import catalog
from knowledge.retrieve import KnowledgeRetriever
from usecases.admin import NoteAdmin, PreferenceAdmin
from usecases.book import UNCOVERED, BookTools
from usecases.results import AgentTrace, as_payload, merge_trace

__all__ = ["AgentBook", "UNCOVERED", "build_agent_book_graph", "invoke_agent_book"]

AgentBookTask = Literal["ask", "note", "example", "quote", "chat", "feedback"]


class AgentBookState(TypedDict, total=False):
    task: AgentBookTask
    query: str
    search_query: str
    hits: list[KnowledgeChunk]
    result: dict[str, Any]
    positive: bool
    routed: str
    followup: bool
    steps: Annotated[list[str], operator.add]


class AgentBook(ProjectProcessBase):
    def __init__(self, environment: str | None = None) -> None:
        super().__init__("agent", "agent_book", environment)
        self.retriever = KnowledgeRetriever(environment)
        self.search = build_search(
            resolve_search_provider(self.product_config),
            retriever=self.retriever,
            cfg=self.product_config,
        )
        self.llm_provider = resolve_llm_provider(self.product_config)
        self.llm = build_llm(self.llm_provider, self.product_config)
        self.prompts = catalog()
        self._graph = None
        notes = NoteAdmin(self.loader.config_dir / "agent" / "templates")
        domain = self.product_config["domain"]
        preferences = PreferenceAdmin(
            self.io,
            profile_path=self.paths.table_path(
                Layer.GOLD, domain, str(self.product_config.get("profile_table", "profile"))
            ),
            session_path=self.paths.table_path(
                Layer.GOLD, domain, str(self.product_config.get("session_table", "session"))
            ),
            trace_path=self.paths.table_path(
                Layer.GOLD, domain, str(self.product_config.get("trace_table", "trace"))
            ),
        )
        self.book = BookTools(
            llm=self.llm,
            notes=notes,
            preferences=preferences,
            io=self.io,
            notes_path=self.paths.table_path(Layer.GOLD, domain, self.product_config["table"]),
            echo=isinstance(self.llm, EchoLlm),
            prompts=self.prompts,
        )

    def route_message(self, message: str) -> RouteDecision:
        last = str(self.book.preferences.last_turn().get("query") or "")
        return route_message(self.llm, message, last_query=last)

    def bind_followup(self, query: str) -> tuple[str, bool]:
        last = self.book.preferences.last_turn()
        return bind_followup_query(query, str(last.get("query") or ""))

    def expand_query(self, query: str) -> str:
        if isinstance(self.llm, EchoLlm):
            return query
        raw = self.llm.complete(
            system=self.prompts.body("expand"),
            user=f"User query: {query}",
        )
        expanded = (raw or "").strip().splitlines()[0].strip().strip("\"'")
        return expanded[:500] if expanded else query

    def retrieve(self, query: str) -> list:
        top_k = int(self.product_config.get("top_k", 4))
        return self.search.search(query, top_k=top_k)

    def graph(self):
        if self._graph is not None:
            return self._graph
        from langgraph.graph import END, START, StateGraph

        builder = StateGraph(AgentBookState)
        builder.add_node("route", self._node_route)
        builder.add_node("feedback", self._node_feedback)
        builder.add_node("expand", self._node_expand)
        builder.add_node("retrieve", self._node_retrieve)
        builder.add_node("ask", self._node_ask)
        builder.add_node("note", self._node_note)
        builder.add_node("example", self._node_example)
        builder.add_node("quote", self._node_quote)
        builder.add_node("uncovered", self._node_uncovered)
        builder.add_conditional_edges(
            START,
            _entry,
            {"route": "route", "expand": "expand", "feedback": "feedback"},
        )
        builder.add_conditional_edges(
            "route",
            _after_route,
            {"expand": "expand", "feedback": "feedback"},
        )
        builder.add_edge("expand", "retrieve")
        builder.add_conditional_edges(
            "retrieve",
            _after_retrieve,
            {
                "ask": "ask",
                "note": "note",
                "example": "example",
                "quote": "quote",
                "uncovered": "uncovered",
            },
        )
        builder.add_edge("ask", END)
        builder.add_edge("note", END)
        builder.add_edge("example", END)
        builder.add_edge("quote", END)
        builder.add_edge("uncovered", END)
        builder.add_edge("feedback", END)
        self._graph = builder.compile()
        return self._graph

    def invoke(
        self,
        *,
        task: AgentBookTask,
        query: str,
        positive: bool = True,
    ) -> dict[str, Any]:
        reset = getattr(self.llm, "reset_usage", None)
        if callable(reset):
            reset()
        started = time.perf_counter()
        state = self.graph().invoke(
            {
                "task": task,
                "query": query,
                "hits": [],
                "steps": [],
                "positive": positive,
            }
        )
        payload = as_payload(state.get("result") or {})
        hits = list(state.get("hits") or [])
        prompt_id = str(payload.get("prompt_id") or "")
        prompt_sha = str(payload.get("prompt_sha") or "")
        trace = AgentTrace(
            steps=list(state.get("steps") or []),
            search_query=str(state.get("search_query") or state.get("query") or ""),
            chunk_ids=[hit.id for hit in hits],
            followup=bool(state.get("followup")),
            routed=state.get("routed"),
            prompt_id=prompt_id,
            prompt_sha=prompt_sha,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            tokens_in=getattr(self.llm, "tokens_in", None),
            tokens_out=getattr(self.llm, "tokens_out", None),
        )
        result = merge_trace(payload, trace)
        self.book.preferences.remember_trace(trace.as_dict())
        return result

    def _node_route(self, state: AgentBookState) -> dict[str, Any]:
        decision = self.route_message(state["query"])
        updates: dict[str, Any] = {
            "task": decision.tool,
            "query": decision.query or state["query"],
            "routed": decision.tool,
            "steps": ["route"],
        }
        if decision.feedback_positive and decision.tool != "feedback":
            self.book.feedback(comment=state["query"], positive=True)
        return updates

    def _node_expand(self, state: AgentBookState) -> dict[str, Any]:
        query, followed = self.bind_followup(state["query"])
        return {
            "query": query,
            "search_query": self.expand_query(query),
            "followup": followed,
            "steps": ["expand"],
        }

    def _node_retrieve(self, state: AgentBookState) -> dict[str, Any]:
        query = state.get("search_query") or state["query"]
        return {"hits": self.retrieve(query), "steps": ["retrieve"]}

    def _node_ask(self, state: AgentBookState) -> dict[str, Any]:
        return {
            "result": as_payload(self.book.ask(state["query"], state.get("hits") or [])),
            "steps": ["ask"],
        }

    def _node_note(self, state: AgentBookState) -> dict[str, Any]:
        return {
            "result": as_payload(self.book.note(state["query"], state.get("hits") or [])),
            "steps": ["note"],
        }

    def _node_example(self, state: AgentBookState) -> dict[str, Any]:
        return {
            "result": as_payload(
                self.book.example(state["query"], state.get("hits") or [])
            ),
            "steps": ["example"],
        }

    def _node_quote(self, state: AgentBookState) -> dict[str, Any]:
        return {
            "result": as_payload(self.book.quote(state["query"], state.get("hits") or [])),
            "steps": ["quote"],
        }

    def _node_feedback(self, state: AgentBookState) -> dict[str, Any]:
        return {
            "result": as_payload(
                self.book.feedback(
                    comment=state.get("query") or "",
                    positive=state.get("positive", True),
                )
            ),
            "steps": ["feedback"],
        }

    def _node_uncovered(self, state: AgentBookState) -> dict[str, Any]:
        return {
            "result": as_payload(
                self.book.uncovered(state.get("task") or "ask", state["query"])
            ),
            "steps": ["uncovered"],
        }


def build_agent_book_graph(agent: AgentBook):
    return agent.graph()


def invoke_agent_book(
    *,
    task: AgentBookTask,
    query: str,
    environment: str | None = None,
    positive: bool = True,
) -> dict[str, Any]:
    return AgentBook(environment).invoke(task=task, query=query, positive=positive)


def _entry(state: AgentBookState) -> str:
    if state.get("task") == "chat":
        return "route"
    if state.get("task") == "feedback":
        return "feedback"
    return "expand"


def _after_route(state: AgentBookState) -> str:
    if state.get("task") == "feedback":
        return "feedback"
    return "expand"


def _after_retrieve(state: AgentBookState) -> str:
    if not state.get("hits"):
        return "uncovered"
    task = state.get("task") or "ask"
    if is_book_tool(task):
        return task
    return "ask"


def _run(
    task: str,
    query: str,
    *,
    environment: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return invoke_agent_book(task=task, query=query, environment=environment, **extra)


def run_ask(*, question: str, environment: str | None = None) -> dict[str, Any]:
    return _run("ask", question, environment=environment)


def run_note(*, topic: str, environment: str | None = None) -> dict[str, Any]:
    return _run("note", topic, environment=environment)


def run_example(*, topic: str, environment: str | None = None) -> dict[str, Any]:
    return _run("example", topic, environment=environment)


def run_quote(*, query: str, environment: str | None = None) -> dict[str, Any]:
    return _run("quote", query, environment=environment)


def run_chat(*, message: str, environment: str | None = None) -> dict[str, Any]:
    return _run("chat", message, environment=environment)


def run_feedback(
    *, comment: str = "", positive: bool = True, environment: str | None = None
) -> dict[str, Any]:
    return _run("feedback", comment, environment=environment, positive=positive)
