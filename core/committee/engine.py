"""
QuantBIST RC5
Investment Committee Engine
"""

from __future__ import annotations


from core.committee.models import (
    CommitteeMember,
    CommitteeResult,
    CommitteeVote,
    PriorityLevel,
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
# SCORE ADJUSTMENT
# =====================================================


def _adjust_score(
    member: CommitteeMember,
    score: float,
) -> float:
    """
    Member intelligence adjustment.
    """


    value = score



    adjustments = {

        CommitteeMember.AI_ANALYST: 10,

        CommitteeMember.MARKET_ANALYST: 5,

        CommitteeMember.RISK_MANAGER: -5,

        CommitteeMember.PORTFOLIO_MANAGER: 0,

    }



    value += adjustments.get(

        member,

        0,

    )



    return max(

        0,

        min(

            100,

            value,

        ),

    )






# =====================================================
# SCORE TO VOTE
# =====================================================


def _score_to_vote(
    score: float,
) -> Vote:
    """
    Convert intelligence score to vote.
    """


    if score >= 90:

        return Vote.STRONG_BUY



    if score >= 75:

        return Vote.BUY



    if score >= 60:

        return Vote.ACCUMULATE



    if score >= 45:

        return Vote.HOLD



    if score >= 30:

        return Vote.REDUCE



    if score >= 15:

        return Vote.SELL



    return Vote.STRONG_SELL






# =====================================================
# CONFIDENCE
# =====================================================


def _confidence(
    score: float,
) -> int:


    return max(

        50,

        min(

            99,

            int(round(score)),

        ),

    )






# =====================================================
# PRIORITY
# =====================================================


def _priority(
    votes: list[CommitteeVote],
) -> str:
    """
    Determine committee priority.
    """


    average = sum(

        vote.score

        for vote in votes

    ) / len(votes)



    if average < 30:

        return PriorityLevel.CRITICAL.value



    if average < 50:

        return PriorityLevel.HIGH.value



    if average >= 80:

        return PriorityLevel.LOW.value



    return PriorityLevel.NORMAL.value






# =====================================================
# SUMMARY
# =====================================================


def _summary(
    votes: list[CommitteeVote],
    result: CommitteeResult,
) -> str:


    return (

        f"Committee {result.action.value} | "

        f"Score {result.score:.1f} | "

        f"Confidence {result.confidence}%"

    )






# =====================================================
# EXPLANATION
# =====================================================


def _explanation(
    votes: list[CommitteeVote],
) -> list[str]:


    return [

        vote.summary

        for vote in votes

    ]






def _factors(
    votes: list[CommitteeVote],
) -> dict[str,float]:


    return {

        vote.member.value:

            vote.score

        for vote in votes

    }






# =====================================================
# PUBLIC API
# =====================================================


def run_committee(
    portfolio: PortfolioAnalysis,
    market: MarketStatus,
) -> CommitteeResult:
    """
    Execute Investment Committee.
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

                scorecard.get(
                    "portfolio",
                    50,
                ),

            ),


            (

                CommitteeMember.MARKET_ANALYST,

                scorecard.get(
                    "market",
                    50,
                ),

            ),


            (

                CommitteeMember.RISK_MANAGER,

                scorecard.get(
                    "risk",
                    50,
                ),

            ),


            (

                CommitteeMember.AI_ANALYST,

                scorecard.get(
                    "ai",
                    50,
                ),

            ),

        ]




        votes: list[CommitteeVote] = []



        for member, raw_score in members:


            score = _adjust_score(

                member,

                float(raw_score),

            )



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

                    summary=(

                        f"{member.value}: "

                        f"{vote.value} "

                        f"({score:.1f})"

                    ),

                    reasoning=[

                        f"Score contribution: {score:.1f}"

                    ],

                )

            )





        result = conduct_vote(

            votes,

        )





        result.priority = _priority(

            votes,

        )


        result.explanation = _explanation(

            votes,

        )


        result.decision_factors = _factors(

            votes,

        )


        result.summary = _summary(

            votes,

            result,

        )





        logger.info(

            "Committee finished | Action=%s Score=%.2f",

            result.action.value,

            result.score,

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
