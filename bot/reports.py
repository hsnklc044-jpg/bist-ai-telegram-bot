"""
QuantBIST
Report Commands
"""

from __future__ import annotations

import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from bot.common import reply
from core.infrastructure.logger import get_logger
from core.reports.forward import forward_report
from core.reports.health import health_report
from core.reports.overview import build_overview

logger = get_logger(__name__)


def _build_summary() -> str:
    return build_overview().text


async def summary(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /summary (read-only: stored prices and personal records)."""

    await reply(update, "⏳ Özet hazırlanıyor...")

    text = await asyncio.to_thread(_build_summary)

    await reply(update, text)


async def performance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /performans (live results of recorded views and the paper account)."""

    await reply(update, "⏳ Kayıtlar puanlanıyor...")

    text = await asyncio.to_thread(forward_report)

    await reply(update, text)


async def resend(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /rapor_tekrar [27.10]: send a saved daily report again (nothing is recomputed)."""

    from core.reports.daily import saved_report

    await reply(update, saved_report(" ".join(context.args or []) or None))


async def yearly(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /yil [2026] [gerçek|sanal]: yearly statement of sales, dividends and fees (read-only)."""

    from core.market.calendar import now_istanbul
    from core.reports import annual

    text = await asyncio.to_thread(annual.annual_text, list(context.args or []), now_istanbul().date())
    await reply(update, text)


async def stress_test(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /stres [sanal]: open positions in the worst stored XU100 falls (read-only)."""

    from core.reports import stress

    await reply(update, "⏳ Stres testi hesaplanıyor...")
    await reply(update, await asyncio.to_thread(stress.stress_text, stress.parse_account(list(context.args or []))))


async def price_alarm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /alarm [HİSSE altında|üstünde SEVİYE | sil N]: closing price alarms, checked in the evening report."""

    from core.alerts import levels

    await reply(update, await asyncio.to_thread(levels.command, list(context.args or [])))


async def screen_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara [koşullar | AD]: BIST 100 filtered by the user's indicator conditions (a filter, not advice)."""

    from core.screen import command as screen

    words = list(context.args or [])
    chat = update.effective_chat.id
    query, answer = screen.resolve(words, chat)
    if query is None:
        await reply(update, answer)
        return
    await reply(update, "⏳ Taranıyor (geçmiş karne ile birlikte)...")
    result, trials = await asyncio.to_thread(screen.screen_list, query, chat)
    card_task = asyncio.ensure_future(asyncio.to_thread(screen.C.cached_history, query, screen._history_data))
    try:
        history = await asyncio.wait_for(asyncio.shield(card_task), CARD_WAIT)
    except asyncio.TimeoutError:  # the list goes out now, the card when it is ready
        history = screen.PENDING
        task = asyncio.ensure_future(_card_later(update, chat, card_task))
        _BACKGROUND.add(task)
        task.add_done_callback(_BACKGROUND.discard)
    except Exception:  # noqa: BLE001 - the list still goes out
        logger.exception("History card failed")
        history = None
    text = await asyncio.to_thread(screen.finish, query, chat, result, trials, history)
    await reply(update, text, _screen_buttons(chat))


CARD_WAIT = 60  # seconds the list waits for its history card (Aşama 3, madde 10)
_BACKGROUND: set = set()


async def _card_later(update, chat, card_task) -> None:
    from core.screen import command as screen

    try:
        history = await card_task
    except Exception:  # noqa: BLE001
        logger.exception("History card failed")
        history = None
    await reply(update, screen.card_later(chat, history))


def _screen_buttons(chat_id):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    from core.screen import command as screen

    row = [InlineKeyboardButton("Devam ▶", callback_data="tara:devam")] if screen.has_more(chat_id) else []
    row += [InlineKeyboardButton("Karne", callback_data="tara:karne"),
            InlineKeyboardButton("Kaydet", callback_data="tara:kaydet")]
    return InlineKeyboardMarkup([row])


def _allowed_chat() -> int:
    from core.infrastructure.settings import require_bot_settings

    return require_bot_settings().chat_id


async def screen_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """The buttons under a /tara answer; only the allowed chat is answered (like the commands)."""

    from core.screen import command as screen

    query = update.callback_query
    await query.answer()
    chat = query.message.chat.id
    if chat != _allowed_chat():
        return
    action = (query.data or "").partition(":")[2]
    if action == "devam":
        text = screen.more_text(chat)
        markup = _screen_buttons(chat) if screen.has_more(chat) else None
    elif action == "karne":
        text, markup = screen.card_text(chat), None
    elif action == "kaydet":
        text, markup = screen.save_hint(chat), None
    else:
        return
    for i, part in enumerate(_split(text)):
        await query.message.reply_text(part, **({"reply_markup": markup} if markup and i == len(_split(text)) - 1 else {}))


def _split(text: str) -> list[str]:
    from bot.common import split_message

    return split_message(text)


async def screen_templates(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_sablonlar: the ready-made templates with their cached cards."""

    from core.screen import templates

    await reply(update, await asyncio.to_thread(templates.list_text))


async def screen_fields(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_alanlar: every field with its unit."""

    from core.screen import command as screen

    await reply(update, screen.fields_text())


async def screen_explain(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_aciklama KOD koşullar: each condition's value for one stock."""

    from core.screen import command as screen

    await reply(update, await asyncio.to_thread(screen.explain_text, list(context.args or []),
                                                update.effective_chat.id))


async def screen_more(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_devam: the next 15 rows of the last /tara."""

    from core.screen import command as screen

    chat = update.effective_chat.id
    text = screen.more_text(chat)
    await reply(update, text, _screen_buttons(chat) if screen.has_more(chat) else None)


async def save_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_kaydet AD koşullar."""

    from core.screen import command as screen

    await reply(update, await asyncio.to_thread(screen.save_text, list(context.args or [])))


async def list_screens(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_liste: the saved screens."""

    from core.screen import command as screen

    await reply(update, await asyncio.to_thread(screen.list_saved_text))


async def delete_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_sil AD."""

    from core.screen import command as screen

    await reply(update, await asyncio.to_thread(screen.delete_text, list(context.args or [])))


async def subscribe_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_abone AD."""

    from core.screen import subscriptions

    await reply(update, await asyncio.to_thread(subscriptions.subscribe_text, list(context.args or []),
                                                update.effective_chat.id))


async def screen_subscriptions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_abonelikler."""

    from core.screen import subscriptions

    await reply(update, await asyncio.to_thread(subscriptions.list_text))


async def unsubscribe_screen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_abone_iptal AD."""

    from core.screen import subscriptions

    await reply(update, await asyncio.to_thread(subscriptions.cancel_text, list(context.args or []),
                                                update.effective_chat.id))


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /durum (system health from the records on disk)."""

    await reply(update, await asyncio.to_thread(health_report))
