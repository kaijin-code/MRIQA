from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class RoleResult:
    role: str
    content: str
    citations: list[dict[str, Any]]


class BaseRoleAgent:
    role: str = ""
    system_prompt: str = ""
    _last_citations: list[dict[str, Any]] = []

    async def respond(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> RoleResult:
        raise NotImplementedError

    async def respond_stream(
        self,
        message: str,
        history: list[dict[str, Any]] | None,
        session: Any,
    ) -> AsyncIterator[str]:
        raise NotImplementedError
