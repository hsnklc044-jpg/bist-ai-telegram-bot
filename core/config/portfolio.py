"""
QuantBIST Framework
Portfolio Configuration
"""

from __future__ import annotations

# =====================================================
# PORTFOLIO HEALTH
# =====================================================

HEALTH_EXCELLENT = 90.0
HEALTH_GOOD = 75.0
HEALTH_WARNING = 60.0

# =====================================================
# CASH MANAGEMENT
# =====================================================

IDEAL_CASH_RATIO = 10.0

# =====================================================
# POSITION LIMITS
# =====================================================

MIN_POSITIONS = 5
MAX_POSITIONS = 20

# Target position weight (%)
TARGET_POSITION_WEIGHT = 10.0

# Maximum allowed weight for a single position (%)
MAX_POSITION_WEIGHT = 25.0

# Maximum sector exposure (%)
MAX_SECTOR_WEIGHT = 35.0

# =====================================================
# PORTFOLIO RISK THRESHOLDS
# (% Maximum Drawdown)
# =====================================================

RISK_LOW = 10.0
RISK_MEDIUM = 20.0
RISK_HIGH = 35.0
RISK_CRITICAL = 50.0

# =====================================================
# REBALANCE
# =====================================================

REBALANCE_THRESHOLD = 5.0

# =====================================================
# OPTIMIZATION
# =====================================================

OPTIMAL_POSITION_COUNT = 10
MIN_POSITION_WEIGHT = 2.5

# =====================================================
# PORTFOLIO SCORING
# =====================================================

HEALTH_SCORE_MAX = 100.0
HEALTH_SCORE_MIN = 0.0

# =====================================================
# DIVERSIFICATION
# =====================================================

MIN_DIVERSIFICATION_SCORE = 50.0
TARGET_DIVERSIFICATION_SCORE = 80.0

# =====================================================
# DEFAULTS
# =====================================================

DEFAULT_CASH_RATIO = 10.0
DEFAULT_RISK_FREE_RATE = 0.0
