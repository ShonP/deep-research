"""Web page fetcher: download + extract main text content."""

from __future__ import annotations

import json

import httpx
from agent_framework import tool


@tool
def fetch_page(url: str) -> str:
    """Fetch a web page and extract its main text content."""
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
        return json.dumps({"url": url, "content": text or "(no extractable content)"})
    except httpx.HTTPError as e:
        return json.dumps({"url": url, "error": str(e)})
