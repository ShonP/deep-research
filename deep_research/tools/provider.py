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


# --- Extra providers (opt-in via --providers flag) ---

YOUTUBE_INSTRUCTIONS = """You are a YouTube researcher.
1. Use youtube_search to find relevant videos on the topic.
2. Use youtube_transcript to get the full transcript of promising videos.
3. Synthesize key insights from the video content.
Include video titles, links, and key quotes from transcripts.
"""

REDDIT_INSTRUCTIONS = """You are a Reddit researcher.
1. Use fetch_reddit to get top posts from relevant subreddits.
2. Focus on discussions with high engagement (score, comments).
3. Synthesize key opinions, recommendations, and links shared.
"""

HN_INSTRUCTIONS = """You are a Hacker News researcher.
1. Use fetch_hackernews to get top stories.
2. Focus on stories relevant to the research topic.
3. Note community sentiment and linked resources.
"""

RSS_INSTRUCTIONS = """You are an RSS feed researcher.
1. Use fetch_rss to read relevant feeds.
2. Focus on recent articles matching the research topic.
3. Summarize key findings with source links.
"""

GITHUB_TRENDING_INSTRUCTIONS = """You are a GitHub Trending researcher.
1. Use github_trending to find trending repos.
2. Focus on repos relevant to the research topic.
3. Note star counts, languages, and descriptions.
"""


@dataclass(frozen=True)
class YouTubeProvider:
    name: str = "youtube"
    instructions: str = YOUTUBE_INSTRUCTIONS
    tools: list = field(default_factory=lambda: _youtube_tools())

@dataclass(frozen=True)
class RedditProvider:
    name: str = "reddit"
    instructions: str = REDDIT_INSTRUCTIONS
    tools: list = field(default_factory=lambda: _reddit_tools())

@dataclass(frozen=True)
class HackerNewsProvider:
    name: str = "hackernews"
    instructions: str = HN_INSTRUCTIONS
    tools: list = field(default_factory=lambda: _hn_tools())

@dataclass(frozen=True)
class RSSProvider:
    name: str = "rss"
    instructions: str = RSS_INSTRUCTIONS
    tools: list = field(default_factory=lambda: _rss_tools())

@dataclass(frozen=True)
class GitHubTrendingProvider:
    name: str = "github-trending"
    instructions: str = GITHUB_TRENDING_INSTRUCTIONS
    tools: list = field(default_factory=lambda: _trending_tools())


def _youtube_tools():
    from deep_research.tools.youtube import youtube_search, youtube_transcript
    return [youtube_search, youtube_transcript]

def _reddit_tools():
    from deep_research.tools.reddit import fetch_reddit
    return [fetch_reddit]

def _hn_tools():
    from deep_research.tools.hackernews import fetch_hackernews
    return [fetch_hackernews]

def _rss_tools():
    from deep_research.tools.rss import fetch_rss
    return [fetch_rss]

def _trending_tools():
    from deep_research.tools.github_trending import github_trending
    return [github_trending]


EXTRA_PROVIDERS = {
    "youtube": YouTubeProvider,
    "reddit": RedditProvider,
    "hackernews": HackerNewsProvider,
    "rss": RSSProvider,
    "github-trending": GitHubTrendingProvider,
}
