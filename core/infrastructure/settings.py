"""
QuantBIST RC4
Application Settings
"""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application configuration."""

    bot_token: str
    chat_id: int
    app_name: str = "QuantBIST RC4"
    version: str = "4.0.0"
    debug: bool = False


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", ""),
    chat_id=int(os.getenv("CHAT_ID", "0")),
)

if not settings.bot_token:
    raise RuntimeError(
        "BOT_TOKEN .env dosyasında bulunamadı."
    )
