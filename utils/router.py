"""
Routing utilities: structured output chain + routing schema.
"""

from __future__ import annotations

from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_together import ChatTogether

from prompts.system_prompts import ROUTING_SYSTEM_PROMPT


class RouteQuery(TypedDict):
    destination: Literal["suspicious_activity", "company_info", "account_info", "unrelated"]
    task: str


def create_route_chain(model: str = "openai/gpt-oss-120b", temperature: float = 0.0):
    """
    Build the structured-output routing chain.
    """
    router_llm = ChatTogether(model=model, temperature=temperature)
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTING_SYSTEM_PROMPT),
            ("human", "{question}"),
        ]
    )
    return route_prompt | router_llm.with_structured_output(RouteQuery)

