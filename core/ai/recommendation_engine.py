"""
QuantBIST RC4
Recommendation Engine
"""

from __future__ import annotations


def generate_recommendation(
    ai: dict,
) -> str:
    """
    Dashboard ve Telegram için yatırım önerisi üretir.
    """

    risk = ai["risk"]
    best = ai["best"]
    health = ai["portfolio_health"]

    if risk == "HIGH":

        return (
            "⚠️ Portföy riski yüksek. "
            "Yeni alım yerine risk azaltılması önerilir."
        )

    if health >= 85:

        return (
            f"✅ Portföy sağlıklı. "
            f"En güçlü fırsat: {best}."
        )

    if health >= 70:

        return (
            f"📊 Portföy dengeli. "
            f"{best} takip edilmeli."
        )

    return (
        "📉 Portföy performansı zayıf. "
        "Pozisyonlar gözden geçirilmeli."
    )