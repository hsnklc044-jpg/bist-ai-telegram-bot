"""
QuantBIST RC4
Decision Models
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Decision:
    """
    QuantBIST nihai yatırım kararı.

    Dashboard, Telegram, Morning Report ve
    gelecekteki API katmanı bu modeli kullanacaktır.
    """

    action: str
    score: int
    confidence: int
    priority: str
    summary: str

    portfolio_health: float
    portfolio_grade: str

    risk_level: str

    market_status: str
    market_trend: str
    market_regime: str

    best_symbol: str
    worst_symbol: str

    rebalance_required: bool

    reasons: list[str] = field(default_factory=list)

    suggestions: list[str] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)

    @property
    def buy_signal(self) -> bool:
        return self.action in (
            "BUY",
            "STRONG BUY",
        )

    @property
    def sell_signal(self) -> bool:
        return self.action in (
            "SELL",
            "REDUCE RISK",
        )

    @property
    def rebalance_signal(self) -> bool:
        return self.action == "REBALANCE"

    @property
    def healthy(self) -> bool:
        return self.portfolio_health >= 80

    @property
    def high_confidence(self) -> bool:
        return self.confidence >= 80

    @property
    def critical(self) -> bool:
        return self.priority.upper() == "CRITICAL"