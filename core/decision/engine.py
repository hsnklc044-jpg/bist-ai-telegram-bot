"""
QuantBIST RC4
Decision Engine
"""

from __future__ import annotations

from core.analysis.engine import analyze
from core.ai.recommendation_engine import generate_recommendation
from core.decision.models import Decision


def generate_decision(
    stats,
    signals: list[dict],
) -> Decision:
    """
    QuantBIST merkezi karar motoru.

    Framework içerisindeki analiz motorlarını kullanarak
    nihai yatırım kararını üretir.

    Parameters
    ----------
    stats
        PortfolioStats nesnesi.

    signals
        Güncel sinyaller.
        (İleride AI ve Strategy Engine tarafından kullanılacaktır.)

    Returns
    -------
    Decision
    """

    # --------------------------------------------------
    # Analysis Engine
    # --------------------------------------------------

    analysis = analyze(stats)

    portfolio = analysis["portfolio"]

    market = analysis["market"]

    # --------------------------------------------------
    # AI Recommendation
    # --------------------------------------------------

    decision = generate_recommendation(

        portfolio=portfolio,

        market=market,

    )

    return decision