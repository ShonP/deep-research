"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration loaded from .env file and environment variables."""

    azure_api_key: str = ""
    openai_base_url: str = ""
    model: str = "gpt-5.5"
    max_rounds: int = 3
    tavily_api_key: str = ""
    searxng_url: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    azure_whisper_endpoint: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached Settings instance (created on first call)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
