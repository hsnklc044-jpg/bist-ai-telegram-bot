"""
QuantBIST
Rebalancing helper (road plan part 2; 05.11.2026): how far each holding is from the user's OWN
target weight and the fewest whole-share trades that bring it back.

    /denge THYAO=30 ASELS=20 [bant=5] [sanal]

- Weights are of the account's value (shares at the last close; the paper account adds its cash).
- A holding with no target is left as it is; the targets plus those holdings may not pass 100%.
- A holding inside the band (default BAND points) is not traded: fewer trades, fewer costs.
- Trades are whole shares, rounded toward zero so a target is never overshot; a sale never passes
  the shares held. The cost line uses the research cost per side (0.15%).
Arithmetic only: no order is sent and nothing here says what to buy or sell.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BAND = 0.05
COST = 0.0015  # commission 0.10% + slippage 0.05% per side (RESEARCH_LOG)
USAGE = ("Kullanım: /denge THYAO=30 ASELS=20 [bant=5] [sanal] – hedef ağırlıklar yüzde olarak; bant içindeki "
         "sapmaya dokunulmaz. Hesap sonucu, öneri değil; emir verilmez.")
DISCLAIMER = "Hesap sonucudur, öneri değildir; emir verilmez. Karar ve sorumluluk kullanıcıdadır."


class RebalanceError(ValueError):
    pass


@dataclass
class Request:
    targets: dict[str, float]
    band: float = BAND
    account: str = "real"


@dataclass
class Row:
    symbol: str
    weight: float
    target: float | None
    lots: int = 0
    price: float | None = None


@dataclass
class Plan:
    rows: list[Row] = field(default_factory=list)
    cash_change: float = 0.0
    cost: float = 0.0
    unpriced: list[str] = field(default_factory=list)


def _number(text: str) -> float:
    try:
        return float(text.strip().lstrip("%").replace(",", "."))
    except ValueError as exc:
        raise RebalanceError(f"sayı okunamadı: {text!r}") from exc


def parse(words: list[str]) -> Request:
    from core.ledger.book import normalize_symbol

    targets, band, account = {}, BAND, "real"
    for word in words:
        low = word.lower()
        if low in ("sanal", "paper"):
            account = "paper"
        elif low in ("gercek", "gerçek", "real"):
            account = "real"
        elif low.startswith("bant="):
            band = _number(word.split("=", 1)[1]) / 100
            if not 0 <= band <= 0.5:
                raise RebalanceError("bant %0 ile %50 arasında olmalı")
        elif "=" in word:
            code, value = word.split("=", 1)
            weight = _number(value) / 100
            if not 0 <= weight <= 1:
                raise RebalanceError(f"{code}: hedef %0 ile %100 arasında olmalı")
            try:
                targets[normalize_symbol(code)] = weight
            except ValueError as exc:
                raise RebalanceError(str(exc)) from exc
        else:
            raise RebalanceError(f"anlaşılmadı: {word!r}")
    if not targets:
        raise RebalanceError("en az bir hedef yazın (ör. THYAO=30)")
    if sum(targets.values()) > 1 + 1e-9:
        raise RebalanceError(f"hedeflerin toplamı %{sum(targets.values()) * 100:.0f}; %100'ü geçemez")
    return Request(targets, band, account)


def plan(holdings: dict[str, tuple[float, float]], targets: dict[str, float], total: float, band: float = BAND,
         prices: dict[str, float] | None = None) -> Plan:
    """holdings: symbol -> (shares, last price); prices: last prices of target stocks not held."""

    out = Plan()
    if not total > 0:
        return out
    prices = prices or {}
    for symbol in sorted(set(holdings) | set(targets)):
        shares, price = holdings.get(symbol, (0.0, prices.get(symbol)))
        if price is None or not price > 0:
            out.unpriced.append(symbol)
            continue
        weight = shares * price / total
        target = targets.get(symbol)
        row = Row(symbol, weight, target, 0, price)
        if target is not None and abs(target - weight) > band:
            exact = (target - weight) * total / price
            lots = int(exact + (1e-9 if exact > 0 else -1e-9))  # toward zero (19,9999… is 20): never overshot
            row.lots = max(lots, -int(shares))
        out.rows.append(row)
        out.cash_change -= row.lots * price
        out.cost += abs(row.lots) * price * COST
    return out


def text(words: list[str], entries=None, bars=None) -> str:
    from core.reports.daily import tr

    try:
        request = parse(words)
    except RebalanceError as exc:
        return f"⚠️ {exc}\n{USAGE}" if words else USAGE
    if entries is None:
        from core.ledger.book import load_ledger

        entries = load_ledger()
    if bars is None:
        from core.reports.daily import raw_bars as bars
    from core.ledger.book import cash_balance, open_positions

    def last(symbol):
        df = bars(symbol)
        return float(df["close"].iloc[-1]) if df is not None and len(df) else None

    holdings = {p.symbol: (p.quantity, last(p.symbol)) for p in open_positions(entries, request.account)}
    free = {s: w for s, w in request.targets.items() if s not in holdings}
    prices = {s: last(s) for s in free}
    total = sum(q * p for q, p in holdings.values() if p)
    if request.account == "paper":
        total += cash_balance(entries, "paper")
    untargeted = sum(q * p for s, (q, p) in holdings.items() if p and s not in request.targets) / total if total else 0
    if sum(request.targets.values()) + untargeted > 1 + 1e-9:
        share = f"%{untargeted * 100:.1f}".replace(".", ",")
        return f"⚠️ Hedeflerin toplamı ile hedefi yazılmamış hisselerin bugünkü payı ({share}) %100'ü geçiyor.\n{USAGE}"
    result = plan(holdings, request.targets, total, request.band, prices)
    name = "Sanal hesap" if request.account == "paper" else "Gerçek hesap"
    lines = [f"⚖️ Yeniden dengeleme hesabı – {name}, değer {tr(total)} TL, bant ±{request.band * 100:g} puan"]
    if not total > 0:
        return "\n".join([*lines, "Hesapta değer yok.", DISCLAIMER])
    for r in result.rows:
        code = r.symbol.removesuffix(".IS")
        weight = f"%{r.weight * 100:.1f}".replace(".", ",")
        if r.target is None:
            lines.append(f"  {code}: {weight} (hedef yok, dokunulmadı)")
            continue
        goal = f"%{r.target * 100:.1f}".replace(".", ",")
        action = ("bant içinde, işlem yok" if not r.lots else
                  f"{'al' if r.lots > 0 else 'sat'} {abs(r.lots)} adet × ~{tr(r.price, 2)} = ~{tr(abs(r.lots) * r.price)} TL")
        lines.append(f"  {code}: {weight} → hedef {goal}: {action}")
    if result.unpriced:
        lines.append("Fiyatı bulunamadı: " + ", ".join(s.removesuffix(".IS") for s in result.unpriced))
    lines.append(f"Nakit etkisi: {'+' if result.cash_change >= 0 else '-'}{tr(abs(result.cash_change))} TL; tahmini "
                 f"maliyet ~{tr(result.cost)} TL (işlem başına %0,15). Vergi hariç.")
    lines.append("Son kapanış fiyatlarıyla; gerçek işlem fiyatı farklı olur.")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


__all__ = ["BAND", "Plan", "RebalanceError", "Request", "Row", "parse", "plan", "text"]
