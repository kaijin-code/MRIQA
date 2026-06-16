from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from .base import BaseRoleAgent, RoleResult
from ..llm.qwen import get_qwen_client
from ..rag.retriever import retrieve_chunks


class TechnicalSupportAgent(BaseRoleAgent):
    role = "technical_support"
    system_prompt = (
        "You are a technical support agent. Use the knowledge base snippets "
        "when available and provide actionable troubleshooting steps."
    )

    async def respond(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> RoleResult:
        qwen = get_qwen_client()
        retrieved = await retrieve_chunks(message, session)

        if retrieved:
            context_lines = [
                f"[{index + 1}] {item.content} (source: {item.source or 'unknown'})"
                for index, item in enumerate(retrieved)
            ]
            context_block = "\n".join(context_lines)
        else:
            context_block = "No knowledge base snippets available."

        system_prompt = f"{self.system_prompt}\n\nKnowledge base:\n{context_block}"
        content = await qwen.chat(system_prompt, message, history)

        citations = [
            {
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "source": item.source,
                "score": item.score,
            }
            for item in retrieved
        ]

        return RoleResult(role=self.role, content=content, citations=citations)

    async def respond_stream(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> AsyncIterator[str]:
        qwen = get_qwen_client()
        retrieved = await retrieve_chunks(message, session)

        if retrieved:
            context_lines = [
                f"[{index + 1}] {item.content} (source: {item.source or 'unknown'})"
                for index, item in enumerate(retrieved)
            ]
            context_block = "\n".join(context_lines)
        else:
            context_block = "No knowledge base snippets available."

        self._last_citations = [
            {
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "source": item.source,
                "score": item.score,
            }
            for item in retrieved
        ]

        system_prompt = f"{self.system_prompt}\n\nKnowledge base:\n{context_block}"
        async for token in qwen.chat_stream(system_prompt, message, history):
            yield token
