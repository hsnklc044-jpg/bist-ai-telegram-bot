"""
QuantBIST
Technical indicator scorecard: the user's TradingView script "Teknik Gösterge Değerlendirici" (06.11.2026)
ported rule by rule. Twelve indicators, a good/bad verdict and a fixed number of points each, 100 in total.
It is a description of today's indicators, not a buy or sell call, and nothing here changes a model or a
rule: /karne is information only.

Differences from the script, on purpose and stated:
- the closed daily candles of the price store are used (TradingView also scores the live bar during the
  session, so a session reading can differ from the close);
- an indicator that cannot be computed (short history, flat prices) is "veri yok" with 0 points and is
  counted in the missing total; the script would silently score it 0;
- RMA and EMA start from the first value instead of an SMA seed: with 150+ candles the difference is far
  below any threshold here (the weight of the seed falls by 1/14 per candle).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MIN_CANDLES = 150
SMA_LENGTH, RSI_LENGTH, ATR_LENGTH, ADX_LENGTH, CCI_LENGTH, MFI_LENGTH = 20, 14, 14, 14, 20, 14
ATR_FACTOR = 1.1  # ATR above 110% of its own 14-session average
SUPERTREND_LENGTH, SUPERTREND_MULT = 10, 3.0
SAR_START, SAR_INCREMENT, SAR_MAX = 0.02, 0.02, 0.20
DISCLAIMER = "Teknik gösterge sonucudur; öneri değildir."

# the user's order; group is only for the short summary line (the total never changes)
RULES = (
    ("Supertrend (yön)", "Trend", 5),
    ("MACD (çizgi)", "Momentum", 10),
    ("RSI (50 üstü)", "Momentum", 10),
    ("SMA (fiyat üstü)", "Trend", 10),
    ("ATR (14 gün)", "Bantlar ve oynaklık", 5),
    ("Bollinger (orta bant)", "Bantlar ve oynaklık", 10),
    ("ADX (20 üstü, DI+ > DI-)", "Trend", 10),
    ("PSAR (fiyat altı)", "Trend", 10),
    ("OBV (20 gün SMA üstü)", "Hacim", 10),
    ("CCI (-100 üstü)", "Momentum", 5),
    ("Göreceli hacim (RelVol)", "Hacim", 10),
    ("MFI (50 üstü)", "Hacim", 5),
)
MAXIMUM = sum(points for _, _, points in RULES)  # 100


@dataclass(frozen=True)
class Row:
    name: str
    group: str
    value: str
    ok: bool | None  # None: veri yok
    points: int
    maximum: int


@dataclass
class Card:
    rows: list[Row] = field(default_factory=list)
    day: object = None

    @property
    def total(self) -> int:
        return sum(r.points for r in self.rows)

    @property
    def missing(self) -> int:
        return sum(r.ok is None for r in self.rows)

    def groups(self) -> dict[str, tuple[int, int]]:
        out: dict[str, list[int]] = {}
        for r in self.rows:
            got = out.setdefault(r.group, [0, 0])
            got[0] += r.points
            got[1] += r.maximum
        return {k: (v[0], v[1]) for k, v in out.items()}


# --- indicators (Pine definitions) ------------------------------------------------------------------------


def rma(x: pd.Series, n: int) -> pd.Series:
    """Pine ta.rma: Wilder smoothing, alpha 1/n."""

    return x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    prev = df["close"].shift(1)
    parts = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1)
    return parts.max(axis=1)  # the first candle has no previous close: its range is high - low


def rsi(close: pd.Series, n: int = RSI_LENGTH) -> pd.Series:
    delta = close.diff()
    gain, loss = rma(delta.clip(lower=0), n), rma((-delta).clip(lower=0), n)
    out = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    return out.where(loss != 0, np.where(gain > 0, 100.0, np.nan))


def macd(close: pd.Series) -> tuple[pd.Series, pd.Series]:
    line = ema(close, 12) - ema(close, 26)
    return line, ema(line, 9)


def atr(df: pd.DataFrame, n: int = ATR_LENGTH) -> pd.Series:
    return rma(true_range(df), n)


def dmi(df: pd.DataFrame, n: int = ADX_LENGTH) -> tuple[pd.Series, pd.Series, pd.Series]:
    """DI+, DI- (RMA) and the script's ADX: the SMA (not Wilder) of DX."""

    high, low = df["high"], df["low"]
    up, down = high - high.shift(1), low.shift(1) - low
    plus = up.where((up > down) & (up > 0), 0.0).where(up.notna(), 0.0)
    minus = down.where((down > up) & (down > 0), 0.0).where(down.notna(), 0.0)
    tr = rma(true_range(df), n)
    di_plus, di_minus = 100 * rma(plus, n) / tr, 100 * rma(minus, n) / tr
    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    return di_plus, di_minus, dx.rolling(n).mean()


