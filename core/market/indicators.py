"""
QuantBIST RC8
Market Indicator Engine

Technical Intelligence Layer

- EMA Trend
- RSI Momentum
- MACD
- ATR
- Bollinger Bands
- Technical Score
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
# CONFIG
# =====================================================


MIN_HISTORY_LENGTH = 50







# =====================================================
# HELPERS
# =====================================================


def _last(
    series: pd.Series,
) -> float:


    series = series.dropna()


    if series.empty:

        return 0.0



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

        )

        .ema_indicator()

    )







def _sma(
    close: pd.Series,
    window: int,
) -> float:


    return _last(

        SMAIndicator(

            close,

            window=window,

        )

        .sma_indicator()

    )







def _rsi(
    close: pd.Series,
) -> float:


    return _last(

        RSIIndicator(

            close,

            window=14,

        )

        .rsi()

    )







def _macd(
    close: pd.Series,
):


    indicator = MACD(

        close

    )


    return (

        _last(

            indicator.macd()

        ),


        _last(

            indicator.macd_signal()

        ),


        _last(

            indicator.macd_diff()

        ),

    )







def _atr(
    high,
    low,
    close,
):


    return _last(

        AverageTrueRange(

            high,

            low,

            close,

            window=14,

        )

        .average_true_range()

    )







def _bollinger(
    close,
):


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
# ADAPTIVE LONG TERM EMA
# =====================================================


def _long_term_ema(
    close: pd.Series,
    candles: int,
) -> float:


    if candles >= 200:

        return _ema(

            close,

            200,

        )


    if candles >= 100:

        return _ema(

            close,

            100,

        )


    return _ema(

        close,

        50,

    )








# =====================================================
# TREND ENGINE
# =====================================================


def _trend(
    ema20: float,
    ema50: float,
    long_term: float,
) -> MarketTrend:


    if (

        ema20 > ema50

        and

        ema50 > long_term

    ):

        return MarketTrend.BULLISH





    if (

        ema20 < ema50

        and

        ema50 < long_term

    ):

        return MarketTrend.BEARISH





    return MarketTrend.NEUTRAL







# =====================================================
# MOMENTUM
# =====================================================


def _momentum(
    rsi: float,
    histogram: float,
) -> str:


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
# SNAPSHOT
# =====================================================


def generate_indicator_snapshot(
    symbol: str,
) -> IndicatorSnapshot:


    logger.info(

        "Generating indicator snapshot | %s",

        symbol,

    )


    try:



        df = load_price_history(

            symbol,

        )




        if df.empty:

            raise MarketError(

                f"No market data: {symbol}"

            )





        required_columns = {

            "close",

            "high",

            "low",

            "volume",

        }



        if not required_columns.issubset(

            df.columns

        ):

            raise MarketError(

                "Missing OHLCV columns."

            )





        candles = len(df)



        if candles < MIN_HISTORY_LENGTH:

            raise MarketError(

                f"Insufficient history: {candles}"

            )






        if candles < 200:

            logger.warning(

                "Short history | %s | candles=%d | adaptive EMA active",

                symbol,

                candles,

            )







        close = df["close"]

        high = df["high"]

        low = df["low"]

        volume = df["volume"]






        ema20 = _ema(

            close,

            20,

        )



        ema50 = _ema(

            close,

            50,

        )



        long_term = _long_term_ema(

            close,

            candles,

        )







        sma20 = _sma(

            close,

            20,

        )


        sma50 = _sma(

            close,

            50,

        )


        sma200 = _sma(

            close,

            200,

        )







        rsi = _rsi(

            close,

        )





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

            long_term,

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


            ema200=long_term,



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

            "Indicator completed | %s | Trend=%s",

            symbol,

            trend.value,

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
# SIGNAL HELPERS
# =====================================================


def is_bullish(
    snapshot: IndicatorSnapshot,
) -> bool:


    return snapshot.trend is MarketTrend.BULLISH







def is_bearish(
    snapshot: IndicatorSnapshot,
) -> bool:


    return snapshot.trend is MarketTrend.BEARISH







def is_neutral(
    snapshot: IndicatorSnapshot,
) -> bool:


    return snapshot.trend is MarketTrend.NEUTRAL







def strong_buy_signal(
    snapshot: IndicatorSnapshot,
) -> bool:


    return (

        snapshot.trend is MarketTrend.BULLISH

        and

        snapshot.rsi < 70

        and

        snapshot.macd > snapshot.macd_signal

    )







def strong_sell_signal(
    snapshot: IndicatorSnapshot,
) -> bool:


    return (

        snapshot.trend is MarketTrend.BEARISH

        and

        snapshot.rsi > 30

        and

        snapshot.macd < snapshot.macd_signal

    )







# =====================================================
# SCORE
# =====================================================


def indicator_score(
    snapshot: IndicatorSnapshot,
) -> float:


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

            0,

            min(

                100,

                score,

            ),

        ),

        2,

    )








__all__ = [

    "generate_indicator_snapshot",

    "indicator_score",

    "is_bullish",

    "is_bearish",

    "is_neutral",

    "strong_buy_signal",

    "strong_sell_signal",

]