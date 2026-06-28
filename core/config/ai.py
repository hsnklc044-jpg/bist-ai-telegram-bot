"""
QuantBIST Framework
AI Configuration
"""

from __future__ import annotations

# =====================================================
# DECISION THRESHOLDS
# =====================================================

STRONG_BUY_SCORE = 90
BUY_SCORE = 75
WATCH_SCORE = 55
REDUCE_SCORE = 35

# =====================================================
# CONFIDENCE
# =====================================================

MIN_CONFIDENCE = 50
MAX_CONFIDENCE = 99
CONFIDENCE_OFFSET = 5

# =====================================================
# BASE SCORE
# =====================================================

BASE_SCORE = 50
MIN_SCORE = 0
MAX_SCORE = 100

# =====================================================
# PORTFOLIO HEALTH
# =====================================================

GRADE_A_SCORE = 25
GRADE_B_SCORE = 15
GRADE_C_SCORE = 5
GRADE_D_SCORE = -20

# =====================================================
# RISK
# =====================================================

LOW_RISK_SCORE = 20
MEDIUM_RISK_SCORE = 10
HIGH_RISK_SCORE = -10
CRITICAL_RISK_SCORE = -20

# =====================================================
# REBALANCE
# =====================================================

NO_REBALANCE_BONUS = 5
REBALANCE_PENALTY = -5

# =====================================================
# MARKET
# =====================================================

RISK_ON_SCORE = 25
MARKET_NEUTRAL_SCORE = 10
RISK_OFF_SCORE = -20

BREADTH_POSITIVE_SCORE = 10
BREADTH_NEUTRAL_SCORE = 5
BREADTH_NEGATIVE_SCORE = -10

GREED_SCORE = 10
FEAR_SCORE = -10