"""
QuantBIST Framework
Market Indicator Engine
"""

from __future__ import annotations

import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import (
    EMAIndicator,
    MACD,
    SMAIndicator,
)
from ta.volatility import (
    AverageTrueRange,
    BollingerBands,
)

from core.infrastructure.exceptions import (
    MarketError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.market.data import (
    load_price_history,
)

from core.market.models import (
    IndicatorSnapshot,
    MarketTrend,
)

logger = get_logger(__name__)


# =====================================================
# HELPERS
# =====================================================

def _last(series: pd.Series) -> float:
    """
    Return last value.
    """

    return round(
        float(series.iloc[-1]),
        4,
    )


def _ema(
    close: pd.Series,
    window: int,
) -> float:

    return _last(

        EMAIndicator(
            close,
            window=window,
        ).ema_indicator()

    )


def _sma(
    close: pd.Series,
    window: int,
) -> float:

    return _last(

        SMAIndicator(
            close,
            window=window,
        ).sma_indicator()

    )


def _rsi(
    close: pd.Series,
) -> float:

    return _last(

        RSIIndicator(
            close,
            window=14,
        ).rsi()

    )
def _macd(
    close: pd.Series,
) -> tuple[float, float, float]:
    """
    Calculate MACD values.
    """

    macd = MACD(close)

    return (

        _last(
            macd.macd()
        ),

        _last(
            macd.macd_signal()
        ),

        _last(
            macd.macd_diff()
        ),

    )


def _atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> float:
    """
    Calculate ATR.
    """

    return _last(

        AverageTrueRange(

            high,

            low,

            close,

            window=14,

        ).average_true_range()

    )


def _bollinger(
    close: pd.Series,
) -> tuple[float, float, float]:
    """
    Calculate Bollinger Bands.
    """

    bb = BollingerBands(

        close,

        window=20,

        window_dev=2,

    )

    return (

        _last(
            bb.bollinger_hband()
        ),

        _last(
            bb.bollinger_mavg()
        ),

        _last(
            bb.bollinger_lband()
        ),

    )


# =====================================================
# TREND ENGINE
# =====================================================

def _trend(
    ema20: float,
    ema50: float,
    ema200: float,
) -> MarketTrend:
    """
    Determine primary trend.
    """

    if ema20 > ema50 > ema200:

        return MarketTrend.BULLISH

    if ema20 < ema50 < ema200:

        return MarketTrend.BEARISH

    return MarketTrend.NEUTRAL


def _momentum(
    rsi: float,
    histogram: float,
) -> str:
    """
    Determine momentum.
    """

    if rsi >= 70:

        return "OVERBOUGHT"

    if rsi <= 30:

        return "OVERSOLD"

    if histogram > 0:

        return "POSITIVE"

    if histogram < 0:

        return "NEGATIVE"

    return "NEUTRAL"

# =====================================================
# SNAPSHOT ENGINE
# =====================================================

def generate_indicator_snapshot(
    symbol: str,
) -> IndicatorSnapshot:
    """
    Generate complete technical indicator snapshot.
    """

    logger.info(
        "Generating indicator snapshot for %s",
        symbol,
    )

    try:

        df = load_price_history(symbol)

        if df.empty:

            raise MarketError(
                f"No market data for {symbol}"
            )

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        ema20 = _ema(close, 20)
        ema50 = _ema(close, 50)
        ema200 = _ema(close, 200)

        sma20 = _sma(close, 20)
        sma50 = _sma(close, 50)
        sma200 = _sma(close, 200)

        rsi = _rsi(close)

        macd, signal, histogram = _macd(
            close,
        )

        atr = _atr(
            high,
            low,
            close,
        )

        bb_upper, bb_middle, bb_lower = _bollinger(
            close,
        )

        trend = _trend(
            ema20,
            ema50,
            ema200,
        )

        momentum = _momentum(
            rsi,
            histogram,
        )

        snapshot = IndicatorSnapshot(

            symbol=symbol,

            price=_last(close),

            volume=_last(volume),

            ema20=ema20,
            ema50=ema50,
            ema200=ema200,

            sma20=sma20,
            sma50=sma50,
            sma200=sma200,

            rsi=rsi,

            atr=atr,

            macd=macd,
            macd_signal=signal,
            macd_histogram=histogram,

            bollinger_upper=bb_upper,
            bollinger_middle=bb_middle,
            bollinger_lower=bb_lower,

            trend=trend,

            momentum=momentum,

        )

        logger.info(
            "Indicator snapshot generated for %s",
            symbol,
        )

        return snapshot

    except MarketError:

        raise

    except Exception as exc:

        logger.exception(
            "Indicator calculation failed."
        )

        raise MarketError(
            str(exc)
        ) from exc

# =====================================================
# HELPERS
# =====================================================

def is_bullish(
    snapshot: IndicatorSnapshot,
) -> bool:
    """
    Returns True if trend is bullish.
    """

    return snapshot.trend is MarketTrend.BULLISH


def is_bearish(
    snapshot: IndicatorSnapshot,
) -> bool:
    """
    Returns True if trend is bearish.
    """

    return snapshot.trend is MarketTrend.BEARISH


def is_neutral(
    snapshot: IndicatorSnapshot,
) -> bool:
    """
    Returns True if trend is neutral.
    """

    return snapshot.trend is MarketTrend.NEUTRAL


def strong_buy_signal(
    snapshot: IndicatorSnapshot,
) -> bool:
    """
    Strong bullish signal.
    """

    return (

        snapshot.trend is MarketTrend.BULLISH

        and snapshot.rsi < 70

        and snapshot.macd > snapshot.macd_signal

    )


def strong_sell_signal(
    snapshot: IndicatorSnapshot,
) -> bool:
    """
    Strong bearish signal.
    """

    return (

        snapshot.trend is MarketTrend.BEARISH

        and snapshot.rsi > 30

        and snapshot.macd < snapshot.macd_signal

    )


def indicator_score(
    snapshot: IndicatorSnapshot,
) -> float:
    """
    Calculate a technical score between 0 and 100.
    """

    score = 50.0

    if snapshot.trend is MarketTrend.BULLISH:
        score += 20
    elif snapshot.trend is MarketTrend.BEARISH:
        score -= 20

    if snapshot.rsi < 30:
        score += 10
    elif snapshot.rsi > 70:
        score -= 10

    if snapshot.macd > snapshot.macd_signal:
        score += 10
    else:
        score -= 10

    if snapshot.price > snapshot.ema200:
        score += 10
    else:
        score -= 10

    return round(

        max(
            0.0,
            min(
                100.0,
                score,
            ),
        ),

        2,

    )


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "generate_indicator_snapshot",

    "indicator_score",

    "is_bullish",

    "is_bearish",

    "is_neutral",

    "strong_buy_signal",

    "strong_sell_signal",

]
