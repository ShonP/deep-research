"""Query refiner agent: generates optimized search queries for a research topic."""

from __future__ import annotations

from agent_framework import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import llm_call_logging
from deep_research.models.state import RefinedQueries

SYSTEM_PROMPT = """\
You are a search query optimizer. Given a research topic and context, generate
2-3 highly targeted search queries that will return the best results.

Rules:
- Each query should target a DIFFERENT angle or aspect
- Use specific keywords, not vague phrases
- Include technical terms when appropriate
- Avoid redundancy between queries
"""


async def refine_queries(topic: str, context: str, max_queries: int = 3) -> list[str]:
    """Generate 2-3 optimized search queries for a research topic."""
    agent = Agent(
        client=get_chat_client(),
        name="query-refiner",
        instructions=SYSTEM_PROMPT,
        middleware=[llm_call_logging],
    )
    prompt = f"Research topic: {topic}\nBroader context: {context}\nGenerate {max_queries} optimized search queries."
    response = await agent.run(prompt, options={"response_format": RefinedQueries})
    if response.value:
        queries = response.value.queries[:max_queries]
        return queries if queries else [topic]
    return [topic]
