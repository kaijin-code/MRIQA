from __future__ import annotations

from .base import BaseRoleAgent


class CustomerServiceAgent(BaseRoleAgent):  
    role = "customer_service"
    system_prompt = (
        "You are a customer service agent. Answer clearly and politely, "
        "focus on usage guidance, process, and high-level help."
    )
