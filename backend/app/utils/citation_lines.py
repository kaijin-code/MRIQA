from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, Protocol
from uuid import UUID


class CitationChunk(Protocol):
    id: UUID
    chunk_index: int
    content: str


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _original_span(original: str, compact_start: int, compact_length: int) -> tuple[int, int]:
    """Map a compact match without allocating an integer offset for every character."""
    position = 0
    start = 0
    for offset, char in enumerate(original):
        if char.isspace():
            continue
        if position == compact_start:
            start = offset
        position += 1
        if position == compact_start + compact_length:
            return start, offset + 1
    raise ValueError("Compact excerpt is outside the original text")


def build_citation_excerpts(
    document_content: str | None,
    chunks: Iterable[CitationChunk],
    chunk_ids: set[UUID] | None = None,
) -> dict[UUID, dict[str, Any]]:
    """Use original text only when the excerpt has one unambiguous location.

    Historical indexes discarded whitespace and repeated Markdown headings.
    Their line numbers explicitly refer to reconstructed knowledge text.
    """
    original = _normalize_newlines(document_content) if document_content is not None else None
    compact_original = re.sub(r"\s+", "", original) if original is not None else ""
    result: dict[UUID, dict[str, Any]] = {}
    reconstructed_line = 1
    for chunk in sorted(chunks, key=lambda item: (item.chunk_index, str(item.id))):
        content = _normalize_newlines(chunk.content)
        if chunk_ids is None or chunk.id in chunk_ids:
            displayed_content = content.rstrip("\n")
            start_line = reconstructed_line
            kind = "reconstructed"
            compact_content = re.sub(r"\s+", "", content)
            if original is not None and compact_content:
                compact_offset = compact_original.find(compact_content)
                if compact_offset >= 0 and compact_original.find(compact_content, compact_offset + 1) < 0:
                    offset, end = _original_span(original, compact_offset, len(compact_content))
                    displayed_content = original[offset:end]
                    start_line = original.count("\n", 0, offset) + 1
                    kind = "original"
            result[chunk.id] = {
                "content": displayed_content,
                "start_line": start_line,
                "end_line": start_line + displayed_content.count("\n"),
                "line_number_kind": kind,
            }
        # Joining ordered chunks with two newlines gives stable legacy positions.
        reconstructed_line += content.count("\n") + 2
    return result
