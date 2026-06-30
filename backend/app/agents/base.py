from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from ..llm.qwen import get_qwen_client
from ..rag.retriever import RetrievedChunk, retrieve_chunks


@dataclass
class RoleResult:
    role: str
    content: str
    citations: list[dict[str, Any]]


class BaseRoleAgent:
    role: str = ""
    system_prompt: str = ""
    rag_enabled: bool = True
    _last_citations: list[dict[str, Any]] = []

    def __init__(self) -> None:
        self._last_citations = []

    @staticmethod
    def _format_retrieved_chunks(retrieved: list[RetrievedChunk]) -> str:
        if not retrieved:
            return "No knowledge base snippets available."

        context_lines = [
            f"[{index + 1}] {item.content} (source: {item.source or 'unknown'})"
            for index, item in enumerate(retrieved)
        ]
        return "\n".join(context_lines)

    @staticmethod
    def _build_citations(retrieved: list[RetrievedChunk]) -> list[dict[str, Any]]:
        return [
            {
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "source": item.source,
                "score": item.score,
            }
            for item in retrieved
        ]

    async def _prepare_rag_context(
        self,
        message: str,
        session: Any,
    ) -> tuple[str, list[dict[str, Any]]]:
        if not self.rag_enabled:
            return "", []

        retrieved = await retrieve_chunks(message, session)
        return self._format_retrieved_chunks(retrieved), self._build_citations(retrieved)

    async def _respond_with_llm(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> RoleResult:
        qwen = get_qwen_client()
        context_block, citations = await self._prepare_rag_context(message, session)
        self._last_citations = citations
        system_prompt = self.system_prompt
        if context_block:
            system_prompt = f"{system_prompt}\n\nKnowledge base:\n{context_block}"

        content = await qwen.chat(system_prompt, message, history)
        return RoleResult(role=self.role, content=content, citations=citations)

    async def _respond_stream_with_llm(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> AsyncIterator[str]:
        qwen = get_qwen_client()
        context_block, citations = await self._prepare_rag_context(message, session)
        self._last_citations = citations

        system_prompt = self.system_prompt
        if context_block:
            system_prompt = f"{system_prompt}\n\nKnowledge base:\n{context_block}"

        async for token in qwen.chat_stream(system_prompt, message, history):
            yield token

    async def respond(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> RoleResult:
        return await self._respond_with_llm(message, history, session)

    async def respond_stream(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> AsyncIterator[str]:
        async for token in self._respond_stream_with_llm(message, history, session):
            yield token
