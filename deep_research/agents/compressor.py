"""Compressor agent: deduplicates and compresses research findings."""

from __future__ import annotations

import json

from agent_framework._agents import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import llm_call_logging

SYSTEM_PROMPT = """\
You are a research findings compressor. You take raw research findings and:
1. Remove duplicate or overlapping information
2. Merge related findings into cohesive summaries
3. Preserve ALL key insights, citations, and source URLs
4. Keep specific data, code examples, and concrete evidence
5. Maintain source attribution for every claim

Output ONLY valid JSON (no markdown fences):
{
  "compressed": [
    {
      "topic": "merged topic title",
      "summary": "compressed summary preserving key details and URLs",
      "key_sources": ["url1", "url2"]
    }
  ],
  "notes": ["important cross-cutting insight 1"]
}

Rules:
- Reduce volume by 30-50% while preserving ALL unique information
- Never drop source URLs or citations
- Merge findings about the same subtopic
- Keep code snippets and specific data intact
"""


async def compress_findings(findings: list[dict], query: str) -> tuple[list[dict], list[str]]:
    """Compress and deduplicate findings. Returns (compressed_findings, notes)."""
    if len(findings) <= 2:
        return findings, []

    findings_text = json.dumps(findings, indent=2)
    agent = Agent(
        client=get_chat_client(),
        name="findings-compressor",
        instructions=SYSTEM_PROMPT,
        middleware=[llm_call_logging],
    )
    prompt = (
        f"Research query: {query}\n\n"
        f"Raw findings ({len(findings)} total):\n{findings_text}\n\n"
        "Compress and deduplicate these findings."
    )
    response = await agent.run(prompt)
    return _parse_compressed(response.text, findings)


def _parse_compressed(
    text: str,
    fallback: list[dict],
) -> tuple[list[dict], list[str]]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        data = json.loads(text.strip())
        compressed = data.get("compressed", [])
        notes = data.get("notes", [])
        return (compressed, notes) if compressed else (fallback, notes)
    except (json.JSONDecodeError, KeyError):
        return fallback, []
