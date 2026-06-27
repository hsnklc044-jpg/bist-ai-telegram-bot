"""
QuantBIST RC4
Portfolio Allocator
"""

from __future__ import annotations

from core.portfolio.optimizer import optimize_portfolio


def calculate_target_allocations() -> dict:
    """
    Portfolio için hedef ağırlıkları hesaplar.

    Returns
    -------
    dict
        {
            "target_weight": float,
            "needs_rebalance": bool,
            "allocations": list,
        }
    """

    optimization = optimize_portfolio()

    weights = optimization["weights"]

    if not weights:

        return {

            "target_weight": 0.0,

            "needs_rebalance": False,

            "allocations": [],

        }

    position_count = len(weights)

    target_weight = round(
        100 / position_count,
        2,
    )

    allocations = []

    needs_rebalance = False

    tolerance = 5.0

    for item in weights:

        current_weight = item["weight"]

        difference = round(
            current_weight - target_weight,
            2,
        )

        if difference > tolerance:

            action = "REDUCE"

            needs_rebalance = True

        elif difference < -tolerance:

            action = "INCREASE"

            needs_rebalance = True

        else:

            action = "KEEP"

        allocations.append({

            "symbol": item["symbol"],

            "current_weight": current_weight,

            "target_weight": target_weight,

            "difference": difference,

            "action": action,

        })

    allocations.sort(

        key=lambda x: abs(x["difference"]),

        reverse=True,

    )

    return {

        "target_weight": target_weight,

        "needs_rebalance": needs_rebalance,

        "allocations": allocations,

    }