def supertrend(df: pd.DataFrame, length: int = SUPERTREND_LENGTH, mult: float = SUPERTREND_MULT) -> pd.Series:
    """The script's Supertrend (hl2 source, RMA ATR): 1 up, -1 down; NaN before the ATR exists."""

    hl2 = ((df["high"] + df["low"]) / 2).to_numpy(float)
    close = df["close"].to_numpy(float)
    band = atr(df, length).to_numpy(float) * mult
    raw_up, raw_dn = hl2 - band, hl2 + band
    n = len(df)
    up, dn, trend = raw_up.copy(), raw_dn.copy(), np.full(n, np.nan)
    start = next((i for i in range(n) if not math.isnan(band[i])), None)
    if start is None:
        return pd.Series(trend, index=df.index)
    trend[start] = 1.0
    for i in range(start + 1, n):
        up1, dn1 = up[i - 1], dn[i - 1]
        up[i] = max(raw_up[i], up1) if close[i - 1] > up1 else raw_up[i]
        dn[i] = min(raw_dn[i], dn1) if close[i - 1] < dn1 else raw_dn[i]
        previous = trend[i - 1]
        if previous == -1 and close[i] > dn1:
            trend[i] = 1.0
        elif previous == 1 and close[i] < up1:
            trend[i] = -1.0
        else:
            trend[i] = previous
    return pd.Series(trend, index=df.index)


def parabolic_sar(df: pd.DataFrame, start: float = SAR_START, increment: float = SAR_INCREMENT,
                  maximum: float = SAR_MAX) -> pd.Series:
    """
    The parabolic SAR the way TradingView's built-in ta.sar computes it (Wilder's rule: the SAR is never inside
    the range of the previous two candles); the first candle is the warm-up (NaN). The ta library's PSAR is not
    used: it clamps to the second-last extreme instead of the more distant of the two and, with pandas 3, its
    `self._psar[i] = ...` appends rows instead of assigning (600 candles come back as 609 values).
    """

    high, low, close = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    n = len(df)
    out = np.full(n, np.nan)
    if n < 3:
        return pd.Series(out, index=df.index)
    result = extreme = accel = math.nan
    below = False
    for i in range(1, n):
        first_bar = False
        if i == 1:
            below = close[1] > close[0]
            extreme, result = (high[1], low[0]) if below else (low[1], high[0])
            first_bar, accel = True, start
        result = result + accel * (extreme - result)
        if below and result > low[i]:
            first_bar, below, result, extreme, accel = True, False, max(high[i], extreme), low[i], start
        elif not below and result < high[i]:
            first_bar, below, result, extreme, accel = True, True, min(low[i], extreme), high[i], start
        if not first_bar:
            if below and high[i] > extreme:
                extreme, accel = high[i], min(accel + increment, maximum)
            elif not below and low[i] < extreme:
                extreme, accel = low[i], min(accel + increment, maximum)
        if below:
            result = min(result, low[i - 1], low[i - 2]) if i > 1 else min(result, low[i - 1])
        else:
            result = max(result, high[i - 1], high[i - 2]) if i > 1 else max(result, high[i - 1])
        out[i] = result
    return pd.Series(out, index=df.index)


def obv(df: pd.DataFrame) -> pd.Series:
    return (np.sign(df["close"].diff()).fillna(0) * df["volume"]).cumsum()


def cci(df: pd.DataFrame, n: int = CCI_LENGTH) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    deviation = tp.rolling(n).apply(lambda w: np.abs(w - w.mean()).mean(), raw=True)
    return (tp - tp.rolling(n).mean()) / (0.015 * deviation.replace(0, np.nan))


def mfi(df: pd.DataFrame, n: int = MFI_LENGTH) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    flow, change = tp * df["volume"], tp.diff()
    upper = flow.where(change > 0, 0.0).rolling(n).sum()
    lower = flow.where(change < 0, 0.0).rolling(n).sum()
    out = 100 - 100 / (1 + upper / lower.replace(0, np.nan))
    return out.where(lower != 0, np.where(upper > 0, 100.0, np.nan))


# --- the card -----------------------------------------------------------------------------------------------


def _n(x: float, decimals: int = 2) -> str:
    return f"{x:,.{decimals}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _last(series: pd.Series) -> float:
    value = float(series.iloc[-1]) if len(series) else math.nan
    return value if math.isfinite(value) else math.nan


