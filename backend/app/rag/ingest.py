from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..llm.qwen import get_qwen_client
from ..models import Chunk, Document
from ..schemas import DocumentInput
from ..utils.chunking import chunk_text


async def ingest_documents(
    documents: list[DocumentInput],
    session: AsyncSession,
) -> tuple[int, int]:
    settings = get_settings()
    qwen = get_qwen_client()

    total_docs = 0
    total_chunks = 0

    for doc in documents:
        doc_id = uuid4()
        doc_row = Document(id=doc_id, title=doc.title, source=doc.source)
        session.add(doc_row)

        chunks = chunk_text(doc.text, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            continue

        embeddings = await qwen.embed_texts(chunks)
        pair_count = min(len(chunks), len(embeddings))

        for index in range(pair_count):
            session.add(
                Chunk(
                    document_id=doc_id,
                    chunk_index=index,
                    content=chunks[index],
                    embedding=embeddings[index],
                )
            )

        total_docs += 1
        total_chunks += pair_count

    await session.commit()
    return total_docs, total_chunks
