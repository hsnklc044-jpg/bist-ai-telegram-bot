"""
QuantBIST
Project paths.

All file locations are resolved from the project root, so the
application works no matter which directory it is started from.
"""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data"
LOG_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports" / "output"

PORTFOLIO_FILE = DATA_DIR / "portfolio_model.csv"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
EQUITY_FILE = DATA_DIR / "equity_curve.csv"

WEB_DIR = ROOT_DIR / "core" / "web"
WEB_STATIC_DIR = WEB_DIR / "static"
WEB_TEMPLATES_DIR = WEB_DIR / "templates"

__all__ = [
    "ROOT_DIR",
    "DATA_DIR",
    "LOG_DIR",
    "REPORTS_DIR",
    "PORTFOLIO_FILE",
    "WATCHLIST_FILE",
    "EQUITY_FILE",
    "WEB_DIR",
    "WEB_STATIC_DIR",
    "WEB_TEMPLATES_DIR",
]
