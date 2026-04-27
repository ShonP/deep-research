"""Lightweight OpenAI client wrapper for Azure-compatible endpoints."""
from __future__ import annotations

import os

from openai import OpenAI


def get_client() -> OpenAI:
    """Create an OpenAI client configured from environment variables."""
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("AZURE_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    if not base_url:
        raise RuntimeError(
            "OPENAI_BASE_URL must be set (e.g. https://your-endpoint.openai.azure.com/openai/v1/)"
        )
    if not api_key:
        raise RuntimeError("AZURE_API_KEY or OPENAI_API_KEY must be set")
    return OpenAI(base_url=base_url, api_key=api_key)


def chat(
    system_prompt: str,
    user_message: str,
    *,
    model: str = "gpt-4o",
    temperature: float = 0.7,
) -> str:
    """Simple single-turn chat completion (no tools)."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content or ""
