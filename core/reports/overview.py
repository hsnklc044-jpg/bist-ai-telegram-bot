"""
QuantBIST
Read-only overview: what /summary and the web panel show.

Market state, both accounts and the open risk alerts, from the stored
prices and the personal records. It never downloads, never fills paper
orders and never writes a file (the daily report does those), so it can
be asked for at any time.

It contains no buy/sell call or "AI decision": no rule tested so far has
shown predictive power (python -m core.backtest.research).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from core.config.paths import ALERTS_LOG_FILE, LEDGER_FILE
from core.ledger.book import LedgerError
from core.ledger.service import alerts_text, portfolio_text
from core.market.universe import BENCHMARK, load_universe
from core.reports.daily import DISCLAIMER, adjusted_bars, market_section


@dataclass
class Overview:
    as_of: date | None
    market: list[str]
    portfolio: str
    alerts: str

    @property
    def text(self) -> str:
        title = f"📋 QuantBIST özet – {self.as_of:%d.%m.%Y} kapanışı" if self.as_of else (
            "📋 QuantBIST özet – fiyat verisi yok"
        )
        return "\n".join(
            [title, "", *self.market, "", self.portfolio, "", self.alerts, "", DISCLAIMER]
        )


def build_overview(
    universe: list[str] | None = None,
    ledger_path: Path | str | None = None,
    alerts_path: Path | str | None = None,
) -> Overview:
    universe = universe or load_universe()

    bench = adjusted_bars(BENCHMARK)
    frames = {s: adjusted_bars(s) for s in universe}
    frames = {s: df for s, df in frames.items() if not df.empty}

    if bench.empty:
        market = ["📊 Piyasa", "Fiyat verisi yok: python -m core.market.update çalıştırın."]
    else:
        market = market_section(frames, bench)

    try:
        portfolio = portfolio_text(ledger_path or LEDGER_FILE)
    except LedgerError as exc:
        portfolio = f"💼 Defter okunamadı: {exc}"

    return Overview(
        as_of=bench.index[-1].date() if not bench.empty else None,
        market=market,
        portfolio=portfolio,
        alerts=alerts_text(alerts_path or ALERTS_LOG_FILE),
    )


__all__ = ["Overview", "build_overview"]
