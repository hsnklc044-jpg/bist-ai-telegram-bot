"""
QuantBIST Framework
Investment Committee Engine
"""

from __future__ import annotations

from core.committee.models import (
    CommitteeMember,
    CommitteeResult,
    CommitteeVote,
    Vote,
)

from core.committee.scoring import (
    generate_scorecard,
)

from core.committee.voting import (
    conduct_vote,
)

from core.infrastructure.exceptions import (
    DecisionError,
)

from core.infrastructure.logger import (
    get_logger,
)

from core.market.models import (
    MarketStatus,
)

from core.portfolio.models import (
    PortfolioAnalysis,
)

logger = get_logger(__name__)


# =====================================================
# HELPERS
# =====================================================

def _score_to_vote(
    score: float,
) -> Vote:
    """
    Convert numeric score into committee vote.
    """

    if score >= 90:

        return Vote.STRONG_BUY

    if score >= 75:

        return Vote.BUY

    if score >= 55:

        return Vote.HOLD

    if score >= 35:

        return Vote.REDUCE

    return Vote.SELL


def _confidence(
    score: float,
) -> int:
    """
    Convert score into confidence.
    """

    return max(

        50,

        min(

            99,

            round(score),

        ),

    )


def _summary(
    member: CommitteeMember,
    vote: Vote,
    score: float,
) -> str:
    """
    Member vote summary.
    """

    return (

        f"{member.value}: "

        f"{vote.value} "

        f"({score:.1f})"

    )


# =====================================================
# PUBLIC API
# =====================================================

def run_committee(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> CommitteeResult:
    """
    Execute complete Investment Committee.
    """

    logger.info(
        "Investment Committee started."
    )

    try:

        scorecard = generate_scorecard(

            portfolio,

            market,

        )

        members = [

            (
                CommitteeMember.PORTFOLIO_MANAGER,
                scorecard["portfolio"],
            ),

            (
                CommitteeMember.MARKET_ANALYST,
                scorecard["market"],
            ),

            (
                CommitteeMember.RISK_MANAGER,
                scorecard["risk"],
            ),

            (
                CommitteeMember.AI_ANALYST,
                scorecard["ai"],
            ),

        ]

        votes: list[CommitteeVote] = []

        for member, score in members:

            vote = _score_to_vote(
                score,
            )

            votes.append(

                CommitteeVote(

                    member=member,

                    vote=vote,

                    confidence=_confidence(
                        score,
                    ),

                    score=round(
                        score,
                        2,
                    ),

                    summary=_summary(

                        member,

                        vote,

                        score,

                    ),

                )

            )

        result = conduct_vote(
            votes,
        )

        logger.info(

            "Investment Committee finished: %s",

            result.action.value,

        )

        return result

    except Exception as exc:

        logger.exception(
            "Investment Committee failed."
        )

        raise DecisionError(
            str(exc)
        ) from exc


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "run_committee",

]