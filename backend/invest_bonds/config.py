from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ConfigError(RuntimeError):
    """Raised when required local configuration is missing."""


class Settings(BaseModel):
    invest_token: str = Field(min_length=1)


def load_settings(env_path: str | Path = ".env") -> Settings:
    load_dotenv(env_path)
    token = os.getenv("INVEST_TOKEN", "").strip()
    if not token:
        raise ConfigError("INVEST_TOKEN is missing. Add it to .env.")
    return Settings(invest_token=token)
