"""
QuantBIST Framework
System Configuration
"""

from __future__ import annotations

from pathlib import Path

# =====================================================
# PROJECT
# =====================================================

PROJECT_NAME = "QuantBIST"

VERSION = "RC4"

# =====================================================
# DIRECTORIES
# =====================================================

ROOT_DIR = Path(".")

DATA_DIR = ROOT_DIR / "data"

LOG_DIR = ROOT_DIR / "logs"

CACHE_DIR = ROOT_DIR / "cache"

# =====================================================
# FILES
# =====================================================

PORTFOLIO_FILE = DATA_DIR / "portfolio_model.csv"

BACKTEST_FILE = DATA_DIR / "backtest_results.csv"

EQUITY_FILE = DATA_DIR / "equity_curve.csv"

# =====================================================
# LOGGING
# =====================================================

LOG_LEVEL = "INFO"
