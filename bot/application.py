"""
QuantBIST
Telegram Application
"""

from __future__ import annotations

from datetime import time

from telegram.ext import Application, ApplicationBuilder

from bot.handlers import register_handlers
from bot.rotation import rebalance_job
from core.infrastructure.logger import get_logger
from core.infrastructure.settings import require_bot_settings
from core.market.calendar import ISTANBUL

logger = get_logger(__name__)

# After the session is final (18:15) and data providers have the candle.
REBALANCE_CHECK = time(18, 45, tzinfo=ISTANBUL)
WEEKDAYS = (1, 2, 3, 4, 5)  # python-telegram-bot: 0 = Sunday


def schedule_jobs(app: Application, chat_id: int) -> None:
    if app.job_queue is None:
        logger.warning(
            "JobQueue unavailable; monthly rebalance notices are off. "
            "Install python-telegram-bot[job-queue]."
        )
        return

    app.job_queue.run_daily(
        rebalance_job,
        time=REBALANCE_CHECK,
        days=WEEKDAYS,
        chat_id=chat_id,
        name="rebalance",
    )


def build_app() -> Application:
    config = require_bot_settings()

    app = ApplicationBuilder().token(config.bot_token).build()

    register_handlers(app, config.chat_id)
    schedule_jobs(app, config.chat_id)

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
