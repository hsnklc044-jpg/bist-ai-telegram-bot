"""
QuantBIST RC4
Telegram Application
"""

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
)

from core.infrastructure.settings import settings
from bot.handlers import register_handlers


def build_app() -> Application:
    app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .build()
    )

    return app


def main() -> None:
    app = build_app()

    register_handlers(app)

    print(
        f"🚀 {settings.app_name} v{settings.version}"
    )

    app.run_polling()