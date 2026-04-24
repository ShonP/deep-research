"""Research agent: investigates a topic using web search and page fetching."""
from __future__ import annotations

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from deep_research.tools.search import web_search
from deep_research.tools.fetch import web_fetch


SYSTEM_PROMPT = """\
You are a thorough web researcher. You are given a research topic to investigate.

Your process:
1. Use web_search to find relevant pages about the topic.
2. Use web_fetch to read the most promising pages (pick 2-3 best results).
3. Synthesize what you learn into a clear summary.

Your final message MUST be a research summary that includes:
- Key findings and insights
- Specific facts, techniques, or data discovered
- Source URLs for citations (include the actual URLs you visited)

Be thorough but concise. Focus on factual, actionable information.
Write your summary as plain text (not JSON).
"""


def create_research_agent() -> Agent:
    """Create the web-research agent with search and fetch tools."""
    return Agent(
        client=OpenAIChatClient(),
        name="ResearchAgent",
        instructions=SYSTEM_PROMPT,
        tools=[web_search, web_fetch],
    )
