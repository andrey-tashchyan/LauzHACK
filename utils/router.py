"""
Routing utilities: structured output chain + routing schema.
"""

from __future__ import annotations

from typing import Literal, Iterator

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
    confidence: float = Field(
        default=1.0,
        description="Confidence score (0-1) for the routing decision"
    )


def create_route_chain(model: str = "openai/gpt-oss-120b", temperature: float = 0.0):
    """
    Build the structured-output routing chain.

    Args:
        model: Together AI model name
        temperature: LLM temperature (0 = deterministic)

    Returns:
        A LangChain chain that routes queries to appropriate agents
    """
    router_llm = ChatTogether(model=model, temperature=temperature)
    route_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTING_SYSTEM_PROMPT),
            ("human", "{question}"),
        ]
    )
    return route_prompt | router_llm.with_structured_output(RouteQuery)


def create_route_chain_stream(model: str = "openai/gpt-oss-120b", temperature: float = 0.0):
    """
    Build a streaming routing chain (falls back to non-streaming for routing decisions).

    Note: Routing decisions themselves don't benefit from streaming since we need
    the complete structured output. This is kept for API consistency.

    Args:
        model: Together AI model name
        temperature: LLM temperature

    Returns:
        Same as create_route_chain (routing doesn't stream)
    """
    # Routing decisions need complete structured output, so we return the same chain
    return create_route_chain(model=model, temperature=temperature)

