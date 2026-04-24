"""Outline agent: generates a structured research outline from a query."""
from __future__ import annotations

from agent_framework import Agent
from agent_framework.github import GitHubCopilotAgent


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


def create_outline_agent() -> Agent:
    """Create the outline-generation agent."""
    return GitHubCopilotAgent(
        name="OutlineAgent",
        instructions=SYSTEM_PROMPT,
    )
