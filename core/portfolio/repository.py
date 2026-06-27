"""
QuantBIST RC4
Portfolio Repository
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PORTFOLIO_FILE = Path("data/portfolio_model.csv")


def load_portfolio() -> pd.DataFrame:
    """
    Portfolio verisini yükler ve standart hale getirir.
    """

    if not PORTFOLIO_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(PORTFOLIO_FILE)

    # -----------------------------
    # Standart kolon isimleri
    # -----------------------------

    df.columns = [
        column.strip().lower()
        for column in df.columns
    ]

    # -----------------------------
    # Value kolonu yoksa oluştur
    # -----------------------------

    if (
        "value" not in df.columns
        and {"price", "quantity"}.issubset(df.columns)
    ):

        df["value"] = (
            df["price"] * df["quantity"]
        )

    # -----------------------------
    # Sayısal alanlar
    # -----------------------------

    numeric_columns = [

        "price",

        "quantity",

        "value",

    ]

    for column in numeric_columns:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0)

    return df