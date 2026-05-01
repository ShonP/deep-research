"""Tools package — registers default search providers."""

from __future__ import annotations

import agent_framework._clients as _  # noqa: F401 — resolve circular import in agent_framework 1.2.x

from deep_research.tools.provider import (
    GitHubSearchProvider,
    GitHubTrendingProvider,
    HackerNewsProvider,
    RedditProvider,
    RSSProvider,
    WebSearchProvider,
)
from deep_research.tools.registry import register

# Default providers (always active)
register(WebSearchProvider())
register(GitHubSearchProvider())
register(RedditProvider())
register(HackerNewsProvider())
register(RSSProvider())
register(GitHubTrendingProvider())
