"""
QuantBIST RC4
Portfolio Rebalancer
"""

from __future__ import annotations

from core.portfolio.allocator import calculate_target_allocations


def generate_rebalance_plan() -> dict:
    """
    Portföy için yeniden dengeleme planı oluşturur.

    Returns
    -------
    dict
        {
            "needs_rebalance": bool,
            "actions": list,
            "summary": str,
        }
    """

    allocation = calculate_target_allocations()

    if not allocation["allocations"]:

        return {

            "needs_rebalance": False,

            "actions": [],

            "summary": "Portfolio is empty.",

        }

    actions = []

    for item in allocation["allocations"]:

        if item["action"] == "KEEP":

            continue

        actions.append({

            "symbol": item["symbol"],

            "action": item["action"],

            "current_weight": item["current_weight"],

            "target_weight": item["target_weight"],

            "difference": abs(item["difference"]),

        })

    actions.sort(

        key=lambda x: x["difference"],

        reverse=True,

    )

    if not actions:

        summary = "Portfolio is already balanced."

    else:

        increase = sum(
            1 for x in actions
            if x["action"] == "INCREASE"
        )

        reduce = sum(
            1 for x in actions
            if x["action"] == "REDUCE"
        )

        summary = (

            f"{reduce} position(s) should be reduced, "

            f"{increase} position(s) should be increased."

        )

    return {

        "needs_rebalance": allocation["needs_rebalance"],

        "actions": actions,

        "summary": summary,

    }