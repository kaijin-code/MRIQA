from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..llm.qwen import get_qwen_client
from ..models import Chunk, Document
from .citations import load_citation_excerpts


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    source: str | None
    score: float
    start_line: int | None = None
    end_line: int | None = None
    line_number_kind: str | None = None


async def retrieve_chunks(query: str, session: AsyncSession) -> list[RetrievedChunk]:
    settings = get_settings()
    if not query.strip():
        return []

    qwen = get_qwen_client()
    query_embedding = await qwen.embed_query(query)

    distance = Chunk.embedding.cosine_distance(query_embedding)
    stmt = (
        select(Chunk, Document.source, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .order_by(distance)
        .limit(settings.rag_top_k)
    )

    rows = (await session.execute(stmt)).all()
    results: list[RetrievedChunk] = []

    for chunk, source, dist_value in rows:
        score = 1.0 - float(dist_value)
        if score < settings.rag_min_similarity:
            continue
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                source=source,
                score=score,
            )
        )

    excerpts = await load_citation_excerpts((item.chunk_id for item in results), session)
    for item in results:
        excerpt = excerpts.get(item.chunk_id)
        if excerpt is not None:
            item.start_line = excerpt["start_line"]
            item.end_line = excerpt["end_line"]
            item.line_number_kind = excerpt["line_number_kind"]
    return results
