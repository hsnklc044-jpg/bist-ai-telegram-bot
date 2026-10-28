"""
QuantBIST
/tara: BIST 100 filtered by the user's own indicator conditions. A filter, not advice: the
list says which stocks meet the conditions today, nothing about what to do with them.

    /tara rsi<30 ema20>ema50          conditions joined by AND (space, "ve" or ", ")
    /tara kapanis>ema50 sıra:güç       order by relative strength (default: alphabetical)
    /tara_kaydet dusuk_rsi rsi<30      saved screens: data/screens.csv (append-only, backed up)

Under every list a history card: the same conditions on 2023-08-01 – 30.10.2026 (the research
period; the holdout from 02.11.2026 is never used), XU100-relative return 5 and 20 sessions
later. It describes the past; it is not a tested rule (no research budget, no pre-registration).
Every match is recorded in the live measurement (signal_log, source "tara") and measured by
/performans per criterion.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from core.config.paths import SCREENS_FILE
from core.infrastructure.csvfiles import open_append, read_rows

SOURCE = "tara"
FIELDS = {
    "rsi": "RSI (14)",
    "ema20": "20 günlük üssel ortalama",
    "ema50": "50 günlük üssel ortalama",
    "macd": "MACD (12, 26)",
    "macd_sinyal": "MACD sinyal çizgisi (9)",
    "hacim": "bugünkü hacim / önceki 20 gün ortalaması (1,5 = %50 fazla)",
    "atr_yuzde": "ATR (14) / kapanış, %",
    "getiri_5g": "son 5 seans getiri, %",
    "getiri_20g": "son 20 seans getiri, %",
    "goreli_guc": "son 20 seansta XU100'e göre fark, puan",
    "kapanis": "son kapanış, TL",
}
MAX_CONDITIONS = 5
MAX_ROWS = 15
MAX_SAVED = 20
MIN_SAMPLES = 30
HORIZONS = (5, 20)
HISTORY_START = "2023-08-01"
DISCLAIMER = "Filtre sonucudur, yatırım önerisi değildir."
EXAMPLE = "Örnek: /tara rsi<30 ema20>ema50"
SAVE_USAGE = "Kullanım: /tara_kaydet AD koşullar (ör. /tara_kaydet dusuk_rsi rsi<30)"
_ASCII = str.maketrans("ıİğĞüÜşŞöÖçÇ", "iIgGuUsSoOcC")
_NAME = re.compile(r"[a-z0-9_]{1,20}")


class ScreenError(ValueError):
    """A condition that cannot be read; the message is shown to the user as it is."""

    def __init__(self, message: str):
        super().__init__(f"⚠️ {message}\n{EXAMPLE}")


def _number(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _fmt(x: float) -> str:
    return f"{x:g}"


@dataclass(frozen=True)
class Condition:
    left: str
    op: str
    right: str | float

    @property
    def text(self) -> str:
        return f"{self.left}{self.op}{self.right if isinstance(self.right, str) else _fmt(self.right)}"

    def holds(self, row) -> bool:
        left = row[self.left]
        right = row[self.right] if isinstance(self.right, str) else self.right
        if pd.isna(left) or pd.isna(right):
            return False
        return bool(left < right) if self.op == "<" else bool(left > right)

    def mask(self, table: pd.DataFrame) -> pd.Series:
        right = table[self.right] if isinstance(self.right, str) else self.right
        return (table[self.left] < right) if self.op == "<" else (table[self.left] > right)


@dataclass(frozen=True)
class Screen:
    conditions: tuple[Condition, ...]
    order: str = "alfabetik"

    @property
    def text(self) -> str:
        return " ".join(c.text for c in self.conditions)


def _normal(text: str) -> str:
    text = text.replace("İ", "i").replace("I", "ı").lower().translate(_ASCII)
    text = re.sub(r"(?<!\d),|,(?!\d)", " ", text)  # "1,5" stays a number; other commas separate
    return re.sub(r"\s*([<>=])\s*", r"\1", text)


def parse(text: str) -> Screen:
    conditions, order = [], "alfabetik"
    for token in _normal(text).split():
        if token == "ve":
            continue
        if token.startswith("sira:"):
            order = {"guc": "guc", "alfabetik": "alfabetik"}.get(token[5:], "")
            if not order:
                raise ScreenError("Sıralama 'alfabetik' ya da 'güç' olabilir (ör. sıra:güç).")
            continue
        if "=" in token:
            raise ScreenError(f"'{token}': Karşılaştırma için < ya da > kullanın (= desteklenmiyor).")
        found = re.fullmatch(r"([^<>]*)([<>])([^<>]*)", token)
        if not found:
            raise ScreenError(f"'{token}' bir koşul değil. Karşılaştırma için < ya da > kullanın.")
        left, op, right = found.groups()
        if not left or not right:
            raise ScreenError(f"'{token}': koşulun bir tarafı eksik.")
        if left not in FIELDS:
            if _number(left) is not None:
                raise ScreenError(f"'{token}': karşılaştırmanın solunda bir alan olmalı (ör. rsi<30).")
            raise ScreenError(f"Bilinmeyen alan '{left}'. Alanlar: {', '.join(FIELDS)}.")
        value: str | float | None = right if right in FIELDS else _number(right)
        if value is None:
            raise ScreenError(f"'{right}' bir sayı ya da alan değil (ör. rsi<30, ema20>ema50).")
        conditions.append(Condition(left, op, value))
    if not conditions:
        raise ScreenError("En az bir koşul yazın.")
    if len(conditions) > MAX_CONDITIONS:
        raise ScreenError(f"Bir taramada en fazla {MAX_CONDITIONS} koşul olabilir.")
    return Screen(tuple(conditions), order)


# --- indicators -----------------------------------------------------------------------------------


def indicators(df: pd.DataFrame, bench_close: pd.Series) -> pd.DataFrame:
    """Every field for every candle (the same indicators and windows as the technical score),
    plus atr (TL) and likidite (20-session mean TL turnover)."""

    from ta.momentum import RSIIndicator
    from ta.trend import MACD, EMAIndicator
    from ta.volatility import AverageTrueRange

    from core.strategy.score import volume_ratio_series

    close = df["close"]
    macd = MACD(close)
    out = pd.DataFrame(index=df.index)
    out["rsi"] = RSIIndicator(close, window=14).rsi()
    out["ema20"] = EMAIndicator(close, window=20).ema_indicator()
    out["ema50"] = EMAIndicator(close, window=50).ema_indicator()
    out["macd"] = macd.macd()
    out["macd_sinyal"] = macd.macd_signal()
    out["hacim"] = volume_ratio_series(df["volume"])
    out["atr"] = AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range()
    out["atr_yuzde"] = out["atr"] / close * 100
    out["getiri_5g"] = (close / close.shift(5) - 1) * 100
    out["getiri_20g"] = (close / close.shift(20) - 1) * 100
    bench = bench_close.reindex(df.index)
    out["goreli_guc"] = out["getiri_20g"] - (bench / bench.shift(20) - 1) * 100
    out["kapanis"] = close
    out["likidite"] = (close * df["volume"]).rolling(20).mean()
    return out


# --- today's list ---------------------------------------------------------------------------------


@dataclass
class Match:
    symbol: str
    day: date
    close: float
    atr: float
    likidite: float
    values: dict = field(default_factory=dict)


def run(screen: Screen, frames: dict[str, pd.DataFrame], bench: pd.DataFrame) -> list[Match]:
    """Stocks meeting every condition on the latest session (XU100's last candle)."""

    latest = bench.index[-1]
    found = []
    for symbol, df in frames.items():
        if df.empty or df.index[-1] != latest:
            continue
        row = indicators(df, bench["close"]).iloc[-1]
        if all(c.holds(row) for c in screen.conditions):
            found.append(Match(symbol, latest.date(), float(row["kapanis"]), float(row["atr"]),
                               float(row["likidite"]), {k: float(row[k]) for k in FIELDS}))
    if screen.order == "guc":
        return sorted(found, key=lambda m: -m.values["goreli_guc"] if m.values["goreli_guc"] == m.values["goreli_guc"]
                      else float("inf"))
    return sorted(found, key=lambda m: m.symbol)


# --- history card ---------------------------------------------------------------------------------


def history(screen: Screen, frames: dict[str, pd.DataFrame], bench: pd.DataFrame,
            eligible: pd.DataFrame | None = None, horizons=HORIZONS) -> dict[int, tuple]:
    """{horizon: (mean excess, hit rate, samples)} on HISTORY_START – SCREEN_END. Buy at the next
    open, sell at the close `horizon` sessions later, minus XU100 over the same sessions. The data
    is cut at SCREEN_END here as well (load_frames already does): the holdout is never read."""

    from core.backtest.run import SCREEN_END

    bench = bench.loc[:SCREEN_END]
    collected: dict[int, list[pd.Series]] = {h: [] for h in horizons}
    for symbol, df in frames.items():
        df = df.loc[:SCREEN_END]
        if df.empty:
            continue
        table = indicators(df, bench["close"])
        mask = pd.Series(True, index=table.index)
        for c in screen.conditions:
            mask &= c.mask(table).fillna(False)
        mask &= table.index >= pd.Timestamp(HISTORY_START)
        if eligible is not None:
            if symbol not in eligible.columns:
                continue
            ok = eligible[symbol].reindex(table.index).ffill().fillna(False).astype(bool)
            mask &= ok
        if not mask.any():
            continue
        b = bench.reindex(df.index)
        entry, bench_entry = df["open"].shift(-1), b["open"].shift(-1)
        for h in horizons:
            excess = (df["close"].shift(-h) / entry - 1) - (b["close"].shift(-h) / bench_entry - 1)
            collected[h].append(excess[mask].dropna())
    card = {}
    for h, parts in collected.items():
        values = pd.concat(parts) if parts else pd.Series(dtype=float)
        n = int(len(values))
        card[h] = (float(values.mean()), float((values > 0).mean()), n) if n else (None, None, 0)
    return card


# --- message --------------------------------------------------------------------------------------


def _money(x: float) -> str:
    from core.reports.daily import tr

    if x != x:
        return "—"
    if x >= 1e9:
        return f"{tr(x / 1e9, 1)} mlr TL"
    if x >= 1e6:
        return f"{tr(x / 1e6, 0)} mn TL"
    return f"{tr(x, 0)} TL"


def _value(x: float) -> str:
    from core.reports.daily import tr

    return tr(x, 2) if abs(x) < 1000 else tr(x, 0)


def _line(m: Match, screen: Screen) -> str:
    from core.reports.daily import tr

    met = []
    for c in screen.conditions:
        right = f"{c.right} {_value(m.values[c.right])}" if isinstance(c.right, str) else _value(c.right)
        met.append(f"{c.left} {_value(m.values[c.left])}{c.op}{right}")
    risk = f"1 ATR {tr(m.atr, 2)} TL (%{tr(m.atr / m.close * 100, 1)})" if m.close else "1 ATR —"
    return (f"• {m.symbol.removesuffix('.IS')} {tr(m.close, 2)} TL | {'; '.join(met)} | {risk} | "
            f"20g ort. işlem {_money(m.likidite)}")


def format_result(screen: Screen, matches: list[Match], card: dict | None) -> str:
    from core.backtest.run import SCREEN_END
    from core.reports.daily import pct

    order = "göreli güç (XU100'e göre, büyükten küçüğe)" if screen.order == "guc" else "alfabetik"
    lines = [f"🔎 /tara {screen.text}"]
    if matches:
        lines.append(f"{matches[0].day:%d.%m.%Y} kapanışı · BIST 100 · {len(matches)} hisse koşulları sağlıyor · "
                     f"sıra: {order}")
        lines += [_line(m, screen) for m in matches[:MAX_ROWS]]
        if len(matches) > MAX_ROWS:
            lines.append(f"(+{len(matches) - MAX_ROWS} hisse daha; liste {MAX_ROWS} satırla sınırlı, "
                         "koşulları daraltın)")
    else:
        lines.append("Koşulları sağlayan hisse yok.")
    lines.append("")
    end = pd.Timestamp(SCREEN_END)
    if card is None:
        lines.append("📒 Geçmiş karne hesaplanamadı.")
    else:
        lines.append(f"📒 Geçmiş karne ({HISTORY_START[:7]} – {end:%d.%m.%Y}, holdout öncesi; o günkü BIST 100 "
                     "üyeleri; ertesi açılıştan itibaren XU100'e göre fazla getiri):")
        for h in sorted(card):
            mean, hit, n = card[h]
            if n < MIN_SAMPLES:
                lines.append(f"  {h} seans: yetersiz örnek ({n})")
            else:
                lines.append(f"  {h} seans: ortalama {pct(mean)}, isabet %{hit * 100:.0f}, örnek {n}")
        lines.append("  Geçmişin özetidir. Koşullar serbestçe denenebildiği için bir kuralın işe yaradığına "
                     "kanıt sayılmaz (araştırma programı dışında; örnekler zaman içinde çakışır).")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


# --- saved screens --------------------------------------------------------------------------------

SAVED_COLUMNS = ("at", "name", "criteria")


def load_saved(path: Path | None = None) -> dict[str, str]:
    """name -> criteria; a later row for the same name replaces the earlier one."""

    return {row["name"]: row["criteria"] for _, row in read_rows(Path(path or SCREENS_FILE), SAVED_COLUMNS)}


def save_text(words: list[str], path: Path | None = None, now: datetime | None = None) -> str:
    """The /tara_kaydet answer (and the row it appends)."""

    from core.market.calendar import now_istanbul

    path = Path(path or SCREENS_FILE)
    if len(words) < 2:
        return SAVE_USAGE
    name = words[0].lower().translate(_ASCII)
    if not _NAME.fullmatch(name):
        return "⚠️ Ad yalnız küçük harf, rakam ve _ olabilir (en fazla 20). " + SAVE_USAGE
    if name in FIELDS:
        return f"⚠️ Ad bir alan adı olamaz ('{name}'). " + SAVE_USAGE
    try:
        screen = parse(" ".join(words[1:]))
    except ScreenError as exc:
        return str(exc)
    saved = load_saved(path)
    if name not in saved and len(saved) >= MAX_SAVED:
        return f"⚠️ En fazla {MAX_SAVED} kayıtlı tarama olabilir."
    criteria = screen.text + (" sıra:güç" if screen.order == "guc" else "")
    fh, new_file = open_append(path)
    with fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(SAVED_COLUMNS)
        writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), name, criteria])
    return f"💾 Kaydedildi: {name}: {criteria}\nÇalıştırmak için: /tara {name}"


