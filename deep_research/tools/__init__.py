from __future__ import annotations

import agent_framework._clients as _  # noqa: F401 — resolve circular import in agent_framework 1.2.x

from deep_research.tools.fetch import fetch_page
from deep_research.tools.github_read import github_read
from deep_research.tools.github_search import github_search
from deep_research.tools.provider import GitHubSearchProvider, WebSearchProvider
from deep_research.tools.registry import register
from deep_research.tools.search import web_search

register(WebSearchProvider())
register(GitHubSearchProvider())

__all__ = ["fetch_page", "github_read", "github_search", "web_search"]
