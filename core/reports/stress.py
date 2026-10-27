"""
QuantBIST
Portfolio stress test: what the open positions would have lost in the worst 1, 5 and 20 session
falls of XU100 in the stored history. The windows are found from the data (no hand-typed event
dates); each holding takes its own return over the same sessions, or XU100's when it has no
prices for them (then marked as assumed).

    python -m core.reports.stress            # real account
    python -m core.reports.stress sanal      # paper account

Information only: the past is not a forecast, and it gives no buy or sell advice.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import pandas as pd

LENGTHS = (1, 5, 20)
ACCOUNT_NAMES = {"real": "Gerçek hesap", "paper": "Sanal hesap"}


@dataclass(frozen=True)
class Window:
    sessions: int
    base: pd.Timestamp  # close before the fall
    end: pd.Timestamp  # close at the bottom
    market: float  # XU100 change over the window


@dataclass(frozen=True)
class Row:
    symbol: str
    value: float
    change: float
    assumed: bool  # no prices on these dates: XU100's change was used


@dataclass
class Scenario:
    window: Window
    rows: list[Row] = field(default_factory=list)

    @property
    def loss(self) -> float:
        return sum(r.value * r.change for r in self.rows)


def worst_windows(close: pd.Series, lengths=LENGTHS) -> list[Window]:
    """The worst `n`-session change of `close` for each n (one window per length)."""

    close = close.dropna()
    found = []
    for n in lengths:
        if len(close) <= n:
            continue
        change = close / close.shift(n) - 1
        end = change.idxmin()
        position = close.index.get_loc(end)
        found.append(Window(n, close.index[position - n], end, float(change.loc[end])))
    return found


def scenario(window: Window, values: dict[str, float], frames: dict[str, pd.DataFrame]) -> Scenario:
    result = Scenario(window)
    for symbol, value in values.items():
        close = frames.get(symbol, pd.DataFrame()).get("close", pd.Series(dtype=float))
        if window.base in close.index and window.end in close.index:
            result.rows.append(Row(symbol, value, float(close.loc[window.end] / close.loc[window.base] - 1), False))
        else:
            result.rows.append(Row(symbol, value, window.market, True))
    return result


def format_report(scenarios: list[Scenario], account: str, total: float) -> str:
    from core.reports.daily import DISCLAIMER, pct, tr

    lines = [f"🧯 Stres testi – {ACCOUNT_NAMES.get(account, account)}", ""]
    if not scenarios or not scenarios[0].rows:
        return "\n".join(lines + ["Açık pozisyon yok; test edilecek bir şey yok.", "", DISCLAIMER])
    lines.append("Bugünkü pozisyonlar, XU100'ün kayıtlı geçmişindeki en kötü düşüşleri yaşasaydı:")
    for s in scenarios:
        w = s.window
        share = f", hesabın {pct(s.loss / total)}" if total > 0 else ""
        lines.append(f"\n• en kötü {w.sessions} seans ({w.base:%d.%m.%Y} → {w.end:%d.%m.%Y}): XU100 {pct(w.market)}")
        lines.append(f"  pozisyonlar: {tr(s.loss)} TL{share}")
        for r in sorted(s.rows, key=lambda r: r.value * r.change):
            note = " (o tarihte verisi yok: XU100 varsayıldı)" if r.assumed else ""
            lines.append(f"    {r.symbol.removesuffix('.IS')}: {pct(r.change)} → {tr(r.value * r.change)} TL{note}")
    lines += [
        "",
        "Geçmiş bir tahmin değildir; daha kötüsü de olabilir. Nakit ve fiyat limitleri hesaba katılmadı.",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def stress_text(account: str = "real") -> str:
    from core.ledger import cash_balance, load_ledger
    from core.market.universe import BENCHMARK
    from core.reports.daily import adjusted_bars, value_holdings

    entries = load_ledger()
    holdings, invested = value_holdings(entries, account)
    values = {h.position.symbol: h.value for h in holdings if not pd.isna(h.value)}
    total = invested + (cash_balance(entries, account) if account == "paper" else 0.0)
    if not values:
        return format_report([], account, total)
    frames = {s: adjusted_bars(s) for s in values}
    windows = worst_windows(adjusted_bars(BENCHMARK)["close"])
    return format_report([scenario(w, values, frames) for w in windows], account, total)


def parse_account(words: list[str]) -> str:
    for word in words:
        if word.strip().lower() in ("sanal", "paper"):
            return "paper"
    return "real"


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="Portfolio stress test")
    parser.add_argument("words", nargs="*", help="[gerçek|sanal]")
    print(stress_text(parse_account(parser.parse_args(argv).words)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Row", "Scenario", "Window", "format_report", "parse_account", "scenario", "stress_text", "worst_windows"]
