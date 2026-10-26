"""
QuantBIST RC5
Portfolio Repository

Portfolio data access layer.
"""

from __future__ import annotations

import pandas as pd

from core.config.paths import PORTFOLIO_FILE
from core.infrastructure.exceptions import (
    PortfolioRepositoryError,
    PortfolioValidationError,
)
from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)





# =====================================================
# CONFIGURATION
# =====================================================



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


    "lot":
        "quantity",

    "lots":
        "quantity",

    "adet":
        "quantity",

    "miktar":
        "quantity",

    "qty":
        "quantity",



    "ticker":
        "symbol",

    "code":
        "symbol",



    "close":
        "price",

    "cost":
        "price",



    "total":
        "value",

    "amount":
        "value",

    "tutar":
        "value",

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


    df = df.rename(


        columns=COLUMN_ALIASES,


    )


    return df






def _clean_symbol(
    df: pd.DataFrame,
) -> pd.DataFrame:


    if "symbol" in df.columns:

        df["symbol"] = (

            df["symbol"]

            .astype(str)

            .str.strip()

            .str.upper()

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
            "Creating portfolio value column."
        )


        df["value"] = (

            df["price"]

            *

            df["quantity"]

        )


    return df






def _convert_numeric_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:


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
    Validate required columns.
    """


    missing = [

        column

        for column in REQUIRED_COLUMNS

        if column not in df.columns

    ]



    if missing:


        raise PortfolioValidationError(

            "Missing required columns: "

            +

            ", ".join(missing)

        )






def _validate_values(
    df: pd.DataFrame,
) -> None:
    """
    Validate portfolio values.
    """


    if df.empty:

        raise PortfolioValidationError(

            "Portfolio dataframe is empty."

        )




    if (

        (df["price"] < 0).any()

        or

        (df["quantity"] < 0).any()

        or

        (df["value"] < 0).any()

    ):


        raise PortfolioValidationError(

            "Portfolio contains negative values."

        )




    if df["symbol"].duplicated().any():


        raise PortfolioValidationError(

            "Duplicate portfolio symbols detected."

        )






# =====================================================
# PUBLIC API
# =====================================================


def _ledger_portfolio(ledger_path=None, prices=None) -> pd.DataFrame | None:
    """
    Open positions from the trade ledger (real account first, else paper),
    valued at the last final close. None when the ledger has no open position,
    so the dashboard keeps working with the sample CSV.
    """

    try:
        from core.ledger import load_ledger, open_positions

        entries = load_ledger(ledger_path)
    except Exception as exc:  # noqa: BLE001 - a broken ledger must not break the dashboard
        logger.warning("Ledger not used for the dashboard | %s", exc)
        return None

    for account in ("real", "paper"):
        positions = open_positions(entries, account)
        if not positions:
            continue
        if prices is None:
            from core.reports.daily import raw_bars

            def price_of(symbol):
                bars = raw_bars(symbol)
                return float(bars["close"].iloc[-1]) if not bars.empty else float("nan")
        else:
            price_of = prices.get
        rows = []
        for p in positions:
            price = price_of(p.symbol)
            rows.append({"symbol": p.symbol, "price": price, "quantity": p.quantity, "value": p.quantity * price})
        df = pd.DataFrame(rows).dropna(subset=["price"])
        if df.empty:
            continue
        df.attrs["source"] = f"işlem defteri ({'gerçek' if account == 'real' else 'sanal'} hesap)"
        return df
    return None


def load_portfolio() -> pd.DataFrame:
    """
    Load and validate the portfolio: open positions from the trade ledger when
    there are any, otherwise the sample file data/portfolio_model.csv.
    df.attrs["source"] says which one was used.
    """


    logger.info(
        "Loading portfolio..."
    )



    try:

        df = _ledger_portfolio()

        if df is None:

            if not PORTFOLIO_FILE.exists():
                raise PortfolioRepositoryError(f"Portfolio file not found: {PORTFOLIO_FILE}")

            df = pd.read_csv(PORTFOLIO_FILE, encoding="utf-8")
            df.attrs["source"] = "örnek (data/portfolio_model.csv)"

            if df.empty:
                raise PortfolioValidationError("Portfolio file is empty.")

        source = df.attrs.get("source", "")

        df = _normalize_columns(df)



        df = _clean_symbol(df)



        df = _create_missing_columns(df)



        df = _convert_numeric_columns(df)



        _validate_schema(df)



        _validate_values(df)





        logger.info(

            "Portfolio repository ready | Rows=%d",

            len(df),

        )




        out = df.copy()
        out.attrs["source"] = source
        return out





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
