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
