"""
QuantBIST RC5
Signal Analytics Engine
"""

from __future__ import annotations


from core.analytics.analyzer import (
    analyze_stock,
)

from core.infrastructure.logger import (
    get_logger,
)


logger = get_logger(__name__)





# =====================================================
# DEFAULT SYMBOLS
# =====================================================


DEFAULT_SYMBOLS = [

    "SASA.IS",

    "SISE.IS",

    "THYAO.IS",

    "TUPRS.IS",

    "ASELS.IS",

    "KCHOL.IS",

    "YKBNK.IS",

    "BIMAS.IS",

    "HEKTS.IS",

    "PETKM.IS",

    "TCELL.IS",

    "GARAN.IS",

    "AKBNK.IS",

    "EREGL.IS",

]





# =====================================================
# SIGNAL FILTER
# =====================================================


VALID_SIGNALS = (

    "WATCH",

    "BUY",

    "STRONG BUY",

    "ACCUMULATE",

)





def _is_valid_signal(
    result: dict,
) -> bool:
    """
    Determine if signal qualifies
    for dashboard.
    """


    signal = result.get(
        "signal",
        "",
    )


    score = result.get(
        "score",
        0,
    )


    confidence = result.get(
        "confidence",
        0,
    )


    if signal not in VALID_SIGNALS:

        return False


    if score < 50:

        return False


    if confidence < 50:

        return False


    return True





# =====================================================
# PUBLIC API
# =====================================================


def get_top_signals(
    symbols: list[str] | None = None,
) -> list[dict]:
    """
    Return highest ranked RC5 signals.


    Pipeline:

    Symbol
       ↓
    Analyzer
       ↓
    Signal Filter
       ↓
    Ranking
       ↓
    Dashboard

    """


    if symbols is None:

        symbols = DEFAULT_SYMBOLS



    opportunities: list[dict] = []



    for symbol in symbols:


        try:


            result = analyze_stock(
                symbol,
            )


            if not result:

                continue



            if not _is_valid_signal(
                result,
            ):

                continue



            result.setdefault(

                "symbol",

                symbol,

            )


            result.setdefault(

                "rank",

                0,

            )


            opportunities.append(

                result,

            )



        except Exception as exc:


            logger.warning(

                "Signal analysis failed | %s | %s",

                symbol,

                exc,

            )


            continue





    # =================================================
    # RANKING
    # =================================================


    opportunities.sort(

        key=lambda item:

        (

            item.get(
                "score",
                0,
            ),

            item.get(
                "confidence",
                0,
            ),

        ),

        reverse=True,

    )





    # =================================================
    # RANK ASSIGNMENT
    # =================================================


    for index, item in enumerate(

        opportunities,

        start=1,

    ):

        item["rank"] = index





    return opportunities[:10]





__all__ = [

    "get_top_signals",

]