# --- the command ----------------------------------------------------------------------------------


def _help(saved: dict[str, str]) -> str:
    lines = ["🔎 /tara: BIST 100'ü kendi koşullarınla filtrele (koşulların hepsi sağlanmalı).", "Örnekler:",
             "  /tara rsi<30", "  /tara ema20>ema50 hacim>1,5", "  /tara kapanis>ema50 goreli_guc>0 sıra:güç",
             "  /tara macd>macd_sinyal atr_yuzde<3", "Alanlar:"]
    lines += [f"  {k}: {v}" for k, v in FIELDS.items()]
    lines.append(f"Operatör: < ya da >; alanlar birbiriyle de karşılaştırılır (ema20>ema50). En fazla {MAX_CONDITIONS} "
                 "koşul. Ondalık virgülle: 1,5.")
    lines.append("Kayıtlı tarama: /tara_kaydet AD koşullar, sonra /tara AD")
    if saved:
        lines += ["Kayıtlı taramaların:"] + [f"  {k}: {v}" for k, v in sorted(saved.items())]
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _live_data():
    from core.market.universe import BENCHMARK, load_universe
    from core.reports.daily import adjusted_bars

    return {s: adjusted_bars(s) for s in load_universe()}, adjusted_bars(BENCHMARK)


_HISTORY: dict = {}


