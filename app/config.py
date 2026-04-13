from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _unpack_secrets() -> None:
    """If APP_SECRETS is set (JSON blob), explode its keys into individual env vars."""
    raw = os.environ.get("APP_SECRETS", "")
    if raw:
        try:
            secrets = json.loads(raw)
            for key, value in secrets.items():
                if isinstance(value, str):
                    os.environ.setdefault(key.upper(), value)
        except (json.JSONDecodeError, AttributeError):
            pass

    # If GOOGLE_CREDENTIALS_JSON is set, write it to a temp file
    # so gspread can read it as a keyfile path
    gcreds = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    if gcreds and not os.environ.get("GOOGLE_CREDENTIALS_FILE"):
        try:
            creds_dict = json.loads(gcreds)
            fd, path = tempfile.mkstemp(suffix=".json", prefix="gcreds_")
            with os.fdopen(fd, "w") as f:
                json.dump(creds_dict, f)
            os.environ["GOOGLE_CREDENTIALS_FILE"] = path
        except (json.JSONDecodeError, OSError):
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
    gemini_model: str = "gemini-2.5-flash-lite"

    # Google Sheets
    google_credentials_json: str = ""
    google_credentials_file: str = ""
    google_sheet_name: str = "Joveo Intel Logs"

    # Tavily search tuning
    tavily_max_results: int = 3
    tavily_search_depth: str = "advanced"
    news_lookback_days: int = 7
    publisher_search_limit: int = 12

    # Slack
    slack_retries: int = 3
    slack_timeout: int = 20

    log_level: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
