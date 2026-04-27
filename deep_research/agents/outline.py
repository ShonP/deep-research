"""Outline agent: generates a structured research outline from a query."""
from __future__ import annotations

from deep_research.llm import chat


SYSTEM_PROMPT = """\
You are a research planner. Given a research query, produce a structured outline
of the MOST IMPORTANT topics to investigate. Prioritize depth over breadth.

Respond with ONLY valid JSON (no markdown fences) in this format:
{
  "topics": [
    {
      "title": "Topic title",
      "description": "What to investigate",
      "priority": "high|medium",
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
      "priority": "high|medium",
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


def generate_outline(query: str, source: str = "web") -> str:
    """Generate a research outline for the given query.

    Returns the raw JSON string from the model.
    """
    prompt = GITHUB_OUTLINE_PROMPT if source in ("github", "both") else SYSTEM_PROMPT
    return chat(
        system_prompt=prompt,
        user_message=f"Create a research outline for: {query}",
        reasoning_effort="low",
    )

