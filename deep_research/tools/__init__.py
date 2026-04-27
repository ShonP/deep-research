import agent_framework._clients as _  # noqa: F401 — resolve circular import in agent_framework 1.2.x

from deep_research.tools.search import web_search
from deep_research.tools.fetch import fetch_page
from deep_research.tools.github_search import github_search
from deep_research.tools.github_read import github_read

__all__ = ["web_search", "fetch_page", "github_search", "github_read"]
