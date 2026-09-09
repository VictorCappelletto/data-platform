"""Page-aware text chunking.

Lever: split on form-feed page breaks first, then pack paragraphs inside a page.
Chunks never cross a page boundary.
"""

from __future__ import annotations

from typing import Any

FORM_FEED = "\x0c"


def split_pages(text: str) -> list[tuple[int, str]]:
    raw_pages = text.split(FORM_FEED)
    pages: list[tuple[int, str]] = []
    for index, raw in enumerate(raw_pages, start=1):
        body = _normalize(raw)
        if body:
            pages.append((index, body))
    return pages or [(1, _normalize(text))]


def chunk_pages(
    pages: list[tuple[int, str]],
    *,
    source_id: str,
    source_path: str,
    max_chars: int = 1200,
    overlap: int = 180,
    min_chars: int = 80,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    serial = 0
    for page_num, body in pages:
        if len(body) < min_chars:
            continue
        title = _page_title(body)
        for piece in _pack_paragraphs(body, max_chars=max_chars, overlap=overlap):
            if len(piece) < min_chars:
                continue
            serial += 1
            chunks.append(
                {
                    "id": f"{source_id}-p{page_num}-{serial}",
                    "source_id": source_id,
                    "source_path": source_path,
                    "title": title,
                    "page": page_num,
                    "text": piece,
                }
            )
    return chunks


def _normalize(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip()


def _page_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return ""


def _pack_paragraphs(text: str, *, max_chars: int, overlap: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        return _window(text, max_chars=max_chars, overlap=overlap)
    packed: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = para if not buf else f"{buf}\n\n{para}"
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if buf:
            packed.append(buf)
        if len(para) <= max_chars:
            buf = para
        else:
            packed.extend(_window(para, max_chars=max_chars, overlap=overlap))
            buf = ""
    if buf:
        packed.append(buf)
    return packed


def _window(text: str, *, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    step = max(max_chars - overlap, 1)
    pieces: list[str] = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + max_chars])
        start += step
    return pieces
