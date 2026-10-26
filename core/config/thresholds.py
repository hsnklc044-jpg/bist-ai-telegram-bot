"""
QuantBIST
Score thresholds.

Single place for every score -> action mapping. Change a
threshold here and every engine follows.
"""

from __future__ import annotations

# Portfolio-level decision and committee votes (score 0-100).
# Checked top to bottom; the first threshold the score reaches wins.
ACTION_LADDER: tuple[tuple[float, str], ...] = (
    (90, "STRONG BUY"),
    (75, "BUY"),
    (60, "ACCUMULATE"),
    (45, "HOLD"),
    (30, "REDUCE"),
    (15, "SELL"),
)
LOWEST_ACTION = "STRONG SELL"

# Single-stock technical signal (core.analytics.scoring).
SIGNAL_STRONG_BUY = 85
SIGNAL_BUY = 70
SIGNAL_SELL = 35
SIGNAL_STRONG_SELL = 20

# Minimums for a stock to appear in the top signals list.
MIN_SIGNAL_SCORE = 50
MIN_SIGNAL_CONFIDENCE = 50


# How a technical signal is worded to users. The score has not passed a
# backtest, so it is presented as a technical view, not a buy/sell call.
SIGNAL_VIEW_LABELS = {
    "STRONG BUY": "Güçlü pozitif",
    "BUY": "Pozitif",
    "WATCH": "Nötr",
    "SELL": "Negatif",
    "STRONG SELL": "Güçlü negatif",
}


def action_for_score(score: float) -> str:
    """Map a 0-100 score onto ACTION_LADDER."""

    for threshold, action in ACTION_LADDER:
        if score >= threshold:
            return action

    return LOWEST_ACTION


__all__ = [
    "ACTION_LADDER",
    "LOWEST_ACTION",
    "SIGNAL_STRONG_BUY",
    "SIGNAL_BUY",
    "SIGNAL_SELL",
    "SIGNAL_STRONG_SELL",
    "MIN_SIGNAL_SCORE",
    "MIN_SIGNAL_CONFIDENCE",
    "SIGNAL_VIEW_LABELS",
    "action_for_score",
]
