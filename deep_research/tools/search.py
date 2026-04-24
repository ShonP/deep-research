"""Web search tool using DuckDuckGo."""
from __future__ import annotations

import json
from typing import Annotated

from agent_framework import tool


@tool
def web_search(
    query: Annotated[str, "The search query to look up on the web"],
    max_results: Annotated[int, "Maximum number of results to return"] = 5,
) -> str:
    """Search the web using DuckDuckGo and return results as JSON."""
    from duckduckgo_search import DDGS

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
    except Exception as e:
        return json.dumps({"error": str(e)})
