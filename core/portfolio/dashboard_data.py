"""
QuantBIST RC5
Portfolio Dashboard Adapter

Dashboard data preparation layer.
"""

from __future__ import annotations

from core.infrastructure.exceptions import (
    PortfolioError,
)
from core.infrastructure.logger import (
    get_logger,
)
from core.portfolio.models import (
    PortfolioStats,
)
from core.portfolio.repository import (
    load_portfolio,
)

logger = get_logger(__name__)





# =====================================================
# CONFIG
# =====================================================


DEFAULT_CASH = 729.0






# =====================================================
# PUBLIC API
# =====================================================


def get_dashboard_stats() -> PortfolioStats:
    """
    Build dashboard portfolio statistics.

    Dashboard
        ↓
    PortfolioStats
        ↓
    Portfolio Intelligence
        ↓
    Decision Engine

    """



    logger.info(

        "Preparing dashboard portfolio statistics..."

    )



    try:


        portfolio = load_portfolio()



        if portfolio.empty:


            logger.warning(

                "Portfolio is empty."

            )



            return PortfolioStats(


                portfolio=0.0,


                cash=DEFAULT_CASH,


                positions=0,


                top_stock="-",



                sharpe=0.0,


                win_rate=0.0,


                profit_factor=0.0,


                max_drawdown=0.0,


            )







        total_value = round(


            float(

                portfolio["value"].sum()

            ),


            2,


        )




        positions = len(

            portfolio

        )





        top_position = portfolio.loc[

            portfolio["value"].idxmax()

        ]





        top_stock = str(

            top_position["symbol"]

        )





        logger.info(


            "Dashboard portfolio prepared | Value=%s Positions=%s",


            total_value,


            positions,


        )





        return PortfolioStats(



            portfolio=total_value,



            cash=DEFAULT_CASH,



            positions=positions,



            top_stock=top_stock,



            # Future analytics engine placeholders

            sharpe=0.0,


            win_rate=0.0,


            profit_factor=0.0,


            max_drawdown=0.0,



        )






    except Exception as exc:



        logger.exception(


            "Dashboard portfolio preparation failed."

        )



        raise PortfolioError(

            str(exc)

        ) from exc






# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_dashboard_stats",

]
