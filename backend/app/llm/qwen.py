from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any

from ..config import get_settings

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

_EMBED_BATCH_SIZE = 10


class _DashScopeEmbeddings:
    def __init__(self, model: str) -> None:
        self._model = model

    def _parse_response(self, response: Any) -> list[list[float]]:
        status = getattr(response, "status_code", None)
        try:
            status_code = int(status)
        except Exception:
            status_code = 0

        if status_code != int(HTTPStatus.OK):
            message = getattr(response, "message", "")
            raise RuntimeError(f"DashScope embeddings failed: status={status} message={message}")

        output = getattr(response, "output", None)
        if not isinstance(output, dict):
            raise RuntimeError("DashScope embeddings returned invalid output")

        embeddings = output.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("DashScope embeddings missing embeddings list")

        vectors: list[list[float]] = []
        for item in embeddings:
            if not isinstance(item, dict) or "embedding" not in item:
                raise RuntimeError("DashScope embeddings item missing embedding")
            vectors.append(item["embedding"])

        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from dashscope.embeddings import TextEmbedding

        response = TextEmbedding.call(model=self._model, input=texts)
        return self._parse_response(response)

    def embed_query(self, text: str) -> list[float]:
        from dashscope.embeddings import TextEmbedding

        response = TextEmbedding.call(model=self._model, input=[text])
        vectors = self._parse_response(response)
        return vectors[0] if vectors else []


class QwenClient:
    def __init__(self) -> None:
        settings = get_settings()

        if settings.dashscope_http_base_url:
            self._chat = ChatOpenAI(
                model=settings.qwen_model,
                temperature=0.2,
                api_key=settings.dashscope_api_key or "EMPTY",
                base_url=settings.dashscope_http_base_url,
            )
            # check_embedding_ctx_length=False 避免按 OpenAI 模型用 tiktoken 分词计数
            self._embeddings = OpenAIEmbeddings(
                model=settings.qwen_embedding_model,
                api_key=settings.dashscope_api_key or "EMPTY",
                base_url=settings.dashscope_http_base_url,
                check_embedding_ctx_length=False,
            )
        else:
            import dashscope

            if settings.dashscope_api_key:
                os.environ.setdefault("DASHSCOPE_API_KEY", settings.dashscope_api_key)
                dashscope.api_key = settings.dashscope_api_key
            self._chat = ChatTongyi(model=settings.qwen_model, temperature=0.2)
            self._embeddings = _DashScopeEmbeddings(model=settings.qwen_embedding_model)

    async def _invoke(self, messages: list[Any]) -> Any:
        if hasattr(self._chat, "ainvoke"):
            return await self._chat.ainvoke(messages)
        return await asyncio.to_thread(self._chat.invoke, messages)

    async def chat(self, system_prompt: str, user_prompt: str, history: list[dict[str, Any]] | None) -> str:
        messages: list[Any] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        if history:
            for item in history:
                role = item.get("role")
                content = item.get("content", "")
                if not content:
                    continue
                if role == "user":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_prompt))
        response = await self._invoke(messages)
        return getattr(response, "content", str(response))

    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type,
    ) -> Any:
        messages: list[Any] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_prompt))

        try:
            structured_model = self._chat.with_structured_output(schema, method="json_mode")
            if hasattr(structured_model, "ainvoke"):
                result = await structured_model.ainvoke(messages)
            else:
                result = await asyncio.to_thread(structured_model.invoke, messages)
            logger.debug("chat_structured: json_mode path succeeded")
            return result
        except Exception as exc:
            logger.warning("chat_structured: json_mode failed (%s), falling back to manual JSON parsing", exc)

        json_instruction = (
            "\n\n请严格以 JSON 格式输出，schema 如下：\n"
            f"{schema.model_json_schema()}\n"
            "只输出 JSON，不要有任何其他文字。"
        )
        messages_with_instruction = [
            *messages[:-1],
            HumanMessage(content=messages[-1].content + json_instruction),
        ]
        response = await self._invoke(messages_with_instruction)
        raw = getattr(response, "content", str(response))
        return schema.model_validate_json(raw.strip().strip("`").removeprefix("json").strip())

    async def chat_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        history: list[dict[str, Any]] | None,
    ) -> AsyncIterator[str]:
        messages: list[Any] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))

        if history:
            for item in history:
                role = item.get("role")
                content = item.get("content", "")
                if not content:
                    continue
                if role == "user":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_prompt))

        async for chunk in self._chat.astream(messages):
            token = getattr(chunk, "content", "")
            if token:
                yield token

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # DashScope 端点单次嵌入上限 10 条文本
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[start : start + _EMBED_BATCH_SIZE]
            embeddings.extend(await asyncio.to_thread(self._embeddings.embed_documents, batch))
        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embeddings.embed_query, text)


_client: QwenClient | None = None


def get_qwen_client() -> QwenClient:
    global _client
    if _client is None:
        _client = QwenClient()
    return _client
