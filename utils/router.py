"""
Routing utilities: structured output chain + routing schema.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_together import ChatTogether
from pydantic import BaseModel, Field

from prompts.system_prompts import ROUTING_SYSTEM_PROMPT


class RouteQuery(BaseModel):
    """Schema for routing queries to appropriate agents."""
    destination: Literal["suspicious_activity", "company_info", "account_info", "unrelated"] = Field(
        description="The agent to route this query to"
    )
    task: str = Field(description="A brief description of the task for the agent")


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

