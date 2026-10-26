"""
QuantBIST
Score thresholds.

Single place for the technical score thresholds and their labels.
"""

from __future__ import annotations

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


__all__ = [
    "SIGNAL_STRONG_BUY",
    "SIGNAL_BUY",
    "SIGNAL_SELL",
    "SIGNAL_STRONG_SELL",
    "MIN_SIGNAL_SCORE",
    "MIN_SIGNAL_CONFIDENCE",
    "SIGNAL_VIEW_LABELS",
]
