"""
QuantBIST RC7
Investment Committee Voting Engine
"""

from __future__ import annotations


from collections import defaultdict


from core.committee.models import (
    CommitteeMember,
    CommitteeResult,
    CommitteeVote,
    Vote,
)


from core.infrastructure.exceptions import (
    DecisionError,
)


from core.infrastructure.logger import (
    get_logger,
)



logger = get_logger(__name__)





# =====================================================
# MEMBER WEIGHTS
# =====================================================


MEMBER_WEIGHTS = {

    CommitteeMember.AI_ANALYST: 2.5,

    CommitteeMember.MARKET_ANALYST: 2.0,

    CommitteeMember.PORTFOLIO_MANAGER: 1.5,

    CommitteeMember.RISK_MANAGER: 1.0,

}





# =====================================================
# NORMALIZER
# =====================================================


def _normalize_vote(value) -> Vote:
    """
    Convert any vote format to Vote enum.
    """

    if isinstance(value, Vote):

        return value



    if isinstance(value, dict):

        value = value.get(
            "action",
            "HOLD"
        )



    if isinstance(value, str):

        try:

            return Vote(value)


        except Exception:

            try:

                return Vote(
                    value.upper()
                )

            except Exception:

                return Vote.HOLD



    return Vote.HOLD





# =====================================================
# HELPERS
# =====================================================


def _average_confidence(
    votes: list[CommitteeVote],
) -> int:


    if not votes:

        return 0



    return round(

        sum(

            vote.confidence

            for vote in votes

        )

        /

        len(votes)

    )






def _average_score(
    votes: list[CommitteeVote],
) -> float:


    if not votes:

        return 0.0



    return round(

        sum(

            vote.score

            for vote in votes

        )

        /

        len(votes),

        2,

    )






def _consensus(
    votes: list[CommitteeVote],
) -> float:
    """
    Consensus percentage.
    """


    if not votes:

        return 0.0



    counter = defaultdict(int)



    for vote in votes:


        current_vote = _normalize_vote(

            vote.vote

        )


        counter[current_vote] += 1



    majority = max(

        counter.values()

    )



    return round(

        majority

        /

        len(votes)

        *

        100,

        2,

    )








def _weighted_vote(
    votes: list[CommitteeVote],
) -> Vote:
    """
    Weighted committee decision.
    """


    scores = defaultdict(float)



    for vote in votes:


        current_vote = _normalize_vote(

            vote.vote

        )



        weight = MEMBER_WEIGHTS.get(

            vote.member,

            1.0,

        )



        scores[current_vote] += weight



    if not scores:

        return Vote.HOLD



    return max(

        scores,

        key=scores.get,

    )








def _priority(
    confidence: int,
    consensus: float,
) -> str:


    if (

        confidence >= 90

        and

        consensus >= 75

    ):

        return "CRITICAL"




    if confidence >= 80:

        return "HIGH"




    if confidence >= 60:

        return "NORMAL"




    return "LOW"








def _summary(
    action: Vote,
    confidence: int,
    consensus: float,
) -> str:


    return (

        f"{action.value} | "

        f"Confidence {confidence}% | "

        f"Consensus {consensus:.0f}%"

    )








def _explanation(
    votes: list[CommitteeVote],
) -> list[str]:


    return [

        vote.summary

        for vote in votes

    ]








def _decision_factors(
    votes: list[CommitteeVote],
) -> dict[str, float]:


    return {


        vote.member.value:

            vote.score

        for vote in votes

    }








# =====================================================
# PUBLIC API
# =====================================================


def conduct_vote(
    votes: list[CommitteeVote],
) -> CommitteeResult:
    """
    Execute RC7 committee voting.
    """


    logger.info(

        "Committee voting started."

    )



    try:


        if not votes:

            raise DecisionError(

                "Committee contains no votes."

            )




        action = _weighted_vote(

            votes,

        )



        confidence = _average_confidence(

            votes,

        )



        score = _average_score(

            votes,

        )



        consensus = _consensus(

            votes,

        )



        priority = _priority(

            confidence,

            consensus,

        )



        summary = _summary(

            action,

            confidence,

            consensus,

        )





        result = CommitteeResult(


            action=action,


            confidence=confidence,


            score=score,


            priority=priority,


            summary=summary,


            votes=votes,


            consensus=consensus,


            explanation=_explanation(

                votes,

            ),


            decision_factors=_decision_factors(

                votes,

            ),

        )





        logger.info(

            "Committee decision completed | Action=%s Score=%.2f Consensus=%.2f",

            action.value,

            score,

            consensus,

        )



        return result






    except DecisionError:

        raise



    except Exception as exc:


        logger.exception(

            "Committee voting failed."

        )


        raise DecisionError(

            str(exc)

        ) from exc







# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "conduct_vote",

]