"""
QuantBIST Framework
Portfolio Repository
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.infrastructure.exceptions import (
    PortfolioRepositoryError,
    PortfolioValidationError,
)

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

# =====================================================
# CONFIGURATION
# =====================================================

PORTFOLIO_FILE = Path("data/portfolio_model.csv")

REQUIRED_COLUMNS = (
    "symbol",
    "price",
    "quantity",
    "value",
)

NUMERIC_COLUMNS = (
    "price",
    "quantity",
    "value",
)

COLUMN_ALIASES = {

    # Quantity
    "lot": "quantity",
    "lots": "quantity",
    "adet": "quantity",
    "miktar": "quantity",
    "qty": "quantity",

    # Symbol
    "ticker": "symbol",
    "code": "symbol",

    # Price
    "close": "price",
    "cost": "price",

    # Value
    "total": "value",
    "amount": "value",
    "tutar": "value",

}

# =====================================================
# HELPERS
# =====================================================


def _normalize_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize dataframe columns.
    """

    df.columns = [

        str(column)
        .strip()
        .lower()

        for column in df.columns

    ]

    df.rename(

        columns=COLUMN_ALIASES,

        inplace=True,

    )

    return df


def _create_missing_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create calculated columns.
    """

    if (

        "value" not in df.columns

        and

        {

            "price",

            "quantity",

        }.issubset(df.columns)

    ):

        logger.info(
            "Creating value column."
        )

        df["value"] = (

            df["price"]

            * df["quantity"]

        )

    return df


def _convert_numeric_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert numeric columns.
    """

    for column in NUMERIC_COLUMNS:

        if column in df.columns:

            df[column] = pd.to_numeric(

                df[column],

                errors="coerce",

            ).fillna(0.0)

    return df


def _validate_schema(
    df: pd.DataFrame,
) -> None:
    """
    Validate dataframe schema.
    """

    missing = [

        column

        for column in REQUIRED_COLUMNS

        if column not in df.columns

    ]

    if missing:

        raise PortfolioValidationError(

            "Missing required columns: "

            + ", ".join(missing)

        )


# =====================================================
# PUBLIC API
# =====================================================


def load_portfolio() -> pd.DataFrame:
    """
    Load portfolio dataframe.
    """

    logger.info(
        "Loading portfolio..."
    )

    try:

        if not PORTFOLIO_FILE.exists():

            raise PortfolioRepositoryError(

                f"Portfolio file not found: {PORTFOLIO_FILE}"

            )

        df = pd.read_csv(PORTFOLIO_FILE)

        logger.info(

            "Portfolio loaded (%d rows).",

            len(df),

        )

        df = _normalize_columns(df)

        df = _create_missing_columns(df)

        df = _convert_numeric_columns(df)

        _validate_schema(df)

        logger.info(
            "Portfolio repository ready."
        )

        return df.copy()

    except (

        PortfolioRepositoryError,

        PortfolioValidationError,

    ):

        raise

    except Exception as exc:

        logger.exception(
            "Unexpected repository error."
        )

        raise PortfolioRepositoryError(
            str(exc)
        ) from exc


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "load_portfolio",

]