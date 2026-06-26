"""
QuantBIST RC4
Market Data Provider
"""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def load_price_history(
    symbol: str,
    period: str = "6mo",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Download historical price data.
    """

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):

        return pd.DataFrame(
            {
                "close": df["Close"].iloc[:, 0],
                "high": df["High"].iloc[:, 0],
                "low": df["Low"].iloc[:, 0],
                "volume": df["Volume"].iloc[:, 0],
            }
        ).dropna()

    return pd.DataFrame(
        {
            "close": df["Close"],
            "high": df["High"],
            "low": df["Low"],
            "volume": df["Volume"],
        }
    ).dropna()