"""
QuantBIST
One-shot Telegram notices, for schedulers without a running bot
(GitHub Actions, cron).

    python -m bot.notify             # rebalance notice when due, weekly report on Fridays
    python -m bot.notify --report    # send the /rotasyon report now
    python -m bot.notify --dry-run   # print instead of sending

Run it once per weekday after 18:15 Istanbul time.
"""

from __future__ import annotations

import argparse
import asyncio

from telegram import Bot

from bot.common import split_message
from core.backtest.runner import load_dataset
from core.infrastructure.logger import get_logger
from core.infrastructure.settings import require_bot_settings
from core.market.calendar import now_istanbul
from core.rotation.service import build_report, check_rebalance, format_report

logger = get_logger(__name__)

FRIDAY = 4


def collect(report_now: bool = False) -> list[str]:
    """Messages due right now."""

    data = load_dataset()

    if report_now:
        return [format_report(build_report(data))]

    messages = []

    notice = check_rebalance(data)
    if notice:
        messages.append(notice)

    today = now_istanbul().date()

    if today.weekday() == FRIDAY:
        report = build_report(data)

        if report.as_of == today:
            messages.append(format_report(report))

    return messages


async def send(messages: list[str]) -> None:
    config = require_bot_settings()

    async with Bot(config.bot_token) as bot:
        for message in messages:
            for part in split_message(message):
                await bot.send_message(chat_id=config.chat_id, text=part)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Send due QuantBIST notices to Telegram.")
    parser.add_argument("--report", action="store_true", help="rotasyon raporunu şimdi gönder")
    parser.add_argument("--dry-run", action="store_true", help="göndermeden yazdır")
    args = parser.parse_args(argv)

    if not args.dry_run:
        require_bot_settings()  # fail before downloading prices

    messages = collect(report_now=args.report)

    if not messages:
        print("Gönderilecek bildirim yok.")
        return

    if args.dry_run:
        print("\n\n---\n\n".join(messages))
        return

    asyncio.run(send(messages))
    print(f"{len(messages)} bildirim gönderildi.")


if __name__ == "__main__":
    main()
