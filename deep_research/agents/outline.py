"""Outline agent: generates a structured research outline from a query."""
from __future__ import annotations

from agent_framework._agents import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import llm_call_logging

SYSTEM_PROMPT = """\
You are a research planner. Given a research query, produce a structured outline
of the MOST IMPORTANT topics to investigate. Prioritize depth over breadth.

Respond with ONLY valid JSON (no markdown fences) in this format:
{
  "topics": [
    {
      "title": "Topic title",
      "description": "What to investigate",
      "subtopics": ["subtopic 1"]
    }
  ]
}

Rules:
- Generate 3 topics maximum (the most important ones)
- Each topic should have 0-1 subtopics (only if truly needed)
- Total queries (topics + subtopics) MUST be 5 or fewer
- Prioritize: what gives the most actionable insight?
- Skip obvious/introductory topics — focus on what matters
"""

GITHUB_OUTLINE_PROMPT = """\
You are a research planner specializing in open-source software discovery. Given a
research query, produce a focused outline for searching GitHub.

Respond with ONLY valid JSON (no markdown fences) in this format:
{
  "topics": [
    {
      "title": "Topic title",
      "description": "What to search for on GitHub",
      "subtopics": ["specific pattern to find"]
    }
  ]
}

Rules:
- Generate 3 topics maximum
- Each topic should have 0-1 subtopics
- Total queries (topics + subtopics) MUST be 5 or fewer
- Focus on finding the BEST repos and code, not exhaustive coverage
- Frame as: "Find repos implementing X", "Search code for Y pattern"
"""


async def generate_outline(query: str, source: str = "web") -> str:
    prompt = GITHUB_OUTLINE_PROMPT if source in ("github", "both") else SYSTEM_PROMPT
    agent = Agent(
        client=get_chat_client(),
        name="outline-planner",
        instructions=prompt,
        middleware=[llm_call_logging],
    )
    response = await agent.run(f"Create a research outline for: {query}")
    return response.text
