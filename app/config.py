from __future__ import annotations

import json
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _unpack_secrets() -> None:
    """If APP_SECRETS is set (JSON blob), explode its keys into individual env vars."""
    raw = os.environ.get("APP_SECRETS", "")
    if raw:
        try:
            secrets = json.loads(raw)
            for key, value in secrets.items():
                os.environ.setdefault(key.upper(), value)
        except (json.JSONDecodeError, AttributeError):
            pass


_unpack_secrets()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    slack_webhook_url: str = ""
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Tavily search tuning
    tavily_max_results: int = 3
    tavily_search_depth: str = "advanced"
    news_lookback_days: int = 7
    publisher_search_limit: int = 12

    # Slack
    slack_retries: int = 3
    slack_timeout: int = 20

    # Scheduling
    cron_hour: int = 9
    cron_minute: int = 0

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
