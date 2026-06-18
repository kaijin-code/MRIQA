from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth import get_current_user
from ...db import get_session
from ...models import Chunk, Document, User
from ...rag.ingest import ingest_documents
from ...schemas import (
    DocumentInput,
    DocumentListResponse,
    DocumentSummary,
    IngestRequest,
    IngestResponse,
)
from ...utils.extractors import extract_text, is_allowed

documents_router = APIRouter(prefix="/documents", tags=["documents"])


@documents_router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IngestResponse:
    docs, chunks = await ingest_documents(request.documents, session)
    return IngestResponse(documents=docs, chunks=chunks)


_MAX_FILE_SIZE = 20 * 1024 * 1024


@documents_router.post("/upload", response_model=IngestResponse)
async def upload(
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IngestResponse:
    documents: list[DocumentInput] = []

    for file in files:
        filename = file.filename or "unknown"
        if not is_allowed(filename):
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {filename}",
            )

        content = await file.read()
        if len(content) > _MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {filename}（最大 20MB）",
            )

        try:
            text = extract_text(content, filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail=f"文件内容为空或无法提取: {filename}",
            )

        documents.append(DocumentInput(title=filename, source=filename, text=text))

    if not documents:
        raise HTTPException(status_code=400, detail="未上传有效文件")

    docs, chunks = await ingest_documents(documents, session)
    return IngestResponse(documents=docs, chunks=chunks)


@documents_router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentListResponse:
    stmt = (
        select(
            Document,
            func.count(Chunk.id).label("chunk_count"),
        )
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()

    documents: list[DocumentSummary] = []
    for document, chunk_count in rows:
        documents.append(
            DocumentSummary(
                id=document.id,
                title=document.title,
                source=document.source,
                created_at=document.created_at,
                chunk_count=chunk_count or 0,
            )
        )

    return DocumentListResponse(documents=documents)


@documents_router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
    )
    chunks = (await session.execute(stmt)).scalars().all()

    text = "\n".join(chunk.content for chunk in chunks)
    filename = document.source or document.title or "document.txt"

    return Response(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@documents_router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    await session.delete(document)
    await session.commit()
    return Response(status_code=204)
