"""
QuantBIST
Live tracking of the paper signal book during the session (K-65): every hour the open signals'
stocks are downloaded as hourly candles (core.market.hourly), stop and target are checked candle by
candle with the book's own rule (core.signals.store), and the circuit breaker is checked on the
day's closed results. Returns the Telegram lines; the bot job sends them. Yahoo's hourly candles
are delayed (about 15 minutes): "real time" here means the last finished hour.

Never creates the book: without data/signals.db there is nothing to follow.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from core.config.paths import SIGNALS_DB
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)


def _line(s) -> str:
    code = s.symbol.removesuffix(".IS")
    if s.status == "acik":
        return f"🧪 Sanal sinyal {code}: girildi {s.entry_price:.2f} TL (stop {s.stop:.2f}, hedef {s.target:.2f})"
    if s.status == "dolmadi":
        return f"🧪 Sanal sinyal {code}: tavan açılış, giriş olmadı"
    word = {"hedef": "hedefe ulaştı", "stop": "stop oldu", "sure": "süresi doldu"}.get(s.status, s.status)
    return f"🧪 Sanal sinyal {code}: {word} ({s.r * 100:+.2f}%)".replace(".", ",")


def track(today: date, path: Path | str | None = None, load=None) -> list[str]:
    """One hourly pass; the messages for what changed (empty when nothing did)."""

    from core.signals import panic, store

    path = Path(path or SIGNALS_DB)
    if not path.exists() or panic.active():
        return []
    try:
        conn = store.connect(path)
    except Exception as exc:  # noqa: BLE001 - the bot must keep running
        logger.warning("Signal book open failed | %s", exc)
        return []
    try:
        open_ = store.signals(conn, store.OPEN_STATES)
        if not open_:
            return []
        if load is None:
            from core.market.hourly import load_hourly as load
        data = load(sorted({s.symbol for s in open_}))
        changed = store.update(conn, lambda symbol: data.frames.get(symbol), expire=False)
        lines = [_line(s) for s in changed]
        was = store.blocked(conn, today)
        store.check_breaker(conn, today)
        if store.blocked(conn, today) and not was:
            lines.append(f"⛔ Şalter açıldı: bugün kapanan işlemlerin zararı %{store.BREAKER * 100:.0f} sınırına "
                         "ulaştı. Bot bugün tarama ve yeni sinyal üretmiyor.")
        if lines:
            lines.append(store.DISCLAIMER)
        return lines
    except Exception as exc:  # noqa: BLE001 - network, Yahoo or data problems: logged, retried next hour
        logger.warning("Live signal tracking failed | %s", exc)
        return []
    finally:
        conn.close()


def in_session(now: datetime) -> bool:
    """A session day between 10:00 and 19:00 Istanbul (the last hourly candle lands after 18:00)."""

    from core.market.calendar import is_session_day

    return is_session_day(now.date()) and 10 <= now.hour < 19


__all__ = ["in_session", "track"]
