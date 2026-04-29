"""Search provider protocol and concrete implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from deep_research.tools.fetch import fetch_page
from deep_research.tools.github_read import github_read
from deep_research.tools.github_search import github_search
from deep_research.tools.search import web_search


@runtime_checkable
class SearchProvider(Protocol):
    """Contract that all search providers must follow."""

    @property
    def name(self) -> str:
        """Unique identifier for this provider (e.g. 'web', 'github')."""
        ...

    @property
    def tools(self) -> list:
        """MAF @tool-decorated functions this provider offers."""
        ...

    @property
    def instructions(self) -> str:
        """Provider-specific research instructions for the agent."""
        ...


WEB_INSTRUCTIONS = """\
You are a thorough web researcher.

Your process:
1. Use web_search to find relevant pages about the topic.
2. Use fetch_page to read the most promising pages (pick 2-3 best results).
3. Synthesize what you learn into a clear summary.

Include key findings, specific facts, and source URLs for citations.
Be thorough but concise. Focus on factual, actionable information.
"""

GITHUB_INSTRUCTIONS = """\
You are a GitHub-focused researcher.

Your process:
1. Use github_search with mode='repos' to find relevant repositories.
2. Use github_search with mode='code' to find specific implementation patterns.
3. Use github_search with mode='issues' to find discussions and solutions.
4. Use github_read to dive into specific files you discover.
5. Synthesize your findings into a clear summary.

Include repository links, code snippets, architecture patterns, and issue discussions.
Be thorough but concise. Focus on real-world, production-quality implementations.
"""


@dataclass(frozen=True)
class WebSearchProvider:
    """Web search provider using Tavily/DuckDuckGo/SearXNG + page fetching."""

    name: str = "web"
    instructions: str = WEB_INSTRUCTIONS
    tools: list = field(default_factory=lambda: [web_search, fetch_page])


@dataclass(frozen=True)
class GitHubSearchProvider:
    """GitHub search provider using gh CLI for repos, code, and issues."""

    name: str = "github"
    instructions: str = GITHUB_INSTRUCTIONS
    tools: list = field(default_factory=lambda: [github_search, github_read])
