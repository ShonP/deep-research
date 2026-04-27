"""Research agent: investigates a topic using web search and page fetching."""
from __future__ import annotations

from deep_research.agent_runner import run_agent


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


def research_topic(topic: str, query: str) -> str:
    """Research a topic using web search and page fetching.

    Returns the research summary as plain text.
    """
    prompt = (
        f"Research the following topic thoroughly:\n\n{topic}\n\n"
        f"Context — this is part of a larger research project on: {query}"
    )
    return run_agent(
        system_prompt=SYSTEM_PROMPT,
        user_message=prompt,
        tools=["web_search", "fetch_page"],
    )

