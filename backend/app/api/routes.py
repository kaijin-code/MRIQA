from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..db import get_session
from ..models import Conversation, Message, User
from ..orchestrator import run_orchestrator, run_orchestrator_stream
from ..rag.ingest import ingest_documents
from ..schemas import (
    ChatRequest,
    ChatResponse,
    ChunkCitation,
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationSummary,
    IngestRequest,
    IngestResponse,
    MessageItem,
    RoleResponse,
)

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(val) for key, val in value.items()}
    return value


def _make_title(message: str, max_length: int = 32) -> str:
    trimmed = " ".join(message.strip().split())
    if len(trimmed) <= max_length:
        return trimmed
    return trimmed[:max_length].rstrip() + "..."


async def _get_conversation(
    conversation_id: UUID | None,
    session: AsyncSession,
    user_id: UUID,
) -> Conversation:
    if conversation_id is None:
        conversation = Conversation(user_id=user_id)
        session.add(conversation)
        await session.flush()
        return conversation

    conversation = await session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    return conversation


async def _load_history(
    conversation_id: UUID,
    session: AsyncSession,
    limit: int = 10,
) -> list[dict[str, Any]]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    rows.reverse()

    return [{"role": row.role, "content": row.content} for row in rows]


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    request: IngestRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> IngestResponse:
    docs, chunks = await ingest_documents(request.documents, session)
    return IngestResponse(documents=docs, chunks=chunks)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ConversationListResponse:
    stmt = (
        select(
            Conversation,
            func.count(Message.id).label("message_count"),
            func.max(Message.created_at).label("last_message_at"),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()

    conversations: list[ConversationSummary] = []
    for conversation, message_count, last_message_at in rows:
        conversations.append(
            ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                created_at=conversation.created_at,
                last_message_at=last_message_at,
                message_count=message_count or 0,
            )
        )

    return ConversationListResponse(conversations=conversations)


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    conversation_id: UUID,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ConversationHistoryResponse:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    messages = (await session.execute(stmt)).scalars().all()

    items: list[MessageItem] = []
    for message in messages:
        items.append(
            MessageItem(
                id=message.id,
                role=message.role,
                content=message.content,
                sources=_json_safe(message.sources) if message.sources else None,
                created_at=message.created_at,
            )
        )

    return ConversationHistoryResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=items,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    conversation = await _get_conversation(request.conversation_id, session, current_user.id)
    history = await _load_history(conversation.id, session)

    if conversation.title is None and not history:
        conversation.title = _make_title(request.message)

    session.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
    )
    await session.flush()

    results = await run_orchestrator(request.message, history, session)

    responses: list[RoleResponse] = []
    for result in results:
        citations = [ChunkCitation.model_validate(item) for item in result.citations]
        safe_sources = _json_safe([item.model_dump() for item in citations])
        session.add(
            Message(
                conversation_id=conversation.id,
                role=result.role,
                content=result.content,
                sources=safe_sources,
            )
        )
        responses.append(
            RoleResponse(role=result.role, content=result.content, citations=citations)
        )

    await session.commit()
    return ChatResponse(conversation_id=conversation.id, responses=responses)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    conversation = await _get_conversation(request.conversation_id, session, current_user.id)
    history = await _load_history(conversation.id, session)

    if conversation.title is None and not history:
        conversation.title = _make_title(request.message)

    session.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
        )
    )
    await session.flush()
    await session.commit()

    async def event_generator():
        current_role: str | None = None
        role_citations: dict[str, list[dict[str, Any]]] = {}

        try:
            async for event in run_orchestrator_stream(
                request.message, history, session, conversation.id
            ):
                event_type = event["event"]
                event_data = event["data"]

                if event_type == "role_start":
                    current_role = event_data["role"]

                if event_type == "citations" and current_role:
                    role_citations[current_role] = event_data.get("citations", [])

                if event_type == "role_end":
                    role = event_data["role"]
                    content = event_data["content"]
                    citations_data = role_citations.get(role)
                    session.add(
                        Message(
                            conversation_id=conversation.id,
                            role=role,
                            content=content,
                            sources=_json_safe(citations_data) if citations_data else None,
                        )
                    )
                    await session.flush()

                yield f"event: {event_type}\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            await session.commit()
        except Exception as exc:
            error_data = json.dumps({"error": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {error_data}\n\n"
            await session.rollback()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await session.delete(conversation)
    await session.commit()
    return Response(status_code=204)
