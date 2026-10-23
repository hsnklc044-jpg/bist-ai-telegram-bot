"""
QuantBIST RC8
Market Data Provider

Responsibilities:

- Yahoo Finance OHLCV provider
- Data normalization
- Market cache layer
- Snapshot generation
- Data quality information
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from core.infrastructure.exceptions import (
    MarketError,
)
from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)





# =====================================================
# CONFIG
# =====================================================


DEFAULT_PERIOD = "6mo"

DEFAULT_INTERVAL = "1d"


CACHE_MINUTES = 5





# =====================================================
# CACHE
# =====================================================


_PRICE_CACHE: dict[str, dict] = {}





def _cache_valid(
    symbol: str,
) -> bool:


    item = _PRICE_CACHE.get(symbol)


    if not item:

        return False



    age = (

        datetime.now()

        -

        item["time"]

    )



    return (

        age

        <

        timedelta(

            minutes=CACHE_MINUTES

        )

    )







# =====================================================
# NORMALIZER
# =====================================================


def _normalize_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:


    if df.empty:

        return pd.DataFrame()



    try:


        if isinstance(

            df.columns,

            pd.MultiIndex,

        ):


            df = pd.DataFrame(

                {

                    "close":
                        df["Close"].iloc[:,0],


                    "high":
                        df["High"].iloc[:,0],


                    "low":
                        df["Low"].iloc[:,0],


                    "volume":
                        df["Volume"].iloc[:,0],

                }

            )


        else:


            df = pd.DataFrame(

                {

                    "close":
                        df["Close"],


                    "high":
                        df["High"],


                    "low":
                        df["Low"],


                    "volume":
                        df.get(
                            "Volume",
                            0,
                        ),

                }

            )




        df["volume"] = (

            pd.to_numeric(

                df["volume"],

                errors="coerce",

            )

            .fillna(0)

        )



        return (

            df

            .dropna()

            .sort_index()

        )



    except Exception as exc:


        raise MarketError(

            f"Normalization failed: {exc}"

        ) from exc







# =====================================================
# DATA QUALITY
# =====================================================


def get_data_quality(
    df: pd.DataFrame,
) -> dict:


    candles = len(df)



    if candles >= 200:

        reliability = 100


    elif candles >= 100:

        reliability = 85


    elif candles >= 50:

        reliability = 70


    else:

        reliability = 50




    return {


        "candles":

            candles,


        "reliability":

            reliability,


        "ema200_available":

            candles >= 200,


        "updated":

            datetime.now(),

    }







# =====================================================
# HISTORY
# =====================================================


def load_price_history(
    symbol: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:


    cache_key = (

        f"{symbol}_{period}_{interval}"

    )



    if _cache_valid(cache_key):


        logger.debug(

            "Cache hit | %s",

            symbol,

        )


        return _PRICE_CACHE[cache_key]["data"]





    logger.info(

        "Loading market data | %s",

        symbol,

    )



    try:



        df = yf.download(

            symbol,

            period=period,

            interval=interval,

            auto_adjust=True,

            progress=False,

            threads=False,

        )




        df = _normalize_dataframe(

            df,

        )




        if df.empty:


            raise MarketError(

                f"No price data: {symbol}"

            )





        _PRICE_CACHE[cache_key] = {


            "data":

                df,


            "time":

                datetime.now(),


        }





        logger.info(

            "Market loaded | %s | candles=%d",

            symbol,

            len(df),

        )



        return df




    except MarketError:

        raise



    except Exception as exc:


        logger.exception(

            "Market download failed."

        )


        raise MarketError(

            str(exc)

        ) from exc







# =====================================================
# LAST PRICE
# =====================================================


def load_last_price(
    symbol: str,
) -> float:


    df = load_price_history(

        symbol,

        period="5d",

    )


    return round(

        float(

            df["close"].iloc[-1]

        ),

        2,

    )








# =====================================================
# SNAPSHOT
# =====================================================


def load_snapshot(
    symbol: str,
) -> dict:


    df = load_price_history(

        symbol,

        period="1mo",

    )



    if len(df) < 2:

        raise MarketError(

            f"Insufficient data: {symbol}"

        )



    close = float(

        df["close"].iloc[-1]

    )


    previous = float(

        df["close"].iloc[-2]

    )



    change = 0.0



    if previous:

        change = round(

            (

                (close - previous)

                /

                previous

            )

            *

            100,

            2,

        )





    return {


        "symbol":

            symbol,


        "price":

            round(

                close,

                2,

            ),


        "change":

            change,


        "volume":

            float(

                df["volume"].iloc[-1]

            ),


        "quality":

            get_data_quality(

                df

            ),


        "updated":

            datetime.now(),

    }









# =====================================================
# MULTI SYMBOL
# =====================================================


def load_market(
    symbols: list[str],
) -> dict[str,pd.DataFrame]:


    result = {}



    for symbol in symbols:


        try:


            result[symbol] = load_price_history(

                symbol,

            )



        except Exception as exc:


            logger.warning(

                "Skipping %s | %s",

                symbol,

                exc,

            )



    return result







# =====================================================
# EXPORTS
# =====================================================


__all__ = [


    "load_price_history",


    "load_last_price",


    "load_snapshot",


    "load_market",


    "get_data_quality",


]