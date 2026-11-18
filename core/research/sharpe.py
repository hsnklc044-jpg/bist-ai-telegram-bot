"""Probabilistic and Deflated Sharpe ratio as pure functions (QB-ARS-1 S-3; Faz B, 19.11.2026). Nothing calls them yet.

- psr(): Probabilistic Sharpe Ratio (Bailey and López de Prado, 2012). The probability that the true Sharpe
  ratio exceeds a benchmark sr_star, given the observed per-period Sharpe ratio, the number of observations
  and the return distribution's skewness and (raw, normal = 3) kurtosis:
      PSR = Phi( (SR - SR*) * sqrt(T - 1) / sqrt(1 - skew * SR + (kurt - 1) / 4 * SR^2) )
- expected_max_sharpe(): expected maximum of N independent Sharpe estimates with variance V and mean 0
  (Bailey and López de Prado, 2014; Euler-Mascheroni constant):
      SR0 = sqrt(V) * ((1 - g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N e)))
- dsr(): Deflated Sharpe Ratio = PSR with SR* = SR0.

Same formulas as core/backtest/overfit.deflated_sharpe (K-81), which works on return series; these take
the summary numbers directly so a study can report them. All Sharpe ratios are per period (not annualized):
SR, SR*, V and T must use the same frequency. Information only; a decision rule comes from a pre-registration.
"""

from __future__ import annotations

import math
import numbers
from statistics import NormalDist

EULER_GAMMA = 0.5772156649015329
_N = NormalDist()


def _real(name: str, x) -> float:
    if isinstance(x, bool) or not isinstance(x, numbers.Real) or not math.isfinite(float(x)):
        raise ValueError(f"{name} sonlu bir sayı olmalı: {x!r}")
    return float(x)


def psr(sr: float, sr_star: float, t: int, skew: float = 0.0, kurt: float = 3.0) -> float:
    """P(true SR > sr_star). t is the number of return observations (>= 2); kurt is raw kurtosis (normal 3)."""

    sr, sr_star, skew, kurt = (_real(n, v) for n, v in
                               (("sr", sr), ("sr_star", sr_star), ("skew", skew), ("kurt", kurt)))
    if isinstance(t, bool) or not isinstance(t, numbers.Integral) or t < 2:
        raise ValueError(f"gözlem sayısı t en az 2 olan bir tam sayı olmalı: {t!r}")
    if kurt < 1:
        raise ValueError(f"basıklık (ham, normal = 3) 1'den küçük olamaz: {kurt}")
    inner = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if not inner > 0:
        raise ValueError("standart hata tanımsız (1 - skew*SR + (kurt-1)/4*SR^2 <= 0)")
    return _N.cdf((sr - sr_star) * math.sqrt(t - 1) / math.sqrt(inner))


def expected_max_sharpe(variance: float, n: int) -> float:
    """Expected maximum of n independent per-period Sharpe estimates with mean 0 and the given variance."""

    variance = _real("variance", variance)
    if variance < 0:
        raise ValueError(f"varyans negatif olamaz: {variance}")
    if isinstance(n, bool) or not isinstance(n, numbers.Integral) or n < 2:
        raise ValueError(f"deneme sayısı n en az 2 olan bir tam sayı olmalı: {n!r}")
    return math.sqrt(variance) * ((1 - EULER_GAMMA) * _N.inv_cdf(1 - 1 / n)
                                  + EULER_GAMMA * _N.inv_cdf(1 - 1 / (n * math.e)))


def dsr(sr: float, t: int, variance: float, n: int, skew: float = 0.0, kurt: float = 3.0) -> float:
    """Deflated Sharpe Ratio of the best of n trials: PSR against the expected maximum under luck alone."""

    return psr(sr, expected_max_sharpe(variance, n), t, skew, kurt)
