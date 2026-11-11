"""
QuantBIST
Telegram Application
"""

from __future__ import annotations

from telegram.ext import Application, ApplicationBuilder, ExtBot

from bot.handlers import register_handlers
from bot.scheduler import (
    schedule_backup_catch_up,
    schedule_daily_report,
    schedule_fundamentals_inbox,
    schedule_heartbeat,
    schedule_macro_refresh,
    schedule_morning_screens,
    schedule_official_prices,
    schedule_otonom_summary,
    schedule_portfolio_health,
    schedule_report_watch,
    schedule_signal_tracking,
    schedule_weekly_summary,
)
from core.infrastructure.logger import get_logger
from core.infrastructure.settings import require_bot_settings

logger = get_logger(__name__)


class RecordingBot(ExtBot):
    """Every message the bot sends (replies and job messages) is copied to logs/telegram_giden.jsonl with its
    source (core.infrastructure.outbox; the user's 10.11.2026 request). A failed send is recorded too."""

    async def send_message(self, chat_id, text, *args, **kwargs):
        from core.infrastructure import outbox
        from core.market import trust

        text = trust.note_outgoing(text)  # level 3 data: one line under the title (J, 11.11.2026)
        try:
            message = await super().send_message(chat_id, text, *args, **kwargs)
        except Exception:
            outbox.record(outbox.current_source(), text, False)
            raise
        outbox.record(outbox.current_source(), text, True)
        return message


def _bot(token: str) -> RecordingBot:
    """The same request settings ApplicationBuilder uses by default (256 connections; 1 for polling)."""

    from telegram.request import HTTPXRequest

    return RecordingBot(token=token, request=HTTPXRequest(connection_pool_size=256),
                        get_updates_request=HTTPXRequest(connection_pool_size=1))

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

    app = ApplicationBuilder().bot(_bot(config.bot_token)).post_init(_start_up).build()

    register_handlers(app, config.chat_id, config.user_id)
    schedule_daily_report(app)
    schedule_report_watch(app, config.chat_id)
    schedule_heartbeat(app)
    schedule_macro_refresh(app)
    schedule_backup_catch_up(app, config.chat_id)
    schedule_fundamentals_inbox(app, config.chat_id)
    schedule_portfolio_health(app, config.chat_id)
    schedule_weekly_summary(app, config.chat_id)
    schedule_otonom_summary(app, config.chat_id)
    schedule_morning_screens(app, config.chat_id)
    schedule_signal_tracking(app, config.chat_id)
    schedule_official_prices(app, config.chat_id)

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
