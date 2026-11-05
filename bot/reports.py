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


LOCKED_TEXT = ("⛔ Şalter açık: bugün kapanan sanal işlemlerin zararı %6 sınırına ulaştı. Bot kendini bugün için "
               "kilitledi; tarama yarın yeniden açılır (DECISIONS K-65). /durum ile defteri görün.")


PANIC_TEXT = "⛔ Panik kilidi açık: tarama durduruldu. Kaldırmak için /devam."


AI_BUSY_TEXT = "⏳ Önceki /tara ai hâlâ çalışıyor; bitince sonucu gelecek."


def _ai_running() -> bool:
    return any(getattr(t, "quantbist_ai", False) and not t.done() for t in _BACKGROUND)


async def _start_screen_ai(update: Update) -> None:
    """/tara ai runs in the background: updates are handled one at a time, so a scan that trains its
    model for minutes kept /panik waiting (03.11.2026 22:48). The handler returns at once."""

    if _ai_running():
        await reply(update, AI_BUSY_TEXT)
        return
    await reply(update, "⏳ BIST 30 taranıyor, adaylar AI katmanına soruluyor (model yoksa ya da 10 günden "
                        "eskiyse önce yeniden eğitilir, birkaç dakika sürebilir). Bu arada /panik ve diğer "
                        "komutlar çalışır...")
    task = asyncio.ensure_future(_screen_ai(update))
    task.quantbist_ai = True
    _BACKGROUND.add(task)
    task.add_done_callback(_BACKGROUND.discard)


async def _screen_ai(update: Update) -> None:
    from core.market.calendar import now_istanbul
    from core.screen import ai

    try:
        messages = await asyncio.to_thread(ai.live, now_istanbul().date())
    except Exception:  # noqa: BLE001 - the user gets an answer, the log the details
        logger.exception("/tara ai failed")
        messages = [("/tara ai şu an çalışmadı (veri ya da model sorunu); ayrıntı logs/quantbist.log içinde.", None)]
    for text, card in messages:
        markup = None
        if card is not None:  # K-67: nothing is entered until the user presses a button
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ İşleme Gir", callback_data=f"sinyal:gir:{card}"),
                                            InlineKeyboardButton("❌ İptal Et", callback_data=f"sinyal:iptal:{card}")]])
        await update.effective_message.reply_text(text, parse_mode="HTML", reply_markup=markup)


SIGNAL_OUTCOME = {
    "bekliyor": "✅ İşleme girildi: ertesi seans açılışında sanal giriş, takip başladı (/durum).",
    "reddedildi": "❌ İptal edildi: sinyal çöpe atıldı.",
    "zaman_asimi": "⌛ Kartın süresi doldu (yalnız kartın günü geçerli); sinyal açılmadı.",
    "kilitli": "⛔ Panik kilidi ya da şalter açık: işlem açılmadı.",
    "nakit_yok": "💰 Sanal kasada boş nakit yok (bugünkü kartlar kullandı): işlem açılmadı; kart hâlâ bugün geçerli.",
    "yok": "Bu kart defterde bulunamadı.",
}


def signal_decision(signal_id: int, enter: bool) -> str:
    from core.market.calendar import now_istanbul
    from core.signals import store

    conn = store.connect()
    try:
        outcome = store.decide(conn, signal_id, enter, now_istanbul().date())
    finally:
        conn.close()
    if outcome.startswith("zaten:"):
        return f"Bu kart için karar zaten verilmiş ({outcome.split(':', 1)[1]})."
    return SIGNAL_OUTCOME[outcome]


async def signal_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """[✅ İşleme Gir] / [❌ İptal Et] under a /tara ai card; the same whitelist as the commands."""

    query = update.callback_query
    await query.answer()
    user = query.from_user.id if query.from_user else None
    if query.message.chat.id != _allowed_chat() or user != _allowed_user():
        return
    parts = (query.data or "").split(":")
    if len(parts) != 3 or parts[1] not in ("gir", "iptal") or not parts[2].isdigit():
        return
    action, signal_id = parts[1], int(parts[2])
    text = await asyncio.to_thread(signal_decision, signal_id, action == "gir")
    try:  # the card shows the decision and loses its buttons
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 - an old card may not be editable; the answer still goes out
        logger.warning("Card buttons could not be removed")
    await query.message.reply_text(text)


async def screen_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara [koşullar | AD]: BIST 100 filtered by the user's indicator conditions (a filter, not advice)."""

    from core.market.calendar import now_istanbul
    from core.screen import command as screen
    from core.signals import store

    if await asyncio.to_thread(store.locked, now_istanbul().date()):
        from core.signals import panic

        await reply(update, PANIC_TEXT if panic.active() else LOCKED_TEXT)
        return
    words = list(context.args or [])
    if [w.lower() for w in words] == ["ai"]:  # the technical trigger + the AI confirmation layer
        await _start_screen_ai(update)
        return
    chat = update.effective_chat.id
    query, answer = screen.resolve(words, chat)
    if query is None:
        await reply(update, answer)
        return
    await reply(update, "⏳ Taranıyor (geçmiş karne ile birlikte)...")
    result, trials = await asyncio.to_thread(screen.screen_list, query, chat)
    card_task = asyncio.ensure_future(asyncio.to_thread(screen.C.cached_history, query, screen._history_data))
    listed = asyncio.Event()  # set once the list went out and its session is written (D12)
    try:
        history = await asyncio.wait_for(asyncio.shield(card_task), CARD_WAIT)
    except asyncio.TimeoutError:  # the list goes out now, the card when it is ready
        history = screen.PENDING
        task = asyncio.ensure_future(_card_later(update, chat, card_task, listed))
        _BACKGROUND.add(task)
        task.add_done_callback(_BACKGROUND.discard)
    except Exception:  # noqa: BLE001 - the list still goes out
        logger.exception("History card failed")
        history = None
    try:
        text = await asyncio.to_thread(screen.finish, query, chat, result, trials, history)
        await reply(update, text, _screen_buttons(chat))
    finally:
        listed.set()


CARD_WAIT = 60  # seconds the list waits for its history card (Aşama 3, madde 10)
_BACKGROUND: set = set()


async def _card_later(update, chat, card_task, listed: asyncio.Event) -> None:
    """The card in its own message, always AFTER the list: computing starts at once, sending
    waits for `listed` (D12: a card that ended first went out as 'Önce /tara ...')."""

    from core.screen import command as screen

    try:
        history = await card_task
    except Exception:  # noqa: BLE001
        logger.exception("History card failed")
        history = None
    await listed.wait()
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


def _allowed_user() -> int:
    from core.infrastructure.settings import settings

    return settings.user_id or _allowed_chat()


async def screen_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """The buttons under a /tara answer; only the allowed chat is answered (like the commands)."""

    from core.screen import command as screen

    query = update.callback_query
    await query.answer()
    chat = query.message.chat.id
    user = query.from_user.id if query.from_user else None
    if chat != _allowed_chat() or user != _allowed_user():  # the same whitelist as the commands
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


async def screen_virtual(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /tara_sanal [AD [kapat]]: the measurement-only virtual book (off by default)."""

    from core.screen import virtual

    await reply(update, await asyncio.to_thread(virtual.command_text, list(context.args or [])))


async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /durum (the short summary) and /durum tum (every check and SLO)."""

    full = [w.lower() for w in (context.args or [])][:1] in (["tum"], ["tüm"])
    await reply(update, await asyncio.to_thread(health_report, full=full))
