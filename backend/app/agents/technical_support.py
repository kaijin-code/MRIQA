from __future__ import annotations

from .base import BaseRoleAgent


class TechnicalSupportAgent(BaseRoleAgent):
    role = "technical_support"
    system_prompt = (
        "You are a technical support agent. Use the knowledge base snippets "
        "when available and provide actionable troubleshooting steps."
    )
