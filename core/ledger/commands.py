"""
QuantBIST
Parsing of ledger commands typed in Telegram (no Telegram imports, so it can be tested).

    /trade al THYAO 100 285,50 [komisyon] [GG.AA.YYYY]
    /trade sat THYAO 40 290,25
    /trade bedelsiz THYAO 900
    /trade bedelli THYAO 100 [fiyat=1]
    /trade temettü THYAO 100 3,25 [GG.AA.YYYY]
    /paper al THYAO 100
    /paper sat THYAO 50
    /paper iptal 3
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from core.ledger.book import LedgerError

SIDES = {
    "al": "buy", "alış": "buy", "alis": "buy", "buy": "buy",
    "sat": "sell", "satış": "sell", "satis": "sell", "sell": "sell",
    "bedelsiz": "bonus", "bonus": "bonus",
    "bedelli": "rights", "rights": "rights",
    "temettü": "dividend", "temettu": "dividend", "dividend": "dividend",
}

TRADE_USAGE = (
    "Kullanım:\n"
    "/trade al THYAO 100 285,50 [komisyon] [GG.AA.YYYY]\n"
    "/trade sat THYAO 40 290,25\n"
    "/trade bedelsiz THYAO 900\n"
    "/trade bedelli THYAO 100 [fiyat, varsayılan 1]\n"
    "/trade temettü THYAO 100 3,25 [GG.AA.YYYY] (100 pay, pay başına net 3,25 TL)"
)
PAPER_USAGE = (
    "Kullanım:\n/paper al THYAO 100\n/paper al THYAO 100 gerekçeniz (isteğe bağlı, kayda geçer)\n"
    "/paper sat THYAO 50\n/paper iptal 3\n/paper (bekleyen emirler)"
)


def parse_number(text: str) -> float:
    """'285,50' -> 285.5; '1.234,5' -> 1234.5; '1234.5' -> 1234.5"""

    s = text.strip().replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError as exc:
        raise LedgerError(f"sayı anlaşılamadı: {text!r}") from exc


def parse_date(text: str) -> date:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise LedgerError(f"tarih anlaşılamadı: {text!r} (GG.AA.YYYY)")


def _side(word: str) -> str:
    side = SIDES.get(word.strip().lower())
    if side is None:
        raise LedgerError(f"işlem türü anlaşılamadı: {word!r} (al, sat, bedelsiz, bedelli, temettü)")
    return side


@dataclass(frozen=True)
class TradeCommand:
    side: str
    symbol: str
    quantity: float
    price: float
    fee: float | None  # None = use the default commission
    day: date | None  # None = today


def parse_trade(args: list[str]) -> TradeCommand:
    if len(args) < 3:
        raise LedgerError(TRADE_USAGE)
    side, symbol, quantity = _side(args[0]), args[1], parse_number(args[2])
    rest = args[3:]
    day = None
    if rest and any(c in rest[-1] for c in "./-") and rest[-1].count(".") + rest[-1].count("/") + rest[-1].count("-") == 2:
        day = parse_date(rest[-1])
        rest = rest[:-1]

    if side == "bonus":
        if rest:
            raise LedgerError("bedelsiz için yalnız adet yazılır: /trade bedelsiz THYAO 900")
        return TradeCommand(side, symbol, quantity, 0.0, 0.0, day)
    if side == "rights":
        price = parse_number(rest[0]) if rest else 1.0
        return TradeCommand(side, symbol, quantity, price, 0.0, day)
    if side == "dividend":
        if len(rest) != 1:
            raise LedgerError("temettü: /trade temettü THYAO 100 3,25 (pay adedi, pay başına net tutar)")
        return TradeCommand(side, symbol, quantity, parse_number(rest[0]), 0.0, day)
    if not rest:
        raise LedgerError("fiyat eksik.\n" + TRADE_USAGE)
    price = parse_number(rest[0])
    fee = parse_number(rest[1]) if len(rest) > 1 else None
    return TradeCommand(side, symbol, quantity, price, fee, day)


@dataclass(frozen=True)
class PaperCommand:
    action: str  # "order" | "cancel" | "list"
    side: str | None = None
    symbol: str | None = None
    quantity: float | None = None
    order_id: int | None = None
    reason: str = ""


def parse_paper(args: list[str]) -> PaperCommand:
    if not args:
        return PaperCommand("list")
    if args[0].lower() in ("iptal", "cancel"):
        if len(args) != 2 or not args[1].isdigit():
            raise LedgerError(PAPER_USAGE)
        return PaperCommand("cancel", order_id=int(args[1]))
    if len(args) < 3:
        raise LedgerError(PAPER_USAGE)
    side = _side(args[0])
    if side not in ("buy", "sell"):
        raise LedgerError("sanal hesapta yalnız al ve sat emri verilir")
    return PaperCommand("order", side, args[1], parse_number(args[2]), reason=" ".join(args[3:]))


__all__ = ["parse_number", "parse_date", "parse_trade", "parse_paper", "TradeCommand", "PaperCommand",
           "TRADE_USAGE", "PAPER_USAGE"]
