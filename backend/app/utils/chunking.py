from __future__ import annotations

import re


def chunk_document(
    text: str,
    source: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[str]:
    if not text or not text.strip():
        return []
    if chunk_overlap >= chunk_size:
        chunk_overlap = max(0, chunk_size - 1)

    if source and source.lower().endswith((".md", ".markdown")):
        return _chunk_markdown(text, chunk_size, chunk_overlap)
    return _chunk_plain(text, chunk_size, chunk_overlap)


def _chunk_markdown(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    sections = _split_by_heading(text)
    chunks: list[str] = []

    for heading, body in sections:
        full = f"{heading}\n\n{body}".strip() if heading else body.strip()
        if not full:
            continue
        if len(full) <= chunk_size:
            chunks.append(full)
            continue
        for piece in _oversize_split(body, chunk_size, chunk_overlap, heading):
            chunks.append(piece)

    return _merge_sections(chunks, chunk_size, chunk_overlap)


def _chunk_plain(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []

    for para in paragraphs:
        if len(para) <= chunk_size:
            chunks.append(para)
        else:
            chunks.extend(_oversize_split(para, chunk_size, chunk_overlap))

    return _merge_sections(chunks, chunk_size, chunk_overlap)


def _merge_sections(sections: list[str], chunk_size: int, chunk_overlap: int) -> list[str]:
    if not sections:
        return []

    merged: list[str] = []
    current = sections[0]

    for section in sections[1:]:
        if len(current) + 1 + len(section) > chunk_size:
            merged.append(current)
            current = section
        else:
            current = f"{current}\n\n{section}"

    merged.append(current)
    return merged


def _oversize_split(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    heading: str | None = None,
) -> list[str]:
    paragraphs = _split_paragraphs(text)

    if len(paragraphs) > 1:
        chunks: list[str] = []
        for para in paragraphs:
            prefix = f"{heading}\n\n" if heading else ""
            full = prefix + para.strip()
            if len(full) <= chunk_size:
                chunks.append(full)
            else:
                chunks.extend(
                    _oversize_split(para, chunk_size, chunk_overlap, heading=None)
                )
        return chunks

    sentences = _split_sentences(text)
    if len(sentences) > 1:
        chunks = []
        for sentence in sentences:
            prefix = f"{heading}\n\n" if heading else ""
            full = prefix + sentence
            if len(full) <= chunk_size:
                chunks.append(full)
            else:
                chunks.extend(_char_fallback(full, chunk_size, chunk_overlap))
        return chunks

    prefix = f"{heading}\n\n" if heading else ""
    full = prefix + text.strip()
    return _char_fallback(full, chunk_size, chunk_overlap)


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _split_by_heading(text: str) -> list[tuple[str | None, str]]:
    lines = text.split("\n")
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            current_lines.append(line)
            continue

        if not in_code_block:
            match = _HEADING_RE.match(stripped)
            if match:
                preamble = "\n".join(current_lines).strip()
                if preamble:
                    sections.append((current_heading, preamble))
                current_heading = stripped
                current_lines = []
                continue

        current_lines.append(line)

    remainder = "\n".join(current_lines).strip()
    if remainder:
        sections.append((current_heading, remainder))

    if not sections:
        cleaned = text.strip()
        if cleaned:
            sections.append((None, cleaned))

    return sections


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]


_SENTENCE_RE = re.compile(r"(?<=[。！？.!?])\s*")


def _split_sentences(text: str) -> list[str]:
    sentences = _SENTENCE_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def _char_fallback(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(text[start:end])
        if end == length:
            break
        start = end - chunk_overlap
    return chunks
