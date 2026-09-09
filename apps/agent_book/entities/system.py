"""Prompt bodies loaded from config/agent/templates/prompts.yml."""

from entities.prompts import catalog

_catalog = catalog()

SYSTEM_PROMPT = _catalog.body("ask")
NOTE_PROMPT = _catalog.body("note")
EXAMPLE_PROMPT = _catalog.body("example")
QUERY_EXPAND_PROMPT = _catalog.body("expand")
ROUTE_PROMPT = _catalog.body("route")
FEEDBACK_PROMPT = _catalog.body("feedback")
