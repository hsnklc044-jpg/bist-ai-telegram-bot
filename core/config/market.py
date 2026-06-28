"""
QuantBIST Framework
Market Configuration
"""

from __future__ import annotations

# =====================================================
# MARKET STATUS
# =====================================================

MARKET_OPEN = "OPEN"
MARKET_CLOSED = "CLOSED"

# =====================================================
# TRENDS
# =====================================================

TREND_BULLISH = "BULLISH"
TREND_NEUTRAL = "NEUTRAL"
TREND_BEARISH = "BEARISH"

# =====================================================
# MARKET BREADTH
# =====================================================

BREADTH_POSITIVE = "POSITIVE"
BREADTH_NEUTRAL = "NEUTRAL"
BREADTH_NEGATIVE = "NEGATIVE"

# =====================================================
# SENTIMENT
# =====================================================

SENTIMENT_GREED = "GREED"
SENTIMENT_NEUTRAL = "NEUTRAL"
SENTIMENT_FEAR = "FEAR"

# =====================================================
# REGIME
# =====================================================

REGIME_RISK_ON = "RISK_ON"
REGIME_NEUTRAL = "NEUTRAL"
REGIME_RISK_OFF = "RISK_OFF"

# =====================================================
# SCORING
# =====================================================

REGIME_RISK_ON_SCORE = 70
REGIME_NEUTRAL_SCORE = 45

BREADTH_POSITIVE_SCORE = 70
BREADTH_NEUTRAL_SCORE = 40

SENTIMENT_GREED_SCORE = 70
SENTIMENT_NEUTRAL_SCORE = 40