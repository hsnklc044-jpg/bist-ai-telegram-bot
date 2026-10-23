"""
QuantBIST
Market Breadth Engine

Breadth measures how many stocks take part in a move, not how the
index itself looks. Computed over the stock universe on the latest
closed session:

- share of stocks above their 50-day average   (weight 0.5)
- share of stocks above their 200-day average  (weight 0.3)
- advancers / (advancers + decliners)           (weight 0.2)
"""

from __future__ import annotations

from core.infrastructure.exceptions import MarketError
from core.infrastructure.logger import get_logger
from core.market.data import load_price_history, preload
from core.market.models import BreadthStatus, MarketBreadth
from core.market.universe import load_universe

logger = get_logger(__name__)

MIN_STOCKS = 5


def _breadth_status(score: float) -> BreadthStatus:
    if score >= 70:
        return BreadthStatus.POSITIVE
    if score >= 45:
        return BreadthStatus.NEUTRAL
    return BreadthStatus.NEGATIVE


def calculate_market_breadth(
    symbol: str | None = None,
    symbols: list[str] | None = None,
) -> MarketBreadth:
    """
    Breadth over `symbols` (default: the universe file).

    `symbol` is accepted for backward compatibility and ignored:
    breadth is never computed from a single index.
    """

    symbols = symbols or load_universe()

    logger.info("Calculating market breadth | %d stocks", len(symbols))

    preload(symbols)

    above_50 = above_200 = with_200 = 0
    advancers = decliners = 0
    counted = 0

    for ticker in symbols:
        try:
            df = load_price_history(ticker)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Breadth skip | %s | %s", ticker, exc)
            continue

        close = df["close"]

        if len(close) < 51:
            continue

        counted += 1
        last = close.iloc[-1]

        if last > close.tail(50).mean():
            above_50 += 1

        if len(close) >= 200:
            with_200 += 1
            if last > close.tail(200).mean():
                above_200 += 1

        change = last - close.iloc[-2]
        if change > 0:
            advancers += 1
        elif change < 0:
            decliners += 1

    if counted < MIN_STOCKS:
        raise MarketError(f"Breadth needs at least {MIN_STOCKS} stocks, got {counted}.")

    pct_50 = above_50 / counted * 100
    pct_200 = above_200 / with_200 * 100 if with_200 else pct_50
    moving = advancers + decliners
    adv_ratio = advancers / moving * 100 if moving else 50.0

    score = round(pct_50 * 0.5 + pct_200 * 0.3 + adv_ratio * 0.2, 2)
    status = _breadth_status(score)

    factors = {
        "stocks": counted,
        "above_sma50_pct": round(pct_50, 1),
        "above_sma200_pct": round(pct_200, 1),
        "advancers": advancers,
        "decliners": decliners,
    }

    summary = (
        f"{status.value} breadth ({score:.0f}/100): "
        f"{above_50}/{counted} above SMA50, {advancers} up / {decliners} down"
    )

    logger.info("Market breadth completed | %s", summary)

    return MarketBreadth(
        status=status,
        score=score,
        summary=summary,
        factors=factors,
    )


__all__ = [
    "calculate_market_breadth",
]
