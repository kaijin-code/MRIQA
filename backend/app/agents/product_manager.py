from __future__ import annotations

from .base import BaseRoleAgent


class ProductManagerAgent(BaseRoleAgent):
    role = "product_manager"
    system_prompt = (
        "You are a product manager. Provide structured product reasoning, "
        "trade-offs, and next-step recommendations."
    )
