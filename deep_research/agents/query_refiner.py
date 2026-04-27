"""Query refiner agent: generates optimized search queries for a research topic."""
from __future__ import annotations

import json

from agent_framework._agents import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import llm_call_logging

SYSTEM_PROMPT = """\
You are a search query optimizer. Given a research topic and context, generate
2-3 highly targeted search queries that will return the best results.

Rules:
- Each query should target a DIFFERENT angle or aspect
- Use specific keywords, not vague phrases
- Include technical terms when appropriate
- Avoid redundancy between queries

Respond with ONLY valid JSON (no markdown fences):
{"queries": ["query 1", "query 2", "query 3"]}
"""


async def refine_queries(topic: str, context: str, max_queries: int = 3) -> list[str]:
    """Generate 2-3 optimized search queries for a research topic."""
    agent = Agent(
        client=get_chat_client(),
        name="query-refiner",
        instructions=SYSTEM_PROMPT,
        middleware=[llm_call_logging],
    )
    prompt = (
        f"Research topic: {topic}\n"
        f"Broader context: {context}\n"
        f"Generate {max_queries} optimized search queries."
    )
    response = await agent.run(prompt)
    return _parse_queries(response.text, topic, max_queries)


def _parse_queries(text: str, fallback_topic: str, max_queries: int) -> list[str]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        data = json.loads(text.strip())
        queries = data.get("queries", [])
        return queries[:max_queries] if queries else [fallback_topic]
    except (json.JSONDecodeError, KeyError):
        return [fallback_topic]
