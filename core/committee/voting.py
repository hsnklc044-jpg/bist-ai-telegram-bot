"""
QuantBIST Framework
Investment Committee Voting
"""

from __future__ import annotations

from collections import Counter

from core.committee.models import (
    CommitteeResult,
    CommitteeVote,
    Vote,
)

from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)


# =====================================================
# CONFIG
# =====================================================

VOTE_WEIGHTS = {

    Vote.STRONG_BUY: 5,

    Vote.BUY: 4,

    Vote.HOLD: 3,

    Vote.REDUCE: 2,

    Vote.SELL: 1,

}


# =====================================================
# HELPERS
# =====================================================

def _average_confidence(
    votes: list[CommitteeVote],
) -> int:
    """
    Average confidence.
    """

    if not votes:

        return 0

    return round(

        sum(

            vote.confidence

            for vote in votes

        )

        / len(votes)

    )


def _average_score(
    votes: list[CommitteeVote],
) -> float:
    """
    Average score.
    """

    if not votes:

        return 0.0

    return round(

        sum(

            vote.score

            for vote in votes

        )

        / len(votes),

        2,

    )


def _consensus(
    votes: list[CommitteeVote],
) -> float:
    """
    Committee consensus percentage.
    """

    if not votes:

        return 0.0

    counter = Counter(

        vote.vote

        for vote in votes

    )

    majority = max(
        counter.values()
    )

    return round(

        majority

        / len(votes)

        * 100,

        2,

    )


def _priority(
    confidence: int,
    consensus: float,
) -> str:
    """
    Decision priority.
    """

    if confidence >= 90 and consensus >= 90:

        return "CRITICAL"

    if confidence >= 80:

        return "HIGH"

    if confidence >= 60:

        return "MEDIUM"

    return "LOW"


# =====================================================
# PUBLIC API
# =====================================================

def conduct_vote(
    votes: list[CommitteeVote],
) -> CommitteeResult:
    """
    Execute committee voting.
    """

    logger.info(
        "Committee voting started."
    )

    if not votes:

        raise ValueError(
            "Committee contains no votes."
        )

    counter = Counter(

        vote.vote

        for vote in votes

    )

    action = counter.most_common(1)[0][0]

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

    summary = (

        f"{action.value} "

        f"({confidence}% confidence, "

        f"{consensus:.0f}% consensus)"

    )

    logger.info(
        "Committee decision: %s",
        action.value,
    )

    return CommitteeResult(

        action=action,

        confidence=confidence,

        score=score,

        priority=priority,

        summary=summary,

        votes=votes,

        consensus=consensus,

    )


# =====================================================
# EXPORTS
# =====================================================

__all__ = [

    "conduct_vote",

]