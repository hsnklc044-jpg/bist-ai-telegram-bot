"""
QuantBIST RC5
Market Data Provider
"""

from __future__ import annotations


from datetime import datetime


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





# =====================================================
# NORMALIZER
# =====================================================


def _normalize_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize Yahoo Finance dataframe.
    """


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

            f"Data normalization failed: {exc}"

        ) from exc





# =====================================================
# HISTORY
# =====================================================


def load_price_history(
    symbol: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:
    """
    Download OHLCV history.
    """


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



        logger.info(

            "Market data loaded | %s | candles=%d",

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
    """
    Return latest close price.
    """


    df = load_price_history(

        symbol,

        period="5d",

    )



    if df.empty:

        raise MarketError(

            f"No price data: {symbol}"

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
    """
    Return market snapshot.
    """


    df = load_price_history(

        symbol,

        period="1mo",

    )



    if len(df) < 2:

        raise MarketError(

            f"Insufficient snapshot data: {symbol}"

        )



    close = float(

        df["close"].iloc[-1]

    )


    previous = float(

        df["close"].iloc[-2]

    )



    change = 0.0



    if previous != 0:


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



        "updated":

            datetime.now(),

    }






# =====================================================
# MULTI SYMBOL
# =====================================================


def load_market(
    symbols: list[str],
) -> dict[str,pd.DataFrame]:
    """
    Download multiple symbols.
    """


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

]