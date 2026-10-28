"""
QuantBIST
Telegram Application
"""

from __future__ import annotations

from telegram.ext import Application, ApplicationBuilder

from bot.handlers import register_handlers
from bot.scheduler import schedule_daily_report, schedule_heartbeat, schedule_report_watch
from core.infrastructure.logger import get_logger
from core.infrastructure.settings import require_bot_settings

logger = get_logger(__name__)

# A network error while starting (e.g. DNS not ready right after the PC wakes up) is retried
# with python-telegram-bot's back-off (1 s growing to 30 s): 20 tries is about 7 minutes.
# After that the bot exits and the "QuantBIST Bot" task restarts it. A wrong token is never retried.
BOOTSTRAP_RETRIES = 20


async def _set_menu(app: Application) -> None:
    """Fill Telegram's "Menu" list; a failure only costs the list, never the bot."""

    from telegram import BotCommand

    from bot.handlers import MENU

    try:
        await app.bot.set_my_commands([BotCommand(c, d) for c, d in MENU])
    except Exception:  # noqa: BLE001
        logger.warning("Telegram command menu not set", exc_info=True)


async def _start_up(app: Application) -> None:
    await _set_menu(app)
    _warm_templates()


def _warm_templates() -> None:
    """The template cards in the background: /tara and /tara_sablonlar never wait for them."""

    import threading

    from core.screen import templates

    def run():
        try:
            templates.warm()
        except Exception:  # noqa: BLE001 - only the cards are late
            logger.warning("Template cards not computed", exc_info=True)

    threading.Thread(target=run, name="tara-templates", daemon=True).start()


def build_app() -> Application:
    config = require_bot_settings()

    app = ApplicationBuilder().token(config.bot_token).post_init(_start_up).build()

    register_handlers(app, config.chat_id)
    schedule_daily_report(app)
    schedule_report_watch(app, config.chat_id)
    schedule_heartbeat(app)

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

    app.run_polling(bootstrap_retries=BOOTSTRAP_RETRIES)