def _history_data():
    """Research-period prices of every BIST 100 member since 2022 and their membership; cut at
    SCREEN_END by load_frames. Kept for the day (the bot restarts daily)."""

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


def screen_text(words: list[str], live=None, history_data=None, signal_path=None, saved_path=None,
                now: datetime | None = None) -> str:
    from core.infrastructure.logger import get_logger
    from core.signals_log import log_signal

    text = " ".join(words).strip()
    try:
        saved = load_saved(saved_path)
    except Exception:  # noqa: BLE001 - a damaged saved file must not stop a plain /tara
        saved = {}
    if not text:
        return _help(saved)
    key = text.lower().translate(_ASCII)
    if key in saved:
        text = saved[key]
    try:
        screen = parse(text)
    except ScreenError as exc:
        return str(exc)

    frames, bench = (live or _live_data)()
    matches = run(screen, frames, bench)
    try:
        data = (history_data or _history_data)()
        card = history(screen, *data) if data is not None else None
    except Exception:  # noqa: BLE001 - the list still goes out
        get_logger(__name__).exception("History card failed")
        card = None
    for m in matches:  # live measurement: every match, not only the rows shown
        log_signal(SOURCE, m.symbol, None, screen.text, m.day, m.close, details=f"kriter={screen.text}",
                   path=signal_path, now=now)
    return format_result(screen, matches, card)


__all__ = ["DISCLAIMER", "FIELDS", "Condition", "Match", "Screen", "ScreenError", "history", "indicators",
           "load_saved", "parse", "run", "save_text", "screen_text"]
