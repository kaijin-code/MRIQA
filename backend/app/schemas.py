from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    roles: list[Literal["customer_service", "technical_support", "product_manager"]]


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(..., min_length=1)
    metadata: dict[str, Any] | None = None


class ChunkCitation(BaseModel):
    document_id: UUID
    chunk_id: UUID
    source: str | None = None
    score: float


class RoleResponse(BaseModel):
    role: str
    content: str
    citations: list[ChunkCitation] = Field(default_factory=list)


class ChatResponse(BaseModel):
    conversation_id: UUID
    responses: list[RoleResponse]


class MessageItem(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list[dict] | None = None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: UUID
    title: str | None = None
    created_at: datetime
    last_message_at: datetime | None = None
    message_count: int


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class ConversationHistoryResponse(BaseModel):
    id: UUID
    title: str | None = None
    created_at: datetime
    messages: list[MessageItem]


class DocumentInput(BaseModel):
    title: str | None = None
    source: str | None = None
    text: str = Field(..., min_length=1)


class IngestRequest(BaseModel):
    documents: list[DocumentInput]


class IngestResponse(BaseModel):
    documents: int
    chunks: int


class DocumentSummary(BaseModel):
    id: UUID
    title: str | None = None
    source: str | None = None
    created_at: datetime
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=64, max_length=64)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=64, max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserInfo"


class UserInfo(BaseModel):
    id: UUID
    username: str
    email: str
    created_at: datetime
