"""
QuantBIST RC4
Portfolio Optimizer
"""

from __future__ import annotations

from core.portfolio.repository import load_portfolio


TARGET_WEIGHT = 20.0
MAX_WEIGHT = 25.0


def optimize_portfolio() -> dict:
    """
    Portfolio allocation analysis.

    Returns
    -------
    dict
        Portfolio optimization results.
    """

    portfolio = load_portfolio()

    if portfolio.empty:

        return {

            "total_value": 0.0,

            "position_count": 0,

            "average_weight": 0.0,

            "largest_position": None,

            "largest_weight": 0.0,

            "smallest_position": None,

            "smallest_weight": 0.0,

            "concentration_risk": False,

            "rebalance": False,

            "weights": [],

            "suggestions": [],

        }

    total_value = float(portfolio["value"].sum())

    position_count = len(portfolio)

    average_weight = round(
        100 / position_count,
        2,
    )

    weights = []

    suggestions = []

    largest_position = None
    largest_weight = -1.0

    smallest_position = None
    smallest_weight = 101.0

    concentration_risk = False

    for _, row in portfolio.iterrows():

        symbol = row["symbol"]

        value = float(row["value"])

        weight = round(
            value / total_value * 100,
            2,
        )

        weights.append({

            "symbol": symbol,

            "value": round(value, 2),

            "weight": weight,

        })

        # Largest Position

        if weight > largest_weight:

            largest_weight = weight

            largest_position = symbol

        # Smallest Position

        if weight < smallest_weight:

            smallest_weight = weight

            smallest_position = symbol

        # Concentration Risk

        if weight > MAX_WEIGHT:

            concentration_risk = True

            suggestions.append(

                f"{symbol}: Reduce allocation ({weight:.2f}%)"

            )

        # Underweight

        elif weight < TARGET_WEIGHT / 2:

            suggestions.append(

                f"{symbol}: Consider increasing allocation ({weight:.2f}%)"

            )

    weights.sort(

        key=lambda item: item["weight"],

        reverse=True,

    )

    rebalance = concentration_risk or len(suggestions) > 0

    return {

        "total_value": round(total_value, 2),

        "position_count": position_count,

        "average_weight": average_weight,

        "largest_position": largest_position,

        "largest_weight": largest_weight,

        "smallest_position": smallest_position,

        "smallest_weight": smallest_weight,

        "concentration_risk": concentration_risk,

        "rebalance": rebalance,

        "weights": weights,

        "suggestions": suggestions,

    }