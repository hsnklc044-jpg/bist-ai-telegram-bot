"""Cost, tick and capacity functions (QB-ARS-1 C-1..C-3; Faz C preparation, 18.11.2026).

Every value is the caller's: no parameter has a default, so a number can only come from a
pre-registration (docs/MALIYET_ONERI.md holds proposals; the owner decides). Limit-lock detection is
core.market.limits (K-75) and is not repeated here. Pure functions; nothing calls them yet.
"""

from __future__ import annotations

import math
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal


def _nonneg(**values: float) -> None:
    for name, v in values.items():
        if v is None or math.isnan(v) or v < 0:
            raise ValueError(f"{name} negatif ya da eksik olamaz: {v}")


def _check_table(table) -> list[tuple[float, float]]:
    rows = [(float(lo), float(tick)) for lo, tick in table]
    if not rows or rows[0][0] != 0.0:
        raise ValueError("fiyat adımı tablosu 0'dan başlamalı")
    for (lo1, t1), (lo2, _t2) in zip(rows, rows[1:], strict=False):
        if not lo2 > lo1:
            raise ValueError("tablo alt sınırları artan olmalı")
    if any(t <= 0 for _, t in rows):
        raise ValueError("fiyat adımı pozitif olmalı")
    if any(t2 < t1 for (_, t1), (_, t2) in zip(rows, rows[1:], strict=False)):
        raise ValueError("fiyat adımı fiyatla azalamaz")
    return rows


def round_to_tick(price: float, table, side: str = "nearest") -> float:
    """Price on the tick grid of its band. side: 'nearest', 'buy' (up) or 'sell' (down)."""

    rows = _check_table(table)
    _nonneg(price=price)
    tick = next(t for lo, t in reversed(rows) if price >= lo)
    mode = {"nearest": ROUND_HALF_UP, "buy": ROUND_CEILING, "sell": ROUND_FLOOR}[side]
    q = Decimal(str(tick))
    steps = (Decimal(str(price)) / q).to_integral_value(rounding=mode)
    return float(steps * q)


def one_way_cost(commission: float, bsmv_on_commission: float, exchange_fee: float, half_spread: float,
                 slippage: float) -> float:
    """Cost of one side as a share of the trade: commission with BSMV on it, exchange fee, half spread,
    slippage."""

    _nonneg(commission=commission, bsmv_on_commission=bsmv_on_commission, exchange_fee=exchange_fee,
            half_spread=half_spread, slippage=slippage)
    return commission * (1 + bsmv_on_commission) + exchange_fee + half_spread + slippage


def slippage(order_tl: float, adv_tl: float, base: float, impact: float) -> float:
    """Liquidity-scaled slippage: base + impact * sqrt(order / average daily traded value)."""

    _nonneg(order_tl=order_tl, adv_tl=adv_tl, base=base, impact=impact)
    if adv_tl == 0:
        return math.inf
    return base + impact * math.sqrt(order_tl / adv_tl)


def within_capacity(order_tl: float, adv_tl: float, max_share: float) -> bool:
    """C-3: the position may not exceed max_share of the average daily traded value."""

    _nonneg(order_tl=order_tl, adv_tl=adv_tl, max_share=max_share)
    return adv_tl > 0 and order_tl <= max_share * adv_tl
