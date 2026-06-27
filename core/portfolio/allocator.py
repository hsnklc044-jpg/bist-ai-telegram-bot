"""
QuantBIST RC4
Portfolio Allocator
"""

from __future__ import annotations

from core.portfolio.optimizer import optimize_portfolio


def calculate_target_allocations() -> dict:
    """
    Portföy için hedef ağırlıkları hesaplar.
    """

    optimization = optimize_portfolio()

    weights = optimization["weights"]

    if not weights:

        return {

            "target_weight": 0.0,

            "allocations": [],

        }

    target_weight = round(
        100 / len(weights),
        2,
    )

    allocations = []

    for item in weights:

        diff = round(
            item["weight"] - target_weight,
            2,
        )

        if diff > 5:

            action = "REDUCE"

        elif diff < -5:

            action = "INCREASE"

        else:

            action = "KEEP"

        allocations.append({

            "symbol": item["symbol"],

            "current_weight": item["weight"],

            "target_weight": target_weight,

            "difference": diff,

            "action": action,

        })

    return {

        "target_weight": target_weight,

        "allocations": allocations,

    }