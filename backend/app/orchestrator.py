from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from .agents import CustomerServiceAgent, ProductManagerAgent, TechnicalSupportAgent
from .agents.base import RoleResult
from .llm.qwen import get_qwen_client
from .schemas import RouteDecision

logger = logging.getLogger(__name__)

ROLE_CUSTOMER = "customer_service"
ROLE_TECH = "technical_support"
ROLE_PM = "product_manager"


_ROUTER_SYSTEM_PROMPT = """你是一个多角色协作系统的路由器，需要根据用户问题判断由哪些角色回答。

可选角色：
- customer_service：客服。处理使用引导、账户/订单/售后流程、产品基础介绍、操作步骤、政策与规则等问题。
- technical_support：技术支持。处理报错排查、API/SDK 用法、集成调试、性能/兼容性问题、日志分析等技术细节问题。
- product_manager：产品经理。处理产品方向与策略、需求取舍与优先级、功能设计与方案权衡、路线图、竞品对比、指标/成功定义、用户场景与体验设计等问题。

判断规则：
1. 仔细理解用户意图，可以多选，只在确实需要多个角色协同时才多选，宁缺毋滥。
2. 单纯使用/操作问题 → 只选 customer_service。
3. 出错、报错、技术细节、调试 → 只选 technical_support。
4. 涉及"做不做、先做哪个、怎么设计、如何衡量、和竞品比、产品方向、优先级" → 选 product_manager。
5. 既要排查问题又要决定后续是否修复/排期 → technical_support, product_manager。
6. 既要给用户答复又涉及产品策略 → customer_service, product_manager。
7. 含糊不清或闲聊 → customer_service。"""


async def _select_roles(message: str, history: list[dict[str, Any]] | None) -> list[str]:
    qwen = get_qwen_client()
    decision: RouteDecision = await qwen.chat_structured(
        _ROUTER_SYSTEM_PROMPT, message, RouteDecision
    )
    logger.info("Router decision: message=%r decision=%s", message, decision.model_dump_json())
    return decision.roles or [ROLE_CUSTOMER]


async def run_orchestrator(
    message: str,
    history: list[dict[str, Any]] | None,
    session: Any,
) -> list[RoleResult]:
    roles = await _select_roles(message, history)

    agents = {
        ROLE_CUSTOMER: CustomerServiceAgent(),
        ROLE_TECH: TechnicalSupportAgent(),
        ROLE_PM: ProductManagerAgent(),
    }

    results: list[RoleResult] = []
    for role in roles:
        agent = agents.get(role)
        if agent is None:
            continue
        results.append(await agent.respond(message, history, session))

    return results


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(val) for key, val in value.items()}
    return value


async def run_orchestrator_stream(
    message: str,
    history: list[dict[str, Any]] | None,
    session: Any,
    conversation_id: UUID,
) -> AsyncIterator[dict[str, Any]]:
    roles = await _select_roles(message, history)

    yield {"event": "start", "data": {"conversation_id": str(conversation_id)}}

    agents = {
        ROLE_CUSTOMER: CustomerServiceAgent(),
        ROLE_TECH: TechnicalSupportAgent(),
        ROLE_PM: ProductManagerAgent(),
    }

    for role in roles:
        agent = agents.get(role)
        if agent is None:
            continue

        yield {"event": "role_start", "data": {"role": role}}

        full_content = ""
        async for token in agent.respond_stream(message, history, session):
            full_content += token
            yield {"event": "token", "data": {"content": token}}

        citations = getattr(agent, "_last_citations", [])
        if citations:
            yield {"event": "citations", "data": {"citations": _json_safe(citations)}}

        yield {"event": "role_end", "data": {"role": role, "content": full_content}}

    yield {"event": "done", "data": {}}
