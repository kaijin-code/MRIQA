from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from .base import BaseRoleAgent, RoleResult
from ..llm.qwen import get_qwen_client


class CustomerServiceAgent(BaseRoleAgent):  
    role = "customer_service"
    system_prompt = (
        "You are a customer service agent. Answer clearly and politely, "
        "focus on usage guidance, process, and high-level help."
    )

    async def respond(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> RoleResult:
        qwen = get_qwen_client()
        content = await qwen.chat(self.system_prompt, message, history)
        return RoleResult(role=self.role, content=content, citations=[])

    async def respond_stream(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> AsyncIterator[str]:
        qwen = get_qwen_client()
        self._last_citations = []
        async for token in qwen.chat_stream(self.system_prompt, message, history):
            yield token
