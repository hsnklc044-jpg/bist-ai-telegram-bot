"""
QuantBIST RC5
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
    Committee voting actions.
    """

    STRONG_BUY = "STRONG BUY"

    BUY = "BUY"

    ACCUMULATE = "ACCUMULATE"

    WATCH = "WATCH"

    HOLD = "HOLD"

    REDUCE = "REDUCE"

    SELL = "SELL"

    STRONG_SELL = "STRONG SELL"




class PriorityLevel(Enum):
    """
    Committee priority level.
    """

    LOW = "LOW"

    NORMAL = "NORMAL"

    HIGH = "HIGH"

    CRITICAL = "CRITICAL"




class CommitteeMember(Enum):
    """
    AI Investment Committee Members.
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
    Individual committee member decision.
    """

    member: CommitteeMember

    vote: Vote

    confidence: int

    score: float

    summary: str


    reasoning: list[str] = field(
        default_factory=list,
    )



    @property
    def high_confidence(self) -> bool:
        """
        Member confidence check.
        """

        return self.confidence >= 80






# =====================================================
# COMMITTEE RESULT
# =====================================================


@dataclass(slots=True)
class CommitteeResult:
    """
    Final AI Investment Committee Decision.
    """

    action: Vote


    confidence: int


    score: float


    priority: str = PriorityLevel.NORMAL.value


    summary: str = ""



    votes: list[CommitteeVote] = field(
        default_factory=list,
    )



    # Consensus percentage
    # Example:
    # 85.0 = %85 agreement

    consensus: float = 0.0



    created_at: datetime = field(
        default_factory=datetime.now,
    )



    # =================================================
    # AI EXPLANATION
    # =================================================


    explanation: list[str] = field(
        default_factory=list,
    )



    decision_factors: dict[str, float] = field(
        default_factory=dict,
    )





    # =================================================
    # PROPERTIES
    # =================================================


    @property
    def action_value(
        self,
    ) -> str:
        """
        Return action string.
        """

        return self.action.value




    @property
    def unanimous(
        self,
    ) -> bool:
        """
        True if every member voted same.
        """

        if not self.votes:

            return False


        first_vote = self.votes[0].vote


        return all(

            vote.vote == first_vote

            for vote in self.votes

        )





    @property
    def buy_signal(
        self,
    ) -> bool:
        """
        Buy recommendation?
        """

        return self.action in (

            Vote.STRONG_BUY,

            Vote.BUY,

            Vote.ACCUMULATE,

        )





    @property
    def sell_signal(
        self,
    ) -> bool:
        """
        Sell recommendation?
        """

        return self.action in (

            Vote.REDUCE,

            Vote.SELL,

            Vote.STRONG_SELL,

        )





    @property
    def watch_signal(
        self,
    ) -> bool:
        """
        Watch recommendation?
        """

        return self.action in (

            Vote.WATCH,

            Vote.HOLD,

        )





    @property
    def high_confidence(
        self,
    ) -> bool:
        """
        High confidence decision?
        """

        return self.confidence >= 80





    @property
    def member_count(
        self,
    ) -> int:
        """
        Number of committee members.
        """

        return len(
            self.votes
        )





    @property
    def consensus_percent(
        self,
    ) -> int:
        """
        Consensus percentage.
        """

        return round(
            self.consensus
        )





    @property
    def critical(
        self,
    ) -> bool:
        """
        Critical committee decision?
        """

        return (

            self.priority.upper()

            ==

            PriorityLevel.CRITICAL.value

        )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "Vote",

    "PriorityLevel",

    "CommitteeMember",

    "CommitteeVote",

    "CommitteeResult",

]
