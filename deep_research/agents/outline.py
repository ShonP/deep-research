"""Outline agent: generates a structured research outline from a query."""
from __future__ import annotations

from deep_research.llm import chat


SYSTEM_PROMPT = """\
You are a research planner. Given a research query, produce a structured outline
of topics and subtopics that should be investigated to comprehensively answer the
query.

Respond with ONLY valid JSON (no markdown fences) in this format:
{
  "topics": [
    {
      "title": "Topic title",
      "description": "What to investigate",
      "subtopics": ["subtopic 1", "subtopic 2"]
    }
  ]
}

Generate 3-4 topics. Each topic should have 1-2 subtopics. Ensure the outline
covers the query from multiple angles (definition, techniques, examples,
best practices, pitfalls, etc.).
"""


GITHUB_OUTLINE_PROMPT = """\
You are a research planner specializing in open-source software discovery. Given a
research query, produce a structured outline of topics optimized for searching
GitHub repositories, code patterns, and issue discussions.

Respond with ONLY valid JSON (no markdown fences) in this format:
{
  "topics": [
    {
      "title": "Topic title",
      "description": "What to search for on GitHub — frame as code/repo search queries",
      "subtopics": ["specific pattern to find", "alternative approach to search"]
    }
  ]
}

Generate 3-4 topics. Each topic should have at most 1-2 subtopics (keep it focused).
Total research queries will be topics + subtopics, so aim for 8-10 total maximum.
Frame descriptions as things to search for in code and repos,
e.g. "Find repos implementing X", "Search for code patterns using Y library",
"Look for issues discussing Z trade-offs".
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

