"""
QuantBIST Framework
Investment Committee Models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# =====================================================
# ENUMS
# =====================================================

class Vote(Enum):
    """
    Committee vote.
    """

    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    SELL = "SELL"


class CommitteeMember(Enum):
    """
    Committee members.
    """

    PORTFOLIO_MANAGER = "Portfolio Manager"

    MARKET_ANALYST = "Market Analyst"

    RISK_MANAGER = "Risk Manager"

    AI_ANALYST = "AI Analyst"


# =====================================================
# MEMBER VOTE
# =====================================================

@dataclass(slots=True)
class CommitteeVote:
    """
    Single committee member vote.
    """

    member: CommitteeMember

    vote: Vote

    confidence: int

    score: float

    summary: str


# =====================================================
# COMMITTEE RESULT
# =====================================================

@dataclass(slots=True)
class CommitteeResult:
    """
    Final committee decision.
    """

    action: Vote

    confidence: int

    score: float

    priority: str

    summary: str

    votes: list[CommitteeVote] = field(
        default_factory=list,
    )

    consensus: float = 0.0

    created_at: datetime = field(
        default_factory=datetime.now,
    )

    @property
    def unanimous(self) -> bool:
        """
        True if every member voted the same.
        """

        if not self.votes:
            return False

        first_vote = self.votes[0].vote

        return all(
            vote.vote == first_vote
            for vote in self.votes
        )

    @property
    def buy_signal(self) -> bool:
        """
        Buy recommendation?
        """

        return self.action in (
            Vote.STRONG_BUY,
            Vote.BUY,
        )

    @property
    def sell_signal(self) -> bool:
        """
        Sell recommendation?
        """

        return self.action in (
            Vote.REDUCE,
            Vote.SELL,
        )

    @property
    def high_confidence(self) -> bool:
        """
        High confidence decision?
        """

        return self.confidence >= 80

    @property
    def member_count(self) -> int:
        """
        Number of committee members.
        """

        return len(self.votes)