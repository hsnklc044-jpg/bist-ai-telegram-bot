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

WATCHLIST_FILE = DATA_DIR / "watchlist.json"
MARKET_DB = DATA_DIR / "market.db"
UNIVERSE_FILE = DATA_DIR / "universe.csv"

# Stage 2: trade ledger, paper orders and logs (plain CSV, append-only)
LEDGER_FILE = DATA_DIR / "ledger.csv"
PAPER_ORDERS_FILE = DATA_DIR / "paper_orders.csv"
ALERTS_LOG_FILE = DATA_DIR / "alerts_log.csv"
PRICE_ALARMS_FILE = DATA_DIR / "price_alarms.csv"
SCREENS_FILE = DATA_DIR / "screens.csv"
SCREEN_SUBSCRIPTIONS_FILE = DATA_DIR / "screen_subscriptions.csv"
SIGNAL_LOG_FILE = DATA_DIR / "signal_log.csv"
EQUITY_LOG_FILE = DATA_DIR / "equity_log.csv"

WEB_DIR = ROOT_DIR / "core" / "web"
WEB_TEMPLATES_DIR = WEB_DIR / "templates"

__all__ = [
    "ROOT_DIR",
    "DATA_DIR",
    "LOG_DIR",
    "REPORTS_DIR",
    "WATCHLIST_FILE",
    "MARKET_DB",
    "UNIVERSE_FILE",
    "LEDGER_FILE",
    "PAPER_ORDERS_FILE",
    "ALERTS_LOG_FILE",
    "PRICE_ALARMS_FILE",
    "SCREENS_FILE",
    "SCREEN_SUBSCRIPTIONS_FILE",
    "SIGNAL_LOG_FILE",
    "EQUITY_LOG_FILE",
    "WEB_DIR",
    "WEB_TEMPLATES_DIR",
]
