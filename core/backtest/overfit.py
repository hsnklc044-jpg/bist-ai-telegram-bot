"""
QuantBIST
Overfitting measures for the research report (DECISIONS K-81): information only, never a decision.

- deflated_sharpe(): Deflated Sharpe Ratio (Bailey and López de Prado, 2014). The probability that the best
  strategy's Sharpe ratio beats what the best of N tries would show by luck alone, given the spread of the N
  Sharpe ratios, the sample length and the best strategy's skewness and kurtosis.
- pbo(): Probability of Backtest Overfitting by combinatorially symmetric cross-validation (Bailey, Borwein,
  López de Prado and Zhu, 2017). The share of the C(16, 8) train/test splits in which the strategy that was
  best in training ranks in the lower half out of sample.

The research report's decision (block bootstrap with Bonferroni) does not change; these two numbers stand
next to it.
"""

from __future__ import annotations

import math
from itertools import combinations
from statistics import NormalDist

import numpy as np
import pandas as pd

EULER = 0.5772156649
BLOCKS = 16
MIN_PER_BLOCK = 5
SPLITS = math.comb(BLOCKS, BLOCKS // 2)
_N = NormalDist()


def returns_matrix(equities: dict[str, pd.Series]) -> pd.DataFrame:
    """Daily returns of each equity curve, on the days every curve has (inner join)."""

    cols = {name: pd.Series(eq, dtype=float).pct_change() for name, eq in equities.items()}
    return pd.concat(cols, axis=1, join="inner").dropna()


def _sharpe(r: np.ndarray) -> float:
    sd = float(np.std(r, ddof=1)) if len(r) > 1 else 0.0
    return float(np.mean(r)) / sd if sd > 0 and math.isfinite(sd) else 0.0


def deflated_sharpe(returns: dict[str, pd.Series] | pd.DataFrame) -> tuple[str, float, int] | None:
    """(best strategy, DSR in [0, 1], number of strategies), or None when it cannot be computed."""

    m = returns if isinstance(returns, pd.DataFrame) else pd.concat(returns, axis=1, join="inner").dropna()
    n, t = m.shape[1], len(m)
    if n < 2 or t < 3:
        return None
    sharpes = {c: _sharpe(m[c].to_numpy()) for c in m.columns}
    best = max(sharpes, key=lambda c: (sharpes[c], -list(m.columns).index(c)))
    variance = float(np.var(list(sharpes.values()), ddof=1))
    if not variance > 0:
        return None
    r = m[best].to_numpy()
    sr = sharpes[best]
    sd = float(np.std(r))
    if not sd > 0:
        return None
    z = (r - r.mean()) / sd
    skew, kurt = float(np.mean(z ** 3)), float(np.mean(z ** 4))
    sr0 = math.sqrt(variance) * ((1 - EULER) * _N.inv_cdf(1 - 1 / n) + EULER * _N.inv_cdf(1 - 1 / (n * math.e)))
    inner = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if not inner > 0:
        return None
    return str(best), _N.cdf((sr - sr0) * math.sqrt(t - 1) / math.sqrt(inner)), n


def pbo(returns: dict[str, pd.Series] | pd.DataFrame, blocks: int = BLOCKS) -> float | None:
    """Share of the train/test splits whose in-sample best ranks at or below the out-of-sample median."""

    m = returns if isinstance(returns, pd.DataFrame) else pd.concat(returns, axis=1, join="inner").dropna()
    n, t = m.shape[1], len(m)
    if n < 2 or t < blocks * MIN_PER_BLOCK:
        return None
    data = m.to_numpy(dtype=float)
    parts = np.array_split(np.arange(t), blocks)
    # per block: count, sum and sum of squares, so any union of blocks gives its Sharpe ratio without copying
    count = np.array([len(p) for p in parts], dtype=float)
    total = np.array([data[p].sum(axis=0) for p in parts])
    squares = np.array([(data[p] ** 2).sum(axis=0) for p in parts])

    def sharpe(chosen):
        k = count[chosen].sum()
        s, q = total[chosen].sum(axis=0), squares[chosen].sum(axis=0)
        mean = s / k
        var = (q - k * mean ** 2) / (k - 1)
        sd = np.sqrt(np.clip(var, 0, None))
        return np.divide(mean, sd, out=np.zeros_like(mean), where=sd > 0)

    every = set(range(blocks))
    below = 0
    for train in combinations(range(blocks), blocks // 2):
        train = list(train)
        test = sorted(every - set(train))
        best = int(np.argmax(sharpe(train)))
        oos = sharpe(test)
        rank = 1 + np.sum(oos < oos[best]) + 0.5 * (np.sum(oos == oos[best]) - 1)  # 1 = worst, ties averaged
        omega = rank / (n + 1)
        below += math.log(omega / (1 - omega)) <= 0
    return below / math.comb(blocks, blocks // 2)


def report_line(equities: dict[str, pd.Series]) -> str:
    head = "Aşırı uyum (bilgi, K-81; karar değişmez): "
    m = returns_matrix(equities)
    dsr = deflated_sharpe(m) if len(m) else None
    p = pbo(m) if len(m) else None
    if dsr is None and p is None:
        return head + "hesaplanmadı (en az 2 strateji ve 80 ortak seans gerekir)"
    parts = []
    if dsr is not None:
        name, value, n = dsr
        parts.append(f"en yüksek Sharpe {name} · DSR %{value * 100:.0f} ({n} strateji)")
    else:
        parts.append("DSR hesaplanmadı")
    parts.append(f"PBO %{p * 100:.0f} (CSCV, {BLOCKS} blok)" if p is not None else "PBO hesaplanmadı")
    return head + " · ".join(parts)


__all__ = ["BLOCKS", "SPLITS", "deflated_sharpe", "pbo", "report_line", "returns_matrix"]
