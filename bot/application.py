"""
QuantBIST
Telegram Application
"""

from __future__ import annotations

from telegram.ext import Application, ApplicationBuilder

from bot.handlers import register_handlers
from core.infrastructure.logger import get_logger
from core.infrastructure.settings import require_bot_settings

logger = get_logger(__name__)


def build_app() -> Application:
    config = require_bot_settings()

    app = ApplicationBuilder().token(config.bot_token).build()

    register_handlers(app, config.chat_id)

    return app


def main() -> None:
    config = require_bot_settings()

    app = build_app()

    logger.info(
        "%s v%s Telegram bot started (chat_id=%s).",
        config.app_name,
        config.version,
        config.chat_id,
    )

    app.run_polling()
