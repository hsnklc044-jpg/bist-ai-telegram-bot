"""
QuantBIST
Application Settings

Values come from environment variables or a `.env` file in the
project root. Missing values do not crash imports; components that
need them (the Telegram bot) call `require_bot_settings()`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from core import __version__
from core.config.paths import ROOT_DIR
from core.infrastructure.exceptions import ConfigurationError

load_dotenv(ROOT_DIR / ".env")


def _int_env(name: str, default: int = 0) -> int:
    raw = os.getenv(name, "").strip()

    if not raw:
        return default

    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(
            f"{name} must be an integer, got {raw!r}."
        ) from exc


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()

    if not raw:
        return default

    return raw in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    """Application configuration."""

    bot_token: str
    chat_id: int
    debug: bool = False
    app_name: str = "QuantBIST"
    version: str = __version__


def load_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", "").strip(),
        chat_id=_int_env("CHAT_ID"),
        debug=_bool_env("QUANTBIST_DEBUG"),
    )


settings = load_settings()


def require_bot_settings() -> Settings:
    """Fail fast with a clear message when the bot is not configured."""

    if not settings.bot_token:
        raise ConfigurationError(
            "BOT_TOKEN bulunamadı. .env.example dosyasını .env olarak "
            "kopyalayıp doldurun."
        )

    if not settings.chat_id:
        raise ConfigurationError(
            "CHAT_ID bulunamadı. Bot sadece bu sohbetten gelen komutlara "
            "cevap verir; .env dosyasına ekleyin."
        )

    return settings


__all__ = [
    "Settings",
    "settings",
    "load_settings",
    "require_bot_settings",
]
