"""
QuantBIST RC6
API Decision Service

Decision API facade.
"""

from __future__ import annotations


from core.decision.service import (
    get_decision as _get_decision,
)


from core.decision.models import (
    Decision,
)





# =====================================================
# PUBLIC API
# =====================================================


def get_decision(
    *args,
    **kwargs,
) -> Decision:
    """
    Return QuantBIST AI decision.

    Source:

        core.decision.service

    This layer only exposes
    decision intelligence.

    """


    return _get_decision(

        *args,

        **kwargs,

    )





# =====================================================
# EXPORTS
# =====================================================


__all__ = [

    "get_decision",

]