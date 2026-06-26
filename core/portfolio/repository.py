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
    Load portfolio data from CSV.
    """

    if not PORTFOLIO_FILE.exists():
        return pd.DataFrame()

    return pd.read_csv(PORTFOLIO_FILE)