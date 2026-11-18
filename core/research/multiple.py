"""Multiple-testing corrections (QB-ARS-1 S-2; Faz B, 18.11.2026). Pure functions; nothing calls them yet.

- Bonferroni: adjusted p = min(1, m * p); controls the family-wise error rate.
- Benjamini-Hochberg (1995): adjusted p_(i) = min_{k >= i} min(1, m * p_(k) / k); controls the false
  discovery rate for independent (or positively dependent) tests.

Which one a study uses is chosen in its pre-registration, before results are seen (ANAYASA Md. 3).
"""

from __future__ import annotations

import math


def _check(ps) -> list[float]:
    values = [float(p) for p in ps]
    if not values:
        raise ValueError("p değeri listesi boş")
    for p in values:
        if math.isnan(p) or not 0.0 <= p <= 1.0:
            raise ValueError(f"p değeri 0 ile 1 arasında olmalı: {p}")
    return values


def _check_alpha(alpha: float) -> float:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"anlamlılık düzeyi 0 ile 1 arasında olmalı: {alpha}")
    return alpha


def bonferroni_adjust(ps) -> list[float]:
    values = _check(ps)
    m = len(values)
    return [min(1.0, m * p) for p in values]


def bonferroni_reject(ps, alpha: float = 0.05) -> list[bool]:
    alpha = _check_alpha(alpha)
    return [p < alpha for p in bonferroni_adjust(ps)]


def bh_adjust(ps) -> list[float]:
    """Benjamini-Hochberg adjusted p-values, in the input order."""

    values = _check(ps)
    m = len(values)
    order = sorted(range(m), key=values.__getitem__)
    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        running = min(running, m * values[i] / rank)
        adjusted[i] = min(1.0, running)
    return adjusted


def bh_reject(ps, q: float = 0.05) -> list[bool]:
    """Reject where the BH-adjusted p-value is at most q (the step-up procedure)."""

    q = _check_alpha(q)
    return [p <= q for p in bh_adjust(ps)]
