"""
QuantBIST
ML filter, features and labels (BIST 30 hedefi, adım 2).

Features of day t use candles up to and including t only (the screen fields' own tested
definitions plus EMA distances and a volume anomaly). The label of day t is the trade the
filter would judge: enter at the NEXT session's open, 2% stop, 4% target, at most HORIZON
sessions. A session that touches both levels counts as a stop (no intraday order is known).
An entry the price limit makes impossible (a limit-up open) has no label.

Labels look forward by construction; each row carries the date its label is known
(`label_end`) so training can never use a label that was not known before the test period.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

STOP = 0.02
TARGET = 0.04
HORIZON = 10
COST = 0.0015  # round trip, as the scenario cards (K-55)
LIMIT_MOVE = 0.095
SCREEN_FIELDS = ("rsi", "adx", "atr_yuzde", "bb_yuzde", "cmf", "stok_k", "obv_egim", "oynaklik_20g")
FEATURES = ("ema50_mesafe", "ema200_mesafe", "ema50_200", "hacim_z", "hacim_oran_5", "getiri_5", "getiri_20",
            *SCREEN_FIELDS)


def features(df: pd.DataFrame) -> pd.DataFrame:
    """One row per candle; NaN while an indicator has too little history."""

    from core.screen.fields import table

    close, volume = df["close"], df["volume"]
    ema50 = close.ewm(span=50, adjust=False, min_periods=50).mean()
    ema200 = close.ewm(span=200, adjust=False, min_periods=200).mean()
    past = volume.shift(1).rolling(20, min_periods=20)  # the 20 sessions before t: today is the anomaly
    out = pd.DataFrame(index=df.index)
    out["ema50_mesafe"] = close / ema50 - 1
    out["ema200_mesafe"] = close / ema200 - 1
    out["ema50_200"] = ema50 / ema200 - 1
    out["hacim_z"] = (volume - past.mean()) / past.std()
    out["hacim_oran_5"] = volume.rolling(5).mean() / past.mean()
    out["getiri_5"] = close / close.shift(5) - 1
    out["getiri_20"] = close / close.shift(20) - 1
    screen = table(df, close, list(SCREEN_FIELDS))
    for name in SCREEN_FIELDS:
        out[name] = screen[name]
    return out.replace([np.inf, -np.inf], np.nan)


def labels(df: pd.DataFrame, stop: float = STOP, target: float = TARGET, horizon: int = HORIZON) -> pd.DataFrame:
    """label (1 target first, 0 otherwise), r (net return of the trade) and label_end per day t."""

    o, h, low, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    n = len(df)
    label = np.full(n, np.nan)
    ret = np.full(n, np.nan)
    end = np.full(n, None, dtype=object)
    for t in range(n - 1):
        entry = o[t + 1]
        if not entry > 0 or entry / c[t] - 1 >= LIMIT_MOVE:
            continue  # no price, or a limit-up open: the order would not fill
        last = min(t + horizon, n - 1)
        if last - t < horizon:
            break  # the outcome is not known yet
        result = None
        for d in range(t + 1, last + 1):
            if low[d] <= entry * (1 - stop):
                result = (0, -stop if o[d] > entry * (1 - stop) else o[d] / entry - 1, d)  # a gap fills at the open
                break
            if h[d] >= entry * (1 + target):
                result = (1, target if o[d] < entry * (1 + target) else o[d] / entry - 1, d)
                break
        if result is None:
            result = (0, c[last] / entry - 1, last)
        label[t], ret[t], end[t] = result[0], result[1] - COST, df.index[result[2]]
    return pd.DataFrame({"label": label, "r": ret, "label_end": pd.to_datetime(pd.Series(end, index=df.index))},
                        index=df.index)


def dataset(frames: dict[str, pd.DataFrame], members=None) -> pd.DataFrame:
    """Pooled rows (date, symbol, features, label). `members(date) -> set of symbols` keeps a
    stock only on the days it was in the universe (point in time)."""

    parts = []
    for symbol, df in frames.items():
        if df is None or len(df) < 250:
            continue
        part = features(df).join(labels(df))
        part["symbol"] = symbol
        parts.append(part)
    if not parts:
        return pd.DataFrame(columns=[*FEATURES, "label", "r", "label_end", "symbol"])
    data = pd.concat(parts).rename_axis("date").reset_index()
    if members is not None:
        keep = [s in members(d) for d, s in zip(data["date"], data["symbol"], strict=True)]
        data = data[keep]
    return data.dropna(subset=[*FEATURES, "label"]).sort_values(["date", "symbol"]).reset_index(drop=True)


__all__ = ["COST", "FEATURES", "HORIZON", "STOP", "TARGET", "dataset", "features", "labels"]
