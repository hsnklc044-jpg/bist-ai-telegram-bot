"""
QuantBIST
/tablo: one line per stock with RSI, the close against a set of EMAs, the volume of the last five sessions
against the usual volume and the candle pattern of the last closed day. Information only: it ranks and
recommends nothing.

The user gave the table's look (06.11.2026), not its rules, so these are written here and are stated in the
output's footer:
- Fiyat/EMA: the close against the EMA set of the user's own scorecard script (5, 20, 50, 100, 200);
  above all = "Tümü Üzerinde", below all = "Tümü Altında", otherwise "Karışık";
- Hacim (5 gün): the mean volume of the last 5 sessions / the mean of the 20 sessions before them;
  under 1 "Ortalama Altında", 1 and over "Ortalama Üzerinde", 1.5 and over "Yüksek";
- Mum: Yutan Boğa / Yutan Ayı (the last candle's body engulfs the previous body, opposite colour, larger body)
  and Yükseliş / Düşüş Marubozu (body at least 90% of the high-low range and the range at least half the ATR).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from core.analytics import scorecard as S

EMA_SET = (5, 20, 50, 100, 200)
VOLUME_RECENT, VOLUME_BASE, HIGH_VOLUME = 5, 20, 1.5
MARUBOZU_BODY, MARUBOZU_RANGE_ATR = 0.90, 0.5
MIN_CANDLES = 210  # the 200-session EMA needs its history
MAX_ROWS = 30
NO_DATA = "veri yok"
DISCLAIMER = "Teknik gösterge sonucudur; öneri değildir."


@dataclass(frozen=True)
class Row:
    symbol: str
    rsi: float
    price_ema: str
    volume: str
    pattern: str
    day: object = None


def price_vs_ema(close: pd.Series) -> str:
    last = float(close.iloc[-1])
    emas = [S.ema(close, n).iloc[-1] for n in EMA_SET]
    if any(not math.isfinite(float(e)) for e in emas):
        return NO_DATA
    above = [last > float(e) for e in emas]
    return "Tümü Üzerinde" if all(above) else ("Tümü Altında" if not any(above) else "Karışık")


def volume_label(volume: pd.Series) -> str:
    if len(volume) < VOLUME_RECENT + VOLUME_BASE:
        return NO_DATA
    recent = float(volume.iloc[-VOLUME_RECENT:].mean())
    base = float(volume.iloc[-(VOLUME_RECENT + VOLUME_BASE):-VOLUME_RECENT].mean())
    if not base > 0:
        return NO_DATA
    ratio = recent / base
    return "Yüksek" if ratio >= HIGH_VOLUME else ("Ortalama Üzerinde" if ratio >= 1 else "Ortalama Altında")


def patterns(df: pd.DataFrame) -> str:
    """The pattern labels of the last closed candle ('' when none)."""

    if len(df) < 2:
        return ""
    o, h, low, c = (float(df[k].iloc[-1]) for k in ("open", "high", "low", "close"))
    po, pc = float(df["open"].iloc[-2]), float(df["close"].iloc[-2])
    body, prev_body = abs(c - o), abs(pc - po)
    found = []
    if pc < po and c > o and o <= pc and c >= po and body > prev_body:
        found.append("Yutan Boğa")
    elif pc > po and c < o and o >= pc and c <= po and body > prev_body:
        found.append("Yutan Ayı")
    rng = h - low
    atr = float(S.atr(df).iloc[-1])
    if rng > 0 and math.isfinite(atr) and body >= MARUBOZU_BODY * rng and rng >= MARUBOZU_RANGE_ATR * atr:
        found.append("Yükseliş Marubozu" if c > o else "Düşüş Marubozu")
    return ", ".join(found)


def row(symbol: str, df: pd.DataFrame | None) -> Row:
    if df is None or len(df) == 0:
        return Row(symbol, math.nan, NO_DATA, NO_DATA, "")
    day = df.index[-1].date()
    if len(df) < MIN_CANDLES:
        return Row(symbol, math.nan, NO_DATA, volume_label(df["volume"]), patterns(df), day)
    rsi = float(S.rsi(df["close"]).iloc[-1])
    return Row(symbol, rsi if math.isfinite(rsi) else math.nan, price_vs_ema(df["close"]),
               volume_label(df["volume"]), patterns(df), day)


def rows(frames: dict[str, pd.DataFrame], symbols: list[str]) -> list[Row]:
    return [row(s, frames.get(s)) for s in symbols]


def text(title: str, table: list[Row]) -> str:
    days = sorted({r.day for r in table if r.day})
    when = f" · son kapanış {days[-1]:%d.%m.%Y}" if days else ""
    lines = [f"📊 Tablo: {title}{when} · {len(table)} hisse"]
    for r in table[:MAX_ROWS]:
        rsi = "—" if math.isnan(r.rsi) else f"{r.rsi:.1f}".replace(".", ",")
        candle = f" · Mum: {r.pattern}" if r.pattern else ""
        lines.append(f"{r.symbol.removesuffix('.IS')} · RSI {rsi} · Fiyat/EMA: {r.price_ema} · "
                     f"Hacim (5g): {r.volume}{candle}")
    if len(table) > MAX_ROWS:
        lines.append(f"ve {len(table) - MAX_ROWS} hisse daha: /tablo KOD KOD ...")
    lines.append(f"{DISCLAIMER} EMA seti 5/20/50/100/200; Hacim: son 5 seans / önceki 20 seans ortalaması.")
    return "\n".join(lines)
