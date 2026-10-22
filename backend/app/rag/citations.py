from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from ..models import Chunk, Document
from ..utils.citation_lines import build_citation_excerpts


def citation_chunk_ids(sources: Iterable[dict[str, Any]]) -> set[UUID]:
    identifiers: set[UUID] = set()
    for source in sources:
        try:
            identifiers.add(UUID(str(source.get("chunk_id"))))
        except (ValueError, TypeError, AttributeError):
            continue
    return identifiers


async def load_citation_excerpts(
    chunk_ids: Iterable[UUID], session: AsyncSession,
) -> dict[UUID, dict[str, Any]]:
    identifiers = set(chunk_ids)
    if not identifiers:
        return {}
    documents = {document.id: document for document in (await session.execute(
        select(Document).where(Document.id.in_(
            select(Chunk.document_id).where(Chunk.id.in_(identifiers))
        ))
    )).scalars().all()}
    if not documents:
        return {}
    chunks = (await session.execute(
        select(Chunk)
        .options(load_only(Chunk.id, Chunk.document_id, Chunk.chunk_index, Chunk.content))
        .where(Chunk.document_id.in_(documents)).order_by(Chunk.chunk_index.asc(), Chunk.id.asc())
    )).scalars().all()
    grouped: dict[UUID, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.document_id].append(chunk)
    result: dict[UUID, dict[str, Any]] = {}
    for document_id, document in documents.items():
        excerpts = build_citation_excerpts(document.content, grouped[document_id], identifiers)
        for chunk_id, excerpt in excerpts.items():
            if chunk_id in identifiers:
                result[chunk_id] = {
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "source": document.source or document.title,
                    **excerpt,
                }
    return result


def enrich_citation_sources(
    sources: list[dict[str, Any]], excerpts: dict[UUID, dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for source in sources:
        item = dict(source)
        try:
            excerpt = excerpts.get(UUID(str(source.get("chunk_id"))))
        except (ValueError, TypeError, AttributeError):
            excerpt = None
        if excerpt is not None:
            item.update({key: value for key, value in excerpt.items() if key != "content"})
        else:
            item.update(start_line=None, end_line=None, line_number_kind=None)
        enriched.append(item)
    return enriched
