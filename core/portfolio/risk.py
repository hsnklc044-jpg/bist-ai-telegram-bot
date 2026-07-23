"""
QuantBIST RC5
Portfolio Risk Engine
"""

from __future__ import annotations


from core.config.portfolio import (
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
)


from core.infrastructure.exceptions import (
    PortfolioError,
)


from core.infrastructure.logger import (
    get_logger,
)


from core.portfolio.models import (
    PortfolioRisk,
    PortfolioStats,
)



logger = get_logger(__name__)





# =====================================================
# HELPERS
# =====================================================


def _normalize(
    value: float,
) -> float:
    """
    Keep risk score between 0-100.
    """

    return round(

        max(

            0.0,

            min(

                value,

                100.0,

            ),

        ),

        2,

    )







def _drawdown_score(
    drawdown: float,
) -> float:
    """
    Drawdown risk contribution.
    """

    return max(

        0.0,

        drawdown,

    )







def _sharpe_penalty(
    sharpe: float,
) -> float:
    """
    Sharpe based risk adjustment.
    """


    if sharpe >= 2:

        return -10



    if sharpe >= 1:

        return 0



    if sharpe >= 0:

        return 10



    return 20







def _position_risk(
    positions: int,
) -> float:
    """
    Position concentration risk.
    """


    if positions <= 3:

        return 20



    if positions <= 5:

        return 10



    if positions <= 10:

        return 5



    return 0







def _risk_level(
    score: float,
) -> str:
    """
    Convert score into RC5 risk level.
    """


    if score < RISK_LOW:

        return "LOW"



    if score < RISK_MEDIUM:

        return "MEDIUM"



    if score < RISK_HIGH:

        return "HIGH"



    return "CRITICAL"







# =====================================================
# PUBLIC API
# =====================================================


def calculate_portfolio_risk(
    stats: PortfolioStats,
) -> PortfolioRisk:
    """
    Calculate RC5 portfolio risk profile.
    """



    logger.info(

        "Portfolio risk calculation started."

    )



    try:



        if stats.max_drawdown < 0:

            raise PortfolioError(

                "Maximum drawdown cannot be negative."

            )





        score = 0.0





        score += _drawdown_score(

            float(

                stats.max_drawdown

            )

        )





        score += _sharpe_penalty(

            float(

                stats.sharpe

            )

        )





        score += _position_risk(

            int(

                stats.positions

            )

        )





        score = _normalize(

            score,

        )





        level = _risk_level(

            score,

        )





        volatility = round(

            min(

                score,

                100,

            ),

            2,

        )





        summary = (

            f"{level} risk "

            f"(Score {score:.0f}/100)"

        )





        logger.info(

            "Risk completed | Level=%s Score=%.2f",

            level,

            score,

        )





        return PortfolioRisk(


            level=level,


            score=score,


            volatility=volatility,


            max_drawdown=stats.max_drawdown,


            sharpe=stats.sharpe,


            summary=summary,


        )







    except PortfolioError:

        raise





    except Exception as exc:


        logger.exception(

            "Portfolio risk calculation failed."

        )


        raise PortfolioError(

            str(exc)

        ) from exc







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "calculate_portfolio_risk",

]
