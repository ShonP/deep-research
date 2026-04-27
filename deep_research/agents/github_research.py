"""GitHub research agent: investigates topics by searching GitHub repos, code, and issues."""
from __future__ import annotations

from agent_framework._agents import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import LoggingMiddleware, RetryMiddleware
from deep_research.tools.github_read import github_read
from deep_research.tools.github_search import github_search

SYSTEM_PROMPT = """\
You are a GitHub-focused researcher. You investigate topics by finding real-world
implementations, open-source projects, and community discussions on GitHub.

Your process:
1. Use github_search with mode='repos' to find relevant repositories.
2. Use github_search with mode='code' to find specific implementation patterns.
3. Use github_search with mode='issues' to find discussions and solutions.
4. Use github_read to dive into specific files you discover.
5. Synthesize your findings into a clear summary.

Your final message MUST be a research summary that includes:
- Repository links with star counts and descriptions
- Code snippets or architecture patterns you found
- Key implementation approaches and trade-offs
- Links to relevant issues/discussions

Be thorough but concise. Focus on real-world, production-quality implementations.
Write your summary as plain text (not JSON).
"""


async def github_research_topic(topic: str, query: str) -> str:
    """Research a topic using GitHub search and file reading.

    Returns the research summary as plain text.
    """
    agent = Agent(
        client=get_chat_client(),
        name="github_researcher",
        instructions=SYSTEM_PROMPT,
        tools=[github_search, github_read],
        middleware=[LoggingMiddleware(), RetryMiddleware()],
    )
    prompt = (
        f"Research the following topic thoroughly:\n\n{topic}\n\n"
        f"Context — this is part of a larger research project on: {query}"
    )
    response = await agent.run(prompt)
    return response.text

