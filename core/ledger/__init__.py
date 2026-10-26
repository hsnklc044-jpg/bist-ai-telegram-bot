"""
QuantBIST
Trade ledger: the single record of what was bought and sold.

    data/ledger.csv   id,date,account,symbol,side,quantity,price,fee,note

Accounts: "real" (fills you report) and "paper" (simulated fills).
Sides:
    buy     quantity at price, plus fee
    sell    quantity at price, minus fee
    bonus   bedelsiz shares received (price 0); existing lots are split
    rights  bedelli shares subscribed at `price` (usually 1 TL)

The file is append-only. A mistake is corrected with a new row (for
example a sell that reverses a wrong buy), never by editing history.
Positions, average cost and realised profit are always recomputed
from the rows (FIFO), so they can be checked by hand.
"""

from core.ledger.book import (
    Entry,
    LedgerError,
    Lot,
    Position,
    append_entry,
    cash_balance,
    load_ledger,
    open_positions,
    replay,
)

__all__ = [
    "Entry",
    "LedgerError",
    "Lot",
    "Position",
    "append_entry",
    "cash_balance",
    "load_ledger",
    "open_positions",
    "replay",
]
