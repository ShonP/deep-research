"""Web page fetcher: download + extract main text content."""
from __future__ import annotations

import json

from agent_framework._tools import tool


@tool
def fetch_page(url: str) -> str:
    """Fetch a web page and extract its main text content."""
    import httpx
    import trafilatura

    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (deep-research bot)"},
        )
        resp.raise_for_status()
        text = trafilatura.extract(resp.text) or ""
        # Truncate to avoid exceeding context limits
        if len(text) > 8000:
            text = text[:8000] + "\n... [truncated]"
        return json.dumps({"url": url, "content": text or "(no extractable content)"})
    except Exception as e:
        return json.dumps({"url": url, "error": str(e)})
