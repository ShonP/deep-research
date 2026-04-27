"""Research agent: investigates a topic using web search and page fetching."""
from __future__ import annotations

from agent_framework._agents import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import (
    caching,
    llm_call_logging,
    retry,
    tool_call_logging,
)
from deep_research.tools.fetch import fetch_page
from deep_research.tools.search import web_search

SYSTEM_PROMPT = """\
You are a thorough web researcher. You are given a research topic to investigate.

Your process:
1. Use web_search to find relevant pages about the topic.
2. Use fetch_page to read the most promising pages (pick 2-3 best results).
3. Synthesize what you learn into a clear summary.

Your final message MUST be a research summary that includes:
- Key findings and insights
- Specific facts, techniques, or data discovered
- Source URLs for citations (include the actual URLs you visited)

Be thorough but concise. Focus on factual, actionable information.
Write your summary as plain text (not JSON).
"""


async def research_topic(topic: str, query: str) -> str:
    agent = Agent(
        client=get_chat_client(),
        name="web-researcher",
        instructions=SYSTEM_PROMPT,
        tools=[web_search, fetch_page],
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )
    prompt = (
        f"Research the following topic thoroughly:\n\n{topic}\n\n"
        f"Context — this is part of a larger research project on: {query}"
    )
    response = await agent.run(prompt)
    return response.text
