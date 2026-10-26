"""
QuantBIST
Risk alert thresholds. Starting values; tune after observing real alerts.
"""

STOP_ATR_MULTIPLE = 2.0  # stop = highest close since entry - 2 x ATR(14)
STOP_NEAR_ATR = 0.5  # "near" when the close is within 0.5 x ATR of the stop
ATR_WINDOW = 14

RUN_UP_LONG_DAYS = 126
RUN_UP_LONG = 1.00  # +100% in 126 sessions
RUN_UP_SHORT_DAYS = 20
RUN_UP_SHORT = 0.50  # +50% in 20 sessions

LIMIT_MOVE = 0.095  # locked limit day: high == low and |change| >= 9.5%

TURNOVER_DAYS = 20
POSITION_TO_TURNOVER = 0.05  # position larger than 5% of average daily turnover
LIQUIDITY_TOP = 50  # turnover rank in the universe

CONCENTRATION = 0.25  # one stock above 25% of the account
ACCOUNT_DRAWDOWN = 0.15  # account value 15% below its peak

STALE_DAYS = 5  # last candle older than this many calendar days

# Portfolio level (core/alerts/portfolio.py)
VAR_DAYS = 250  # history for the 1-day loss estimate
VAR_MIN_DAYS = 60  # fewer common sessions: not computed (shown as unknown)
VAR_LEVEL = 0.95
VAR_LIMIT = 0.05  # 1-day 95% historical loss above 5% of the account
CORR_DAYS = 60
CORR_HIGH = 0.80  # two holdings moving together
CORR_PAIR_WEIGHT = 0.35  # ... that together are this share of the account
