"""Lightweight OpenAI client wrapper for Azure-compatible endpoints."""
from __future__ import annotations

import os

from openai import OpenAI

from deep_research.log import log


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
    model: str = "gpt-5.5",
    temperature: float | None = None,
    reasoning_effort: str = "medium",
) -> str:
    """Simple single-turn chat completion (no tools)."""
    client = get_client()
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    # Reasoning models use reasoning_effort, not temperature
    if model.startswith(("gpt-5", "o1", "o3", "o4")):
        kwargs["reasoning_effort"] = reasoning_effort
        kwargs["max_completion_tokens"] = 16384
    else:
        kwargs["temperature"] = temperature if temperature is not None else 0.7
    response = client.chat.completions.create(**kwargs)
    usage = response.usage
    if usage:
        log.debug("LLM call: model=%s tokens=%d (prompt=%d, completion=%d)",
                  model, usage.total_tokens, usage.prompt_tokens, usage.completion_tokens)
    return response.choices[0].message.content or ""
