"""Combinatorial purged cross-validation and PBO over it (QB-ARS-1 S-3, S-4; Faz B, 18.11.2026).

Pure functions on observation positions 0..n-1 in time order (never shuffled):
- splits(): N contiguous groups, every choice of k test groups; training drops observations whose label
  window [t+1, t+horizon] reaches into a test group (purge) and the `embargo` observations right after
  each test group.
- paths(): the phi = k/N * C(N, k) backtest paths, each covering every observation once.
- leaks(): training observations whose label reaches into test (empty for a correct split).
- pbo(): probability of backtest overfitting over these splits; with horizon = embargo = 0 it equals the
  CSCV PBO of core.backtest.overfit (K-81), which stays as it is.

Nothing here changes a decision, a threshold or a report.
"""

from __future__ import annotations

import math
from itertools import combinations

import numpy as np
import pandas as pd


def _groups(n: int, n_groups: int) -> list[np.ndarray]:
    return np.array_split(np.arange(n), n_groups)


def _check(n: int, n_groups: int, k_test: int, horizon: int, embargo: int) -> None:
    if n_groups < 2 or not 0 < k_test < n_groups:
        raise ValueError(f"grup sayısı ≥ 2 ve 0 < test grubu < grup olmalı: N={n_groups}, k={k_test}")
    if n < n_groups:
        raise ValueError(f"gözlem sayısı ({n}) grup sayısından ({n_groups}) az")
    if horizon < 0 or embargo < 0:
        raise ValueError("etiket süresi ve ambargo negatif olamaz")


def n_paths(n_groups: int, k_test: int) -> int:
    return k_test * math.comb(n_groups, k_test) // n_groups


def leaks(train, test, horizon: int) -> list[int]:
    """Training positions t with any of t+1..t+horizon in the test set, or t itself in it."""

    test_set = set(np.asarray(test).tolist())
    return [int(t) for t in np.asarray(train)
            if t in test_set or any(t + j in test_set for j in range(1, horizon + 1))]


def splits(n: int, n_groups: int, k_test: int, horizon: int, embargo: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """(train, test) position arrays for every choice of k test groups, purged and embargoed."""

    _check(n, n_groups, k_test, horizon, embargo)
    groups = _groups(n, n_groups)
    out = []
    for chosen in combinations(range(n_groups), k_test):
        test = np.concatenate([groups[g] for g in chosen])
        drop = np.zeros(n, dtype=bool)
        drop[test] = True
        for g in chosen:
            start, end = int(groups[g][0]), int(groups[g][-1])
            drop[max(0, start - horizon):start] = True  # purge: labels of these reach into the test group
            drop[end + 1:min(n, end + 1 + embargo)] = True  # embargo after the test group
        train = np.flatnonzero(~drop)
        out.append((train, test))
    return out


def paths(n: int, n_groups: int, k_test: int) -> list[list[tuple[int, np.ndarray]]]:
    """Backtest paths: path j takes, for each group, the test of the j-th split that tests that group."""

    _check(n, n_groups, k_test, 0, 0)
    groups = _groups(n, n_groups)
    seen = {g: [] for g in range(n_groups)}
    for i, chosen in enumerate(combinations(range(n_groups), k_test)):
        for g in chosen:
            seen[g].append(i)
    return [[(seen[g][j], groups[g]) for g in range(n_groups)] for j in range(n_paths(n_groups, k_test))]


def _sharpe(data: np.ndarray, rows: np.ndarray) -> np.ndarray:
    part = data[rows]
    mean = part.mean(axis=0)
    sd = part.std(axis=0, ddof=1) if len(rows) > 1 else np.zeros(part.shape[1])
    return np.divide(mean, sd, out=np.zeros_like(mean), where=sd > 0)


def pbo(returns: pd.DataFrame, n_groups: int, k_test: int, horizon: int, embargo: int) -> float | None:
    """Share of splits whose in-sample best strategy ranks at or below the out-of-sample median."""

    if returns.shape[1] < 2:
        return None
    data = returns.to_numpy(dtype=float)
    n = data.shape[1]
    below = 0
    every = splits(len(data), n_groups, k_test, horizon, embargo)
    for train, test in every:
        best = int(np.argmax(_sharpe(data, train)))
        oos = _sharpe(data, test)
        rank = 1 + np.sum(oos < oos[best]) + 0.5 * (np.sum(oos == oos[best]) - 1)  # 1 = worst, ties averaged
        omega = rank / (n + 1)
        below += math.log(omega / (1 - omega)) <= 0
    return below / len(every)
