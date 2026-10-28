"""
QuantBIST
/tara as text: the list, the eliminated stocks by name, the history card and the fixed last
line. A filter, not advice (DECISIONS K-32, K-33): no "al/sat/öneri/fırsat/hedef fiyat" wording,
the order is alphabetical or by a measured field, never "best".
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path

from core.config.paths import SCREENS_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.screen import card as C
from core.screen import engine, universe
from core.screen.language import ScreenError, normalize, parse

SOURCE = "tara"
MAX_ROWS = 15
MAX_SAVED = 20
DISCLAIMER = "Filtre sonucudur, yatırım önerisi değildir."
SAVE_USAGE = "Kullanım: /tara_kaydet AD koşullar (ör. /tara_kaydet dusuk_rsi rsi<30)"
ORDER_TEXT = {"alfabetik": "alfabetik", "goreli_guc": "göreli güç (XU100'e göre 20 seans, büyükten küçüğe)",
              "hacim": "hacim oranı (büyükten küçüğe)", "rsi": "RSI (küçükten büyüğe)"}
EXAMPLES = ("rsi<30", "ema20>ema50 ve hacim_oran>1,5", "kesti_yukari(ema20,ema50) ve adx>20",
            "kapanis>yuksek_20g ve islem_tl>50 sirala=hacim", "rsi 30..50 ve gg_sira>80 evren=izleme")
_NAME = re.compile(r"[a-z0-9_]{1,20}")


def criterion_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


# --- message --------------------------------------------------------------------------------------


def _line(m: engine.Match) -> str:
    from core.reports.daily import tr

    close, atr = m.close, m.atr
    if close and atr == atr:
        risk = (f"1 ATR %{tr(atr / close * 100, 1)} ({tr(atr, 2)} TL) · "
                f"2 ATR %{tr(2 * atr / close * 100, 1)} ({tr(2 * atr, 2)} TL)")
    else:
        risk = "ATR —"
    return (f"• {m.symbol.removesuffix('.IS')} {tr(close, 2)} | {' · '.join(m.met)} | {risk} | "
            f"likidite {engine.value_text('islem_tl', m.liquidity)}")


def format_result(result: engine.Result, card: dict | None, note: str = "", rows: int = MAX_ROWS) -> str:
    import pandas as pd

    from core.backtest.run import SCREEN_END
    from core.reports.daily import pct

    q = result.query
    lines = [f"🔎 /tara {q.text}"]
    if note:
        lines.append(f"🕒 {note}")
    lines.append(f"{result.day:%d.%m.%Y} kapanışı · {universe.LABELS[q.universe]} · {result.scanned} hisse tarandı · "
                 f"{len(result.matches)} hisse koşulları sağlıyor · sıra: {ORDER_TEXT[q.order]}")
    if result.matches:
        lines += [_line(m) for m in result.matches[:rows]]
        if len(result.matches) > rows:
            lines.append(f"(+{len(result.matches) - rows} hisse daha: /tara_devam)")
    else:
        lines.append("Koşulları sağlayan hisse yok.")
    if result.illiquid:
        names = ", ".join(s.removesuffix(".IS") for s in result.illiquid[:10])
        more = f" +{len(result.illiquid) - 10}" if len(result.illiquid) > 10 else ""
        lines.append(f"Likidite tabanının altında (20 gün ort. < {q.liquidity:g} mn TL, taranmadı): "
                     f"{names}{more}. Kapatmak için likidite=0")
    if result.missing:
        lines.append("Veri eksik (taranmadı): " + "; ".join(f"{s.removesuffix('.IS')} ({why})"
                                                             for s, why in result.missing))
    lines.append("")
    if card is None:
        lines.append("📒 Geçmiş karne hesaplanamadı.")
    else:
        lines.append(f"📒 Geçmiş karne ({C.HISTORY_START[:7]} – {pd.Timestamp(SCREEN_END):%d.%m.%Y}, "
                     "holdout öncesi; o günkü BIST 100 üyeleri; ertesi açılıştan itibaren XU100'e göre fazla getiri):")
        for h in sorted(card):
            mean, hit, n = card[h]
            if n < C.MIN_SAMPLES:
                lines.append(f"  {h} seans: yetersiz örnek ({n})")
            else:
                lines.append(f"  {h} seans: ortalama {pct(mean)}, isabet %{hit * 100:.0f}, örnek {n}")
        lines.append("  Geçmişin özetidir. Koşullar serbestçe denenebildiği için bir kuralın işe yaradığına "
                     "kanıt sayılmaz (araştırma programı dışında; örnekler zaman içinde çakışır).")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


# --- saved screens (CSV until Aşama 4) ------------------------------------------------------------

SAVED_COLUMNS = ("at", "name", "criteria")


def load_saved(path: Path | None = None) -> dict[str, str]:
    """name -> criteria; a later row for the same name replaces the earlier one."""

    return {row["name"]: row["criteria"] for _, row in read_rows(Path(path or SCREENS_FILE), SAVED_COLUMNS)}


def save_text(words: list[str], path: Path | None = None, now: datetime | None = None) -> str:
    from core.market.calendar import now_istanbul
    from core.screen import fields as F

    path = Path(path or SCREENS_FILE)
    if len(words) < 2:
        return SAVE_USAGE
    name = normalize(words[0])
    if not _NAME.fullmatch(name):
        return "⚠️ Ad yalnız küçük harf, rakam ve _ olabilir (en fazla 20). " + SAVE_USAGE
    if name in F.FIELDS:
        return f"⚠️ Ad bir alan adı olamaz ('{name}'). " + SAVE_USAGE
    try:
        query = parse(" ".join(words[1:]))
    except ScreenError as exc:
        return str(exc)
    saved = load_saved(path)
    if name not in saved and len(saved) >= MAX_SAVED:
        return f"⚠️ En fazla {MAX_SAVED} kayıtlı tarama olabilir."
    criteria = query.text + (f" sirala={query.order}" if query.order != "alfabetik" else "")
    fh, new_file = open_append(path)
    with fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(SAVED_COLUMNS)
        writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), name, criteria])
    return f"💾 Kaydedildi: {name}: {criteria}\nÇalıştırmak için: /tara {name}"


# --- the command ----------------------------------------------------------------------------------


def help_text(saved: dict[str, str]) -> str:
    lines = ["🔎 /tara: hisseleri kendi gösterge koşullarınla filtrele (yan yana yazılan koşulların hepsi sağlanmalı).",
             "Örnekler:"] + [f"  /tara {e}" for e in EXAMPLES]
    lines += ["Karşılaştırma < > <= >=, aralık rsi 30..50, kesişim kesti_yukari(a,b) / kesti_asagi(a,b), "
              "pencere son(5, ...), ve / veya / değil ve parantez.",
              "Seçenekler: evren=bist100|izleme · likidite=10 (mn TL; 0 kapalı) · sirala=alfabetik|goreli_guc|hacim|rsi",
              "Tüm alanlar: /tara_alanlar · Kayıt: /tara_kaydet AD koşullar, sonra /tara AD"]
    if saved:
        lines += ["Kayıtlı taramaların:"] + [f"  {k}: {v}" for k, v in sorted(saved.items())]
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _live(symbols: list[str]):
    from core.market.universe import BENCHMARK
    from core.reports.daily import adjusted_bars

    return {s: adjusted_bars(s) for s in symbols}, adjusted_bars(BENCHMARK)


_HISTORY: dict = {}


def _history_data():
    """Research-period prices of every BIST 100 member since 2022 and their membership; cut at
    SCREEN_END by load_frames. Kept for the day."""

    import pandas as pd

    from core.backtest.run import load_frames
    from core.market.calendar import now_istanbul
    from core.market.membership import ever_members, membership_panel
    from core.market.universe import BENCHMARK

    key = now_istanbul().date()
    if key not in _HISTORY:
        frames = {s: df for s, df in load_frames(ever_members()).items() if not df.empty}
        index = pd.DatetimeIndex(sorted(set().union(*(df.index for df in frames.values()))))
        _HISTORY.clear()
        _HISTORY[key] = (frames, load_frames([BENCHMARK])[BENCHMARK], membership_panel(index, list(frames)))
    return _HISTORY[key]


def screen_text(words: list[str], chat_id=None, live=None, history_data=None, signal_path=None, saved_path=None,
                now: datetime | None = None, suspects=None) -> str:
    from core.infrastructure.logger import get_logger
    from core.market.calendar import now_istanbul
    from core.signals_log import log_signal

    now = now or now_istanbul()
    text = " ".join(words).strip()
    try:
        saved = load_saved(saved_path)
    except Exception:  # noqa: BLE001 - a damaged saved file must not stop a plain /tara
        saved = {}
    if not text:
        return help_text(saved)
    key = normalize(text)
    if key in saved:
        text = saved[key]
    try:
        query = parse(text)
        symbols = universe.symbols(query.universe, chat_id)
    except ScreenError as exc:
        return str(exc)

    frames, bench = (live or _live)(symbols)
    found = universe.suspects() if suspects is None else suspects
    result = engine.run(query, frames, bench, found)
    try:
        data = (history_data or _history_data)()
        history = C.history(query, *data) if data is not None else None
    except Exception:  # noqa: BLE001 - the list still goes out
        get_logger(__name__).exception("History card failed")
        history = None
    details = f"kriter={query.text};ozet={criterion_hash(query.text)}"
    for m in result.matches:  # live measurement: every match, not only the rows shown
        log_signal(SOURCE, m.symbol, None, query.text, m.day, m.close, details=details, path=signal_path, now=now)
    return format_result(result, history, engine.time_note(result.day, now))


__all__ = ["DISCLAIMER", "SOURCE", "criterion_hash", "format_result", "help_text", "load_saved", "save_text",
           "screen_text"]
