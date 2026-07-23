"""
QuantBIST RC6
Decision Intelligence Models

Single source of truth for:

- Dashboard
- API
- Reports
- Telegram
- AI Explanation
"""

from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum





# =====================================================
# ENUMS
# =====================================================


class DecisionAction(Enum):

    STRONG_BUY = "STRONG BUY"

    BUY = "BUY"

    ACCUMULATE = "ACCUMULATE"

    WATCH = "WATCH"

    HOLD = "HOLD"

    REDUCE = "REDUCE"

    SELL = "SELL"

    STRONG_SELL = "STRONG SELL"





class RiskLevel(Enum):

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    VERY_HIGH = "VERY_HIGH"

    CRITICAL = "CRITICAL"





class PriorityLevel(Enum):

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


    # =================================================
    # Identity
    # =================================================


    decision_id: str = ""


    timestamp: datetime = field(
        default_factory=datetime.now
    )


    engine_version: str = "RC6"





    # =================================================
    # Final Decision
    # =================================================


    action: str = DecisionAction.HOLD.value


    score: int = 0


    ai_score: int = 0


    confidence: int = 0


    priority: str = PriorityLevel.NORMAL.value


    summary: str = ""


    recommendation: str = ""







    # =================================================
    # AI Intelligence
    # =================================================


    ai_explanation: list[str] = field(
        default_factory=list
    )


    explanation_text: str = ""


    score_breakdown: dict[str, float] = field(
        default_factory=dict
    )


    decision_context: dict[str, str] = field(
        default_factory=dict
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
        default_factory=list
    )


    warnings: list[str] = field(
        default_factory=list
    )


    suggestions: list[str] = field(
        default_factory=list
    )








    # =====================================================
    # SIGNALS
    # =====================================================


    @property
    def buy_signal(self):

        return self.action in (

            DecisionAction.STRONG_BUY.value,

            DecisionAction.BUY.value,

            DecisionAction.ACCUMULATE.value,

        )




    @property
    def accumulate_signal(self):

        return self.action == DecisionAction.ACCUMULATE.value




    @property
    def strong_buy_signal(self):

        return self.action == DecisionAction.STRONG_BUY.value




    @property
    def sell_signal(self):

        return self.action in (

            DecisionAction.REDUCE.value,

            DecisionAction.SELL.value,

            DecisionAction.STRONG_SELL.value,

        )




    @property
    def rebalance_signal(self):

        return self.rebalance_required




    @property
    def high_confidence(self):

        return self.confidence >= 80




    @property
    def critical(self):

        return (

            self.priority.upper()

            ==

            PriorityLevel.CRITICAL.value

        )






    # =====================================================
    # DASHBOARD OUTPUTS
    # =====================================================


    @property
    def summary_dict(self):

        return {

            "action":
                self.action,


            "score":
                self.ai_score,


            "confidence":
                self.confidence,


            "priority":
                self.priority,


            "risk":
                self.risk_level,


            "market":
                self.market_regime,


            "trend":
                self.market_trend,


            "rebalance":
                self.rebalance_required,

        }







    @property
    def intelligence_dict(self):

        return {


            "action":
                self.action,


            "score":
                self.ai_score,


            "recommendation":
                self.recommendation,


            "reasons":
                self.reasons,


            "warnings":
                self.warnings,


            "suggestions":
                self.suggestions,


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