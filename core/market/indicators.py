"""
QuantBIST
Market Indicator Engine

EMA trend, RSI, MACD, ATR, Bollinger Bands.

Values that cannot be computed (too little history) are None, never
0.0: a missing RSI must not look like an oversold stock.
"""

from __future__ import annotations

import math

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange, BollingerBands

from core.infrastructure.exceptions import MarketError
from core.infrastructure.logger import get_logger
from core.market.data import load_price_history
from core.market.models import IndicatorSnapshot, MarketTrend

logger = get_logger(__name__)

MIN_HISTORY_LENGTH = 60
LONG_TERM_WINDOW = 200


def _last(series: pd.Series) -> float | None:
    series = series.dropna()

    if series.empty:
        return None

    value = float(series.iloc[-1])

    if math.isnan(value) or math.isinf(value):
        return None

    return round(value, 4)


def _ema(close: pd.Series, window: int) -> float | None:
    if len(close) < window:
        return None

    return _last(EMAIndicator(close, window=window).ema_indicator())


def _sma(close: pd.Series, window: int) -> float | None:
    if len(close) < window:
        return None

    return _last(SMAIndicator(close, window=window).sma_indicator())


def _trend(
    ema20: float,
    ema50: float,
    long_term: float | None,
) -> MarketTrend:
    """
    BULLISH: EMA20 > EMA50 (> EMA200 when available).
    BEARISH: EMA20 < EMA50 (< EMA200 when available).
    """

    if ema20 > ema50 and (long_term is None or ema50 > long_term):
        return MarketTrend.BULLISH

    if ema20 < ema50 and (long_term is None or ema50 < long_term):
        return MarketTrend.BEARISH

    return MarketTrend.NEUTRAL


def _momentum(rsi: float, histogram: float) -> str:
    if rsi >= 70:
        return "OVERBOUGHT"
    if rsi <= 30:
        return "OVERSOLD"
    if histogram > 0:
        return "POSITIVE"
    if histogram < 0:
        return "NEGATIVE"
    return "NEUTRAL"


def generate_indicator_snapshot(
    symbol: str,
    df: pd.DataFrame | None = None,
) -> IndicatorSnapshot:
    """
    Indicators on the latest closed candle.

    Pass `df` when the caller already loaded the history.
    """

    logger.debug("Generating indicator snapshot | %s", symbol)

    try:
        if df is None:
            df = load_price_history(symbol)

        if df.empty:
            raise MarketError(f"No market data: {symbol}")

        if not {"close", "high", "low", "volume"}.issubset(df.columns):
            raise MarketError("Missing OHLCV columns.")

        candles = len(df)

        if candles < MIN_HISTORY_LENGTH:
            raise MarketError(f"Insufficient history: {symbol} ({candles} candles)")

        close = df["close"]
        high = df["high"]
        low = df["low"]

        macd = MACD(close)
        bands = BollingerBands(close, window=20, window_dev=2)

        values = {
            "price": _last(close),
            "volume": _last(df["volume"]),
            "ema20": _ema(close, 20),
            "ema50": _ema(close, 50),
            "ema200": _ema(close, LONG_TERM_WINDOW),
            "sma20": _sma(close, 20),
            "sma50": _sma(close, 50),
            "sma200": _sma(close, LONG_TERM_WINDOW),
            "rsi": _last(RSIIndicator(close, window=14).rsi()),
            "atr": _last(AverageTrueRange(high, low, close, window=14).average_true_range()),
            "macd": _last(macd.macd()),
            "macd_signal": _last(macd.macd_signal()),
            "macd_histogram": _last(macd.macd_diff()),
            "bollinger_upper": _last(bands.bollinger_hband()),
            "bollinger_middle": _last(bands.bollinger_mavg()),
            "bollinger_lower": _last(bands.bollinger_lband()),
        }

        optional = {"ema200", "sma200"}
        missing = [k for k, v in values.items() if v is None and k not in optional]

        if missing:
            raise MarketError(f"Indicators unavailable for {symbol}: {missing}")

        if values["ema200"] is None:
            logger.info(
                "EMA200 unavailable | %s | candles=%d",
                symbol,
                candles,
            )

        trend = _trend(values["ema20"], values["ema50"], values["ema200"])

        snapshot = IndicatorSnapshot(
            symbol=symbol,
            trend=trend,
            momentum=_momentum(values["rsi"], values["macd_histogram"]),
            **values,
        )

        logger.debug("Indicator completed | %s | Trend=%s", symbol, trend.value)

        return snapshot

    except MarketError:
        raise
    except Exception as exc:
        logger.exception("Indicator calculation failed | %s", symbol)
        raise MarketError(str(exc)) from exc


def above_long_term(snapshot: IndicatorSnapshot) -> bool | None:
    """Price above EMA200; None when EMA200 is unavailable."""

    if snapshot.ema200 is None:
        return None

    return snapshot.price > snapshot.ema200


__all__ = [
    "MIN_HISTORY_LENGTH",
    "generate_indicator_snapshot",
    "above_long_term",
]
