"""
QuantBIST
Extended indicators for any candle frame (daily or hourly; 03.11.2026 request) and the "dip
dönüşü" trigger. Vectorized with the `ta` library (pandas-ta does not import with numpy 2);
the same definitions as the /tara fields. A value with too little history is NaN, never 0.

Columns added by add_indicators():
    trend       ema50, ema200, ema50_uzaklik, ema200_uzaklik (% distance of the close), adx
    momentum    rsi (14), stoch_k, stoch_d (slow stochastic 14, 3, 3), macd, macd_sinyal, macd_hist
    volatility  bb_ust, bb_orta, bb_alt (20, 2), bb_yuzde (%b, 0 = lower band), atr (14)
    volume      cmf (20, %), obv

Trigger (trigger_mask), a candidate for study, not advice:
    (rsi < 35 or stoch_k < 20) and bb_yuzde <= 0.10 (close in the lowest tenth of the band or below)
    and macd_hist < 0 and macd_hist rising (higher than the candle before).
"""

from __future__ import annotations

import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

RSI_LOW = 35
STOCH_LOW = 20
BB_NEAR = 0.10
REQUIRED = ("open", "high", "low", "close", "volume")


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """A copy of `df` with the indicator columns; an empty or unusable frame comes back unchanged."""

    from ta.momentum import RSIIndicator, StochasticOscillator
    from ta.trend import MACD, ADXIndicator, EMAIndicator
    from ta.volatility import AverageTrueRange, BollingerBands
    from ta.volume import OnBalanceVolumeIndicator

    if df is None or df.empty or not set(REQUIRED).issubset(df.columns):
        logger.warning("Indicators skipped: empty frame or missing columns")
        return df if df is not None else pd.DataFrame()
    out = df.copy()
    try:
        high, low, close, volume = out["high"], out["low"], out["close"], out["volume"]
        out["ema50"] = EMAIndicator(close, 50).ema_indicator()
        out["ema200"] = EMAIndicator(close, 200).ema_indicator()
        out["ema50_uzaklik"] = (close / out["ema50"] - 1) * 100
        out["ema200_uzaklik"] = (close / out["ema200"] - 1) * 100
        adx = ADXIndicator(high, low, close, 14).adx()
        out["adx"] = adx.where(pd.Series(range(len(out)), index=out.index) >= 28)  # ta's warm-up zeros are unknown
        out["rsi"] = RSIIndicator(close, 14).rsi()
        fast = StochasticOscillator(high, low, close, window=14, smooth_window=3).stoch()
        out["stoch_k"] = fast.rolling(3).mean()  # slow %K (14, 3)
        out["stoch_d"] = out["stoch_k"].rolling(3).mean()  # %D (3)
        macd = MACD(close)
        out["macd"], out["macd_sinyal"], out["macd_hist"] = macd.macd(), macd.macd_signal(), macd.macd_diff()
        bb = BollingerBands(close, 20, 2)
        out["bb_ust"], out["bb_orta"], out["bb_alt"] = bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()
        out["bb_yuzde"] = bb.bollinger_pband()
        atr = AverageTrueRange(high, low, close, 14).average_true_range()
        out["atr"] = atr.where(pd.Series(range(len(out)), index=out.index) >= 14)
        mfm = (((close - low) - (high - close)) / (high - low)).fillna(0.0)
        out["cmf"] = (mfm * volume).rolling(20).sum() / volume.rolling(20).sum() * 100
        out["obv"] = OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    except Exception as exc:  # noqa: BLE001 - bad data must not stop a whole scan
        logger.warning("Indicators failed | %s", exc)
        return df.copy()
    return out


def trigger_mask(ind: pd.DataFrame) -> pd.Series:
    """True on the candles where the trigger holds (False where any input is NaN)."""

    needed = ("rsi", "stoch_k", "bb_yuzde", "macd_hist")
    if ind is None or ind.empty or not set(needed).issubset(ind.columns):
        return pd.Series(False, index=getattr(ind, "index", None), dtype=bool)
    oversold = (ind["rsi"] < RSI_LOW) | (ind["stoch_k"] < STOCH_LOW)
    near_band = ind["bb_yuzde"] <= BB_NEAR
    hist = ind["macd_hist"]
    turning = (hist < 0) & (hist > hist.shift(1))
    return (oversold & near_band & turning).fillna(False).astype(bool)


def scan(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """The latest candle of each stock where the trigger holds: symbol, time, close and the inputs."""

    rows = []
    for symbol, df in frames.items():
        ind = add_indicators(df)
        mask = trigger_mask(ind)
        if len(mask) and bool(mask.iloc[-1]):
            last = ind.iloc[-1]
            rows.append({"symbol": symbol, "time": ind.index[-1], "close": float(last["close"]),
                         "rsi": float(last["rsi"]), "stoch_k": float(last["stoch_k"]),
                         "bb_yuzde": float(last["bb_yuzde"]), "macd_hist": float(last["macd_hist"])})
    return pd.DataFrame(rows, columns=["symbol", "time", "close", "rsi", "stoch_k", "bb_yuzde", "macd_hist"])


__all__ = ["BB_NEAR", "RSI_LOW", "STOCH_LOW", "add_indicators", "scan", "trigger_mask"]
