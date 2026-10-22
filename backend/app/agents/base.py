from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from ..llm.qwen import get_qwen_client
from ..rag.retriever import RetrievedChunk, retrieve_chunks

_GROUNDING_RULES_WITH_CONTEXT = """回答规范：
- 仅当上述片段确实包含回答所需信息时才作答，并在关键论断后标注编号引用（如 [1]）
- 若片段与问题不相关或不足以回答，请明确说明知识库中未找到充分依据，然后拒答或向用户提出澄清问题
- 事实性细节不要编造，知识库未涵盖的内容需明确说明
- 寒暄或纯通用性问答可正常回应，但需说明依据并非来自知识库"""

_GROUNDING_RULES_EMPTY = """回答规范：
- 知识库中未检索到与该问题相关的片段
- 对事实性/知识性问题请直接拒答（说明知识库无相关资料）或向用户提出澄清问题，不要编造答案
- 寒暄或纯通用性问答可正常回应"""


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
        context_lines = [
            f"[{index + 1}] {item.content} (source: {item.source or 'unknown'}, chunk {item.chunk_index})"
            for index, item in enumerate(retrieved)
        ]
        return "\n".join(context_lines)

    @staticmethod
    def _build_citations(retrieved: list[RetrievedChunk]) -> list[dict[str, Any]]:
        return [
            {
                "document_id": item.document_id,
                "chunk_id": item.chunk_id,
                "chunk_index": item.chunk_index,
                "source": item.source,
                "score": item.score,
                "start_line": item.start_line,
                "end_line": item.end_line,
                "line_number_kind": item.line_number_kind,
            }
            for item in retrieved
        ]

    def _build_system_prompt(self, retrieved: list[RetrievedChunk]) -> str:
        if not self.rag_enabled:
            return self.system_prompt
        if retrieved:
            context_block = self._format_retrieved_chunks(retrieved)
            return (
                f"{self.system_prompt}\n\n知识库检索片段（可能相关也可能不相关）：\n"
                f"{context_block}\n\n{_GROUNDING_RULES_WITH_CONTEXT}"
            )
        return f"{self.system_prompt}\n\n{_GROUNDING_RULES_EMPTY}"

    async def _prepare_rag_context(
        self,
        message: str,
        session: Any,
    ) -> tuple[list[RetrievedChunk], list[dict[str, Any]]]:
        if not self.rag_enabled:
            return [], []
        retrieved = await retrieve_chunks(message, session)
        return retrieved, self._build_citations(retrieved)

    async def _respond_with_llm(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> RoleResult:
        qwen = get_qwen_client()
        retrieved, citations = await self._prepare_rag_context(message, session)
        self._last_citations = citations
        system_prompt = self._build_system_prompt(retrieved)

        content = await qwen.chat(system_prompt, message, history)
        return RoleResult(role=self.role, content=content, citations=citations)

    async def _respond_stream_with_llm(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> AsyncIterator[str]:
        qwen = get_qwen_client()
        retrieved, citations = await self._prepare_rag_context(message, session)
        self._last_citations = citations
        system_prompt = self._build_system_prompt(retrieved)

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
