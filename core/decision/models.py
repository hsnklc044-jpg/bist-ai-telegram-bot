"""
QuantBIST RC5
Decision Intelligence Models
"""

from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum



# =====================================================
# ENUMS
# =====================================================


class DecisionAction(Enum):
    """
    Final AI decision actions.
    """

    STRONG_BUY = "STRONG BUY"

    BUY = "BUY"

    ACCUMULATE = "ACCUMULATE"

    WATCH = "WATCH"

    HOLD = "HOLD"

    REDUCE = "REDUCE"

    SELL = "SELL"

    STRONG_SELL = "STRONG SELL"




class RiskLevel(Enum):
    """
    Portfolio and market risk levels.
    """

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    VERY_HIGH = "VERY_HIGH"

    CRITICAL = "CRITICAL"




class PriorityLevel(Enum):
    """
    Decision priority levels.
    """

    LOW = "LOW"

    NORMAL = "NORMAL"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    CRITICAL = "CRITICAL"





# =====================================================
# DECISION MODEL
# =====================================================


@dataclass(slots=True)
class Decision:
    """
    QuantBIST RC5 Final AI Decision Model.

    Single source of truth:

    - Dashboard
    - API
    - Reports
    - Telegram
    - AI Explanation

    """



    # =================================================
    # Identity
    # =================================================


    decision_id: str = ""


    timestamp: datetime = field(
        default_factory=datetime.now,
    )


    engine_version: str = "RC5"




    # =================================================
    # Final Decision
    # =================================================


    action: str = DecisionAction.HOLD.value


    score: int = 0


    confidence: int = 0


    priority: str = PriorityLevel.NORMAL.value


    summary: str = ""




    # =================================================
    # AI Intelligence
    # =================================================


    ai_score: int = 0


    ai_explanation: list[str] = field(
        default_factory=list,
    )


    explanation_text: str = ""



    score_breakdown: dict[str, float] = field(
        default_factory=dict,
    )


    decision_context: dict[str, str] = field(
        default_factory=dict,
    )





    # =================================================
    # Technical Intelligence
    # =================================================


    technical_score: float = 0.0


    technical_trend: str = ""


    rsi: float = 0.0


    macd_signal: str = ""





    # =================================================
    # Committee Intelligence
    # =================================================


    committee_action: str = ""


    committee_score: float = 0.0


    committee_consensus: float = 0.0





    # =================================================
    # Portfolio Intelligence
    # =================================================


    portfolio_health: float = 0.0


    portfolio_grade: str = ""


    best_symbol: str = ""


    worst_symbol: str = ""


    rebalance_required: bool = False





    # =================================================
    # Risk Intelligence
    # =================================================


    risk_level: str = RiskLevel.LOW.value


    risk_score: float = 0.0





    # =================================================
    # Market Intelligence
    # =================================================


    market_status: str = ""


    market_trend: str = ""


    market_regime: str = ""





    # =================================================
    # Explanation Layer
    # =================================================


    reasons: list[str] = field(
        default_factory=list,
    )


    suggestions: list[str] = field(
        default_factory=list,
    )


    warnings: list[str] = field(
        default_factory=list,
    )





    # =================================================
    # SIGNAL PROPERTIES
    # =================================================


    @property
    def buy_signal(
        self,
    ) -> bool:

        return self.action in (

            DecisionAction.STRONG_BUY.value,

            DecisionAction.BUY.value,

            DecisionAction.ACCUMULATE.value,

        )




    @property
    def accumulate_signal(
        self,
    ) -> bool:

        return self.action == DecisionAction.ACCUMULATE.value





    @property
    def strong_buy_signal(
        self,
    ) -> bool:

        return self.action == DecisionAction.STRONG_BUY.value





    @property
    def sell_signal(
        self,
    ) -> bool:

        return self.action in (

            DecisionAction.REDUCE.value,

            DecisionAction.SELL.value,

            DecisionAction.STRONG_SELL.value,

        )





    @property
    def hold_signal(
        self,
    ) -> bool:

        return self.action in (

            DecisionAction.HOLD.value,

            DecisionAction.WATCH.value,

        )





    @property
    def watch_signal(
        self,
    ) -> bool:

        return self.action == DecisionAction.WATCH.value





    @property
    def rebalance_signal(
        self,
    ) -> bool:

        return self.rebalance_required





    @property
    def healthy(
        self,
    ) -> bool:

        return self.portfolio_health >= 80





    @property
    def high_confidence(
        self,
    ) -> bool:

        return self.confidence >= 80





    @property
    def critical(
        self,
    ) -> bool:

        return (

            self.priority.upper()

            ==

            PriorityLevel.CRITICAL.value

        )





    @property
    def risk_is_high(
        self,
    ) -> bool:

        return self.risk_level.upper() in (

            RiskLevel.HIGH.value,

            RiskLevel.VERY_HIGH.value,

            RiskLevel.CRITICAL.value,

        )





    @property
    def investable(
        self,
    ) -> bool:

        return (

            self.buy_signal

            and

            self.confidence >= 60

            and

            self.risk_level.upper()

            !=

            RiskLevel.CRITICAL.value

        )





    @property
    def market_bullish(
        self,
    ) -> bool:

        return (

            self.market_trend.upper()

            ==

            "BULLISH"

        )





    @property
    def risk_off(
        self,
    ) -> bool:

        return (

            self.market_regime.upper()

            ==

            "RISK_OFF"

        )





    # =================================================
    # DASHBOARD HELPERS
    # =================================================


    @property
    def summary_dict(
        self,
    ) -> dict:

        return {

            "action":
                self.action,


            "score":
                self.score,


            "confidence":
                self.confidence,


            "priority":
                self.priority,


            "risk":
                self.risk_level,


            "market":
                self.market_regime,


            "technical_score":
                self.technical_score,

        }





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "Decision",

    "DecisionAction",

    "RiskLevel",

    "PriorityLevel",

]