def score(df: pd.DataFrame) -> Card:
    """The twelve rows for the last closed candle of `df` (open, high, low, close, volume)."""

    card = Card(day=df.index[-1].date() if len(df) else None)
    points = {name: (group, maximum) for name, group, maximum in RULES}
    if len(df) < MIN_CANDLES:
        card.rows = [Row(name, g, f"yetersiz geçmiş ({len(df)} < {MIN_CANDLES} mum)", None, 0, m)
                     for name, (g, m) in points.items()]
        return card

    close, volume = df["close"], df["volume"]
    sma = close.rolling(SMA_LENGTH).mean()
    line, signal = macd(close)
    atr_now, atr_mean = atr(df), atr(df).rolling(ATR_LENGTH).mean()
    di_plus, di_minus, adx_value = dmi(df)
    obv_series = obv(df)
    rel_volume = volume / volume.rolling(SMA_LENGTH).mean().replace(0, np.nan)
    last = {
        "close": _last(close), "sma": _last(sma), "rsi": _last(rsi(close)), "line": _last(line),
        "signal": _last(signal), "atr": _last(atr_now), "atr_mean": _last(atr_mean),
        "di_plus": _last(di_plus), "di_minus": _last(di_minus), "adx": _last(adx_value),
        "sar": _last(parabolic_sar(df)), "obv": _last(obv_series), "obv_sma": _last(obv_series.rolling(20).mean()),
        "cci": _last(cci(df)), "rel": _last(rel_volume), "mfi": _last(mfi(df)), "trend": _last(supertrend(df)),
    }

    def need(*keys: str) -> bool:
        return all(math.isfinite(last[k]) for k in keys)

    checks = {
        "Supertrend (yön)": (need("trend"), lambda: last["trend"] == 1,
                             lambda: "yukarı" if last["trend"] == 1 else "aşağı"),
        "MACD (çizgi)": (need("line", "signal"), lambda: last["line"] > last["signal"],
                         lambda: f"{_n(last['line'])} / sinyal {_n(last['signal'])}"),
        "RSI (50 üstü)": (need("rsi"), lambda: last["rsi"] > 50, lambda: _n(last["rsi"], 1)),
        "SMA (fiyat üstü)": (need("sma"), lambda: last["close"] > last["sma"],
                             lambda: f"kapanış {_n(last['close'])} / SMA20 {_n(last['sma'])}"),
        "ATR (14 gün)": (need("atr", "atr_mean"), lambda: last["atr"] > ATR_FACTOR * last["atr_mean"],
                         lambda: f"{_n(last['atr'])} / eşik {_n(ATR_FACTOR * last['atr_mean'])}"),
        "Bollinger (orta bant)": (need("sma"), lambda: last["close"] > last["sma"],
                                  lambda: f"kapanış {_n(last['close'])} / orta {_n(last['sma'])}"),
        "ADX (20 üstü, DI+ > DI-)": (need("adx", "di_plus", "di_minus"),
                                     lambda: last["adx"] > 20 and last["di_plus"] > last["di_minus"],
                                     lambda: f"ADX {_n(last['adx'], 1)} · DI+ {_n(last['di_plus'], 1)} / DI- {_n(last['di_minus'], 1)}"),
        "PSAR (fiyat altı)": (need("sar"), lambda: last["close"] > last["sar"], lambda: f"SAR {_n(last['sar'])}"),
        "OBV (20 gün SMA üstü)": (need("obv", "obv_sma"), lambda: last["obv"] > last["obv_sma"],
                                  lambda: f"{_n(last['obv'] / 1e6, 1)} mn / SMA {_n(last['obv_sma'] / 1e6, 1)} mn"),
        "CCI (-100 üstü)": (need("cci"), lambda: last["cci"] > -100, lambda: _n(last["cci"], 0)),
        "Göreceli hacim (RelVol)": (need("rel"), lambda: last["rel"] > 1, lambda: f"{_n(last['rel'])}×"),
        "MFI (50 üstü)": (need("mfi"), lambda: last["mfi"] > 50, lambda: _n(last["mfi"], 1)),
    }
    for name, (group, maximum) in points.items():
        available, good, shown = checks[name]
        if not available:
            card.rows.append(Row(name, group, "veri yok", None, 0, maximum))
            continue
        ok = bool(good())
        card.rows.append(Row(name, group, shown(), ok, maximum if ok else 0, maximum))
    return card


def text(symbol: str, df: pd.DataFrame) -> str:
    card = score(df)
    code = symbol.removesuffix(".IS")
    when = f" · son kapanış {card.day:%d.%m.%Y}" if card.day else ""
    lines = [f"📋 {code} teknik gösterge karnesi{when}"]
    missing = f" (veri yok: {card.missing} gösterge)" if card.missing else ""
    lines.append(f"Toplam: {card.total}/{MAXIMUM}{missing}")
    lines.append(" · ".join(f"{g} {got}/{top}" for g, (got, top) in card.groups().items()))
    for r in card.rows:
        mark = "❔" if r.ok is None else ("✅" if r.ok else "❌")
        lines.append(f"{mark} {r.name}: {r.value} · {r.points}/{r.maximum}")
    lines.append(f"{DISCLAIMER} Kurallar TradingView betiğiyle aynıdır; kapanmış günlük mumlarla hesaplanır.")
    return "\n".join(lines)
