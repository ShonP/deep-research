"""Search provider registry — maps source names to SearchProvider instances."""

from __future__ import annotations

from deep_research.tools.provider import SearchProvider

_PROVIDERS: dict[str, SearchProvider] = {}


def register(provider: SearchProvider) -> None:
    """Register a search provider by its name."""
    _PROVIDERS[provider.name] = provider


def get_providers(source: str) -> list[SearchProvider]:
    """Get providers for a source. 'both'/'all' returns all registered providers."""
    if source in _PROVIDERS:
        return [_PROVIDERS[source]]
    return list(_PROVIDERS.values())


def register_extra_providers(provider_names: list[str]) -> None:
    """Register additional providers by name (youtube, reddit, hackernews, rss, github-trending)."""
    from deep_research.tools.provider import EXTRA_PROVIDERS

    for name in provider_names:
        name = name.strip().lower()
        if name in EXTRA_PROVIDERS and name not in _PROVIDERS:
            provider_cls = EXTRA_PROVIDERS[name]
            register(provider_cls())
            from deep_research.log import log
            log.info("Registered extra provider: %s", name)
