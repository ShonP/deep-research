"""Web search tool using DuckDuckGo."""

from __future__ import annotations

import json

from agent_framework._tools import tool


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo and return results as JSON."""
    from ddgs import DDGS

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return json.dumps({"results": [], "message": "No results found."})
        formatted = [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in results
        ]
        return json.dumps({"results": formatted})
    except (json.JSONDecodeError, OSError) as e:
        return json.dumps({"error": str(e)})
