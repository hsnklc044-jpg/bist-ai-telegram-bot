"""
QuantBIST
Yearly statement from the ledger: realized sales (FIFO cost, fees included), net dividends and
fees paid, for one account and calendar year.

    python -m core.reports.annual 2026          # real account
    python -m core.reports.annual 2026 sanal    # paper account

A statement of the records, not tax advice: no inflation indexing, exemptions or withholding
rules are applied.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date

from core.ledger.book import Entry, Position, _ordered, load_ledger

ACCOUNT_WORDS = {"gerçek": "real", "gercek": "real", "real": "real", "sanal": "paper", "paper": "paper"}
ACCOUNT_NAMES = {"real": "Gerçek hesap", "paper": "Sanal hesap"}


@dataclass(frozen=True)
class Sale:
    day: date
    symbol: str
    quantity: float
    proceeds: float  # quantity × price − fee
    cost: float  # FIFO cost of the shares sold, buy fees included

    @property
    def result(self) -> float:
        return self.proceeds - self.cost


@dataclass(frozen=True)
class Dividend:
    day: date
    symbol: str
    quantity: float
    amount: float  # net (withholding already deducted, as entered)


@dataclass
class Statement:
    year: int
    account: str
    sales: list[Sale] = field(default_factory=list)
    dividends: list[Dividend] = field(default_factory=list)
    fees: float = 0.0

    @property
    def total(self) -> float:
        return sum(s.result for s in self.sales) + sum(d.amount for d in self.dividends)


def statement(entries: list[Entry], year: int, account: str = "real") -> Statement:
    """Replays the whole ledger (earlier years set the FIFO cost) and keeps what happened in `year`."""

    result = Statement(year, account)
    positions: dict[str, Position] = {}
    for e in _ordered(entries):
        if e.account != account or e.date.year > year:
            continue
        position = positions.setdefault(e.symbol, Position(account, e.symbol))
        before = position.realized
        position.apply(e)
        if e.date.year != year:
            continue
        result.fees += e.fee
        if e.side == "sell":
            proceeds = e.quantity * e.price - e.fee
            result.sales.append(Sale(e.date, e.symbol, e.quantity, proceeds, proceeds - (position.realized - before)))
        elif e.side == "dividend":
            result.dividends.append(Dividend(e.date, e.symbol, e.quantity, e.quantity * e.price))
    return result


def format_statement(s: Statement) -> str:
    from core.reports.daily import tr

    def tl(x: float) -> str:
        return f"{tr(x, 2)} TL"

    lines = [f"📒 {s.year} yılı dökümü – {ACCOUNT_NAMES.get(s.account, s.account)}", ""]
    if s.sales:
        lines.append("Satışlar (FIFO maliyet, komisyon dahil):")
        for x in s.sales:
            lines.append(f"  {x.day:%d.%m} {x.symbol.removesuffix('.IS')} {x.quantity:g} adet: satış {tl(x.proceeds)}, "
                         f"maliyet {tl(x.cost)}, sonuç {tl(x.result)}")
        lines.append(f"  Satışların toplam sonucu: {tl(sum(x.result for x in s.sales))}")
    else:
        lines.append("Satışlar: yıl içinde satış yok.")
    if s.dividends:
        lines += ["", "Temettüler (net, stopaj düşülmüş olarak girildiği gibi):"]
        lines += [f"  {d.day:%d.%m} {d.symbol.removesuffix('.IS')} {d.quantity:g} pay: {tl(d.amount)}" for d in s.dividends]
        lines.append(f"  Toplam: {tl(sum(d.amount for d in s.dividends))}")
    lines += [
        "",
        f"Yıl içinde ödenen komisyon: {tl(s.fees)}",
        f"Satış sonucu + temettü: {tl(s.total)}",
        "",
        "Defterdeki kayıtların dökümüdür; vergi danışmanlığı değildir. Enflasyon endekslemesi, istisna ve "
        "stopaj kuralları uygulanmadı; beyan için mali müşavire danışın.",
    ]
    return "\n".join(lines)


def parse_args(args: list[str], today: date) -> tuple[int, str]:
    """[yıl] [gerçek|sanal] in any order; defaults: this year, the real account."""

    year, account = today.year, "real"
    for word in args:
        word = word.strip().lower()
        if word.isdigit() and len(word) == 4:
            year = int(word)
        elif word in ACCOUNT_WORDS:
            account = ACCOUNT_WORDS[word]
        else:
            raise ValueError("Kullanım: /yil [2026] [gerçek|sanal]")
    return year, account


def annual_text(args: list[str], today: date, path=None) -> str:
    try:
        year, account = parse_args(args, today)
    except ValueError as exc:
        return str(exc)
    return format_statement(statement(load_ledger(path), year, account))


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.market.calendar import now_istanbul

    utf8_output()
    parser = argparse.ArgumentParser(description="Yearly statement from the ledger")
    parser.add_argument("words", nargs="*", help="[yıl] [gerçek|sanal]")
    print(annual_text(parser.parse_args(argv).words, now_istanbul().date()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Dividend", "Sale", "Statement", "annual_text", "format_statement", "parse_args", "statement"]
