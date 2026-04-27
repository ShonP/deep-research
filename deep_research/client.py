"""OpenAI chat completion client factory."""
from __future__ import annotations

import os

from agent_framework_openai import OpenAIChatCompletionClient

from deep_research.utils import load_env


def get_chat_client() -> OpenAIChatCompletionClient:
    """Create an OpenAIChatCompletionClient configured from environment."""
    load_env()
    return OpenAIChatCompletionClient(
        model="gpt-5.5",
        api_key=os.environ.get("AZURE_API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", ""),
    )
