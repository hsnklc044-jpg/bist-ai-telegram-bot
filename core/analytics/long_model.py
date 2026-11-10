"""
QuantBIST
The technical half of the 6-12 month model (the user's specification of 06.11.2026): a 100-point technical
score and, separately, an entry decision. A high score alone never means "buy": the decision needs the trend
condition, a breakout above the previous 20 sessions' high, a relative volume of at least 1.5 and a price
not above the user's upper buy price; a stock that scores 82 without a breakout is "İzle" and the missing
condition is shown.

What is not here yet, and is said in the output: the fundamental filter (no financial data is connected),
the KAP date, the sector return difference (no sector map) and the lot sizing. Information only.

Completed daily candles only. An indicator that cannot be computed is "veri yok" (0 points) and the other
indicators are NOT rescaled to 100.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.analytics import scorecard as S

MIN_CANDLES = 210  # the 200-session SMA needs its history
BREAKOUT_WINDOW = 20
RELVOL_MIN, RELVOL_WINDOW = 1.5, 20
ADX_MIN = 20
RULES = (
    ("SMA trendi (kapanış > SMA50 > SMA200, SMA50 yükseliyor)", "Trend", 15),
    ("Supertrend (10, 3) yukarı", "Trend", 8),
    ("ADX/DMI (ADX > 20, +DI > -DI)", "Trend", 10),
    ("Parabolic SAR kapanışın altında", "Trend", 4),
    ("Bollinger (20, 2) orta bandın üstünde", "Trend", 3),
    ("MACD (12, 26, 9) çizgisi sinyalin üstünde", "Momentum", 10),
    ("RSI(14) > 50", "Momentum", 10),
    ("CCI(20) > -100", "Momentum", 5),
    ("OBV kendi SMA20'sinin üstünde", "Hacim", 10),
    ("Göreceli hacim ≥ 1,5 (önceki 20 seans medyanı)", "Hacim", 15),
    ("MFI(14) > 50", "Hacim", 10),
)
MAXIMUM = sum(p for _, _, p in RULES)  # 100
ENTER, WATCH, LACKING, OUT = "Giriş adayı", "İzle", "Veri yetersiz", "Elendi"
DISCLAIMER = "Teknik sonuçtur; öneri değildir."


@dataclass
class Condition:
    name: str
    ok: bool | None  # None: cannot be told
    detail: str


@dataclass
class Result:
    card: S.Card
    conditions: list[Condition] = field(default_factory=list)
    status: str = LACKING
    why: str = ""
    atr: float = math.nan
    atr_pct: float = math.nan
    breakout_level: float = math.nan
    close: float = math.nan
    upper: float | None = None


def _n(x: float, d: int = 2) -> str:
    return S._n(x, d)


def _wilder_adx(df: pd.DataFrame, n: int = 14) -> tuple[float, float, float]:
    """+DI, -DI and the standard (Wilder) ADX: the RMA of DX."""

    plus, minus, _ = S.dmi(df, n)
    dx = 100 * (plus - minus).abs() / (plus + minus).replace(0, np.nan)
    return S._last(plus), S._last(minus), S._last(S.rma(dx, n))


def evaluate(df: pd.DataFrame, upper: float | None = None) -> Result:
    card = S.Card(day=df.index[-1].date() if len(df) else None)
    meta = {name: (group, top) for name, group, top in RULES}
    result = Result(card=card, upper=upper)
    if len(df) < MIN_CANDLES:
        card.rows = [S.Row(name, g, f"yetersiz geçmiş ({len(df)} < {MIN_CANDLES} mum)", None, 0, m)
                     for name, (g, m) in meta.items()]
        result.why = f"{len(df)} mum var, en az {MIN_CANDLES} gerekir"
        return result

    close, volume = df["close"], df["volume"]
    sma50, sma200 = close.rolling(50).mean(), close.rolling(200).mean()
    line, signal = S.macd(close)
    basis = close.rolling(20).mean()
    obv = S.obv(df)
    di_plus, di_minus, adx = _wilder_adx(df)
    median = float(volume.iloc[-(RELVOL_WINDOW + 1):-1].median())
    relvol = float(volume.iloc[-1]) / median if median > 0 else math.nan
    last = {
        "close": S._last(close), "sma50": S._last(sma50), "sma200": S._last(sma200),
        "sma50_before": float(sma50.iloc[-6]) if len(sma50) > 6 else math.nan,
        "trend": S._last(S.supertrend(df)), "di_plus": di_plus, "di_minus": di_minus, "adx": adx,
        "sar": S._last(S.parabolic_sar(df)), "basis": S._last(basis), "line": S._last(line),
        "signal": S._last(signal), "rsi": S._last(S.rsi(close)), "cci": S._last(S.cci(df)),
        "obv": S._last(obv), "obv_sma": S._last(obv.rolling(20).mean()), "mfi": S._last(S.mfi(df)),
        "rel": relvol,
    }
    ok = math.isfinite
    checks = {
        "SMA trendi (kapanış > SMA50 > SMA200, SMA50 yükseliyor)": (
            all(ok(last[k]) for k in ("sma50", "sma200", "sma50_before")),
            lambda: last["close"] > last["sma50"] > last["sma200"] and last["sma50"] > last["sma50_before"],
            lambda: f"{_n(last['close'])} / SMA50 {_n(last['sma50'])} / SMA200 {_n(last['sma200'])}"),
        "Supertrend (10, 3) yukarı": (ok(last["trend"]), lambda: last["trend"] == 1,
                                      lambda: "yukarı" if last["trend"] == 1 else "aşağı"),
        "ADX/DMI (ADX > 20, +DI > -DI)": (
            all(ok(last[k]) for k in ("adx", "di_plus", "di_minus")),
            lambda: last["adx"] > ADX_MIN and last["di_plus"] > last["di_minus"],
            lambda: f"ADX {_n(last['adx'], 1)} · DI+ {_n(last['di_plus'], 1)} / DI- {_n(last['di_minus'], 1)}"),
        "Parabolic SAR kapanışın altında": (ok(last["sar"]), lambda: last["close"] > last["sar"],
                                            lambda: f"SAR {_n(last['sar'])}"),
        "Bollinger (20, 2) orta bandın üstünde": (ok(last["basis"]), lambda: last["close"] > last["basis"],
                                                  lambda: f"orta {_n(last['basis'])}"),
        "MACD (12, 26, 9) çizgisi sinyalin üstünde": (
            ok(last["line"]) and ok(last["signal"]), lambda: last["line"] > last["signal"],
            lambda: f"{_n(last['line'])} / sinyal {_n(last['signal'])}"),
        "RSI(14) > 50": (ok(last["rsi"]), lambda: last["rsi"] > 50, lambda: _n(last["rsi"], 1)),
        "CCI(20) > -100": (ok(last["cci"]), lambda: last["cci"] > -100, lambda: _n(last["cci"], 0)),
        "OBV kendi SMA20'sinin üstünde": (ok(last["obv"]) and ok(last["obv_sma"]),
                                          lambda: last["obv"] > last["obv_sma"],
                                          lambda: f"{_n(last['obv'] / 1e6, 1)} mn / SMA {_n(last['obv_sma'] / 1e6, 1)} mn"),
        "Göreceli hacim ≥ 1,5 (önceki 20 seans medyanı)": (ok(last["rel"]), lambda: last["rel"] >= RELVOL_MIN,
                                                           lambda: f"{_n(last['rel'])}×"),
        "MFI(14) > 50": (ok(last["mfi"]), lambda: last["mfi"] > 50, lambda: _n(last["mfi"], 1)),
    }
    verdict: dict[str, bool | None] = {}
    for name, (group, top) in meta.items():
        available, good, shown = checks[name]
        if not available:
            card.rows.append(S.Row(name, group, "veri yok", None, 0, top))
            verdict[name] = None
            continue
        passed = bool(good())
        verdict[name] = passed
        card.rows.append(S.Row(name, group, shown(), passed, top if passed else 0, top))

    atr = S._last(S.atr(df))
    result.atr, result.close = atr, last["close"]
    result.atr_pct = atr / last["close"] * 100 if math.isfinite(atr) and last["close"] else math.nan
    level = float(df["high"].iloc[-(BREAKOUT_WINDOW + 1):-1].max())
    result.breakout_level = level
    trend_ok = verdict["SMA trendi (kapanış > SMA50 > SMA200, SMA50 yükseliyor)"]
    volume_ok = verdict["Göreceli hacim ≥ 1,5 (önceki 20 seans medyanı)"]
    result.conditions = [
        Condition("SMA trend koşulu", trend_ok, "sağlandı" if trend_ok else "sağlanmadı"),
        Condition("Kırılım: kapanış önceki 20 seansın en yüksek fiyatının üstünde", bool(last["close"] > level),
                  f"kapanış {_n(last['close'])} / seviye {_n(level)}"),
        Condition("Göreceli hacim ≥ 1,5", volume_ok, f"{_n(last['rel'])}×" if ok(last["rel"]) else "veri yok"),
        Condition("Fiyat üst alım fiyatını aşmıyor (referans: son kapanış)",
                  None if upper is None else bool(last["close"] <= upper),
                  "üst alım fiyatı girilmedi" if upper is None else f"{_n(last['close'])} / üst {_n(upper)}"),
    ]
    result.status, result.why = decide(result.conditions)
    return result


def decide(conditions: list[Condition]) -> tuple[str, str]:
    """The decision is separate from the score: every entry condition must hold."""

    technical = conditions[:3]
    if any(c.ok is None for c in technical):
        return LACKING, "; ".join(c.name for c in technical if c.ok is None) + " hesaplanamadı"
    missing = [c.name for c in conditions if c.ok is False]
    pending = [c.detail or c.name for c in conditions if c.ok is None]  # the detail says why (e.g. no upper price)
    if not missing and not pending:
        return ENTER, "dört giriş koşulu da sağlandı (temel filtre ayrıca değerlendirilmeli)"
    parts = [f"eksik: {', '.join(missing)}"] if missing else []
    if pending:
        parts.append(f"bilinmiyor: {', '.join(pending)}")
    return WATCH, "; ".join(parts)


def text(symbol: str, df: pd.DataFrame, upper: float | None = None) -> str:
    r = evaluate(df, upper)
    code = symbol.removesuffix(".IS")
    card = r.card
    lines = [f"🧭 {code} 6–12 ay modeli (teknik) · fiyat verisi {card.day:%d.%m.%Y}" if card.day
             else f"🧭 {code} 6–12 ay modeli (teknik)"]
    groups = card.groups()
    lines.append(f"Teknik puan: {card.total}/{MAXIMUM}" + (f" (veri yok: {card.missing})" if card.missing else "")
                 + " · " + " · ".join(f"{g} {got}/{top}" for g, (got, top) in groups.items()))
    for row in card.rows:
        mark = "❔" if row.ok is None else ("✅" if row.ok else "❌")
        lines.append(f"{mark} {row.name}: {row.value} · {row.points}/{row.maximum}")
    if math.isfinite(r.atr):
        lines.append(f"Risk: ATR(14) {_n(r.atr)} (ATR% {_n(r.atr_pct, 1)}) · kırılım seviyesi {_n(r.breakout_level)}")
    lines.append("Giriş koşulları (puandan ayrı):")
    for c in r.conditions:
        mark = "❔" if c.ok is None else ("✅" if c.ok else "❌")
        lines.append(f"{mark} {c.name}: {c.detail}")
    lines.append("Temel filtre: değerlendirilmedi (finansal veri bağlı değil) · KAP tarihi: veri yok · "
                 "sektör farkı: veri yok")
    lines.append(f"Karar: {r.status}" + (f" — {r.why}" if r.why else ""))
    lines.append(f"{DISCLAIMER} Üst alım fiyatı için: /uzun {code} FİYAT")
    return "\n".join(lines)
