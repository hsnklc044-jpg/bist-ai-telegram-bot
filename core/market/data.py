"""
QuantBIST Framework
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
# HELPERS
# =====================================================

def _normalize_dataframe(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize yfinance dataframe.
    """

    if df.empty:

        return pd.DataFrame()

    if isinstance(
        df.columns,
        pd.MultiIndex,
    ):

        df = pd.DataFrame(

            {

                "close": df["Close"].iloc[:, 0],

                "high": df["High"].iloc[:, 0],

                "low": df["Low"].iloc[:, 0],

                "volume": df["Volume"].iloc[:, 0],

            }

        )

    else:

        df = pd.DataFrame(

            {

                "close": df["Close"],

                "high": df["High"],

                "low": df["Low"],

                "volume": df["Volume"],

            }

        )

    return df.dropna()


# =====================================================
# HISTORY
# =====================================================

def load_price_history(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Download historical OHLCV data.

    Parameters
    ----------
    symbol

    period

    interval

    Returns
    -------
    DataFrame
    """

    logger.info(

        "Loading history for %s",

        symbol,

    )

    try:

        df = yf.download(

            symbol,

            period=period,

            interval=interval,

            auto_adjust=True,

            progress=False,

        )

        df = _normalize_dataframe(
            df,
        )

        logger.info(

            "Loaded %d candles for %s",

            len(df),

            symbol,

        )

        return df

    except Exception as exc:

        logger.exception(

            "Price download failed."

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
    Return latest closing price.
    """

    df = load_price_history(

        symbol,

        period="5d",

    )

    if df.empty:

        raise MarketError(

            f"No data for {symbol}"

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
    Return latest market snapshot.
    """

    df = load_price_history(

        symbol,

        period="1mo",

    )

    if df.empty:

        raise MarketError(

            f"No data for {symbol}"

        )

    close = float(
        df["close"].iloc[-1]
    )

    previous = float(
        df["close"].iloc[-2]
    )

    change = round(

        (close - previous)

        / previous

        * 100,

        2,

    )

    return {

        "symbol": symbol,

        "price": round(close, 2),

        "change": change,

        "updated": datetime.now(),

    }


# =====================================================
# MULTI SYMBOL
# =====================================================

def load_market(
    symbols: list[str],
) -> dict[str, pd.DataFrame]:
    """
    Download multiple symbols.
    """

    result: dict[str, pd.DataFrame] = {}

    for symbol in symbols:

        try:

            result[symbol] = load_price_history(
                symbol,
            )

        except Exception:

            logger.warning(

                "Skipping %s",

                symbol,

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