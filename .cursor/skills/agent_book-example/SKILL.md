---
name: agent_book-example
description: After Agent Book answers a book question, offer a practical day-to-day example. If the user accepts in any wording, call agent_book_example or agent_book_chat. Use for Fundamentos de Engenharia de Dados, agent_book_ask, agent_book_chat, or Agent Book Q&A.
---

# Agent Book — chat e exemplo

Prefer `agent_book_chat` when the user does not name a method. It interprets free-form replies (not only sim/não). Explicit tools still work: `agent_book_ask`, `agent_book_quote`, `agent_book_note`, `agent_book_example`.

After a covered answer, you may offer a day-to-day example. If they accept in any wording (mostra na prática, um caso real, tipo no trabalho), call `agent_book_example` with the same topic.

If they want the book text itself (trecho, página, cita o original), call `agent_book_quote`.

If they praise the answer (gostei, bem objetiva, continua assim), call `agent_book_feedback` with `positive=true` and their comment. Do not wait for a thumbs-up widget.

Follow-ups ("não entendi", "explica melhor", "e no Spark?", "o terceiro") go to `agent_book_chat` or `agent_book_ask` with the user's words. The graph prefixes the last topic from session. Do not drop the previous subject.
