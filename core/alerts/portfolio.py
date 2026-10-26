"""
QuantBIST
Portfolio-level risk: what the per-position rules cannot see.

- 1-day loss estimate: today's holdings replayed over the last VAR_DAYS
  sessions of their (split-adjusted) returns; the 5th percentile of
  that daily result, as a share of the account (historical VaR, 95%).
  It assumes the past year's moves; it is not a limit on losses.
- Holdings that move together: pairs whose 60-session return
  correlation is above CORR_HIGH and that together are a large share of
  the account behave like one bigger position.
- Effective number of positions: 1 / sum(weight^2); 4 equal holdings
  give 4, one dominant holding gives close to 1.
- A holding without a price makes the account value and every share
  wrong; it is reported, never counted as zero risk.

Sector concentration needs sector data, which the system does not have.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from core.alerts.rules import Alert, _n
from core.config import alerts as cfg


@dataclass
class PortfolioRisk:
    total: float
    weights: dict[str, float] = field(default_factory=dict)
    unpriced: list[str] = field(default_factory=list)
    var: float | None = None  # 1-day loss at VAR_LEVEL, share of the account
    days: int = 0  # sessions used for the estimate
    pairs: list[tuple[str, str, float]] = field(default_factory=list)  # correlated, heavy pairs
    top_pair: tuple[str, str, float] | None = None  # highest correlation among holdings

    @property
    def effective_n(self) -> float | None:
        w = np.array(list(self.weights.values()))
        return float(1 / (w**2).sum()) if len(w) and (w**2).sum() > 0 else None

    def line(self) -> str:
        if self.unpriced:
            return f"Risk: hesaplanamadı (fiyatı olmayan: {', '.join(_code(s) for s in self.unpriced)})"
        if self.var is None:
            return f"Risk: 1 günlük kayıp tahmini hesaplanamadı (ortak veri {self.days} seans < {cfg.VAR_MIN_DAYS})"
        parts = [
            f"Risk: 1 günlük kayıp, %{cfg.VAR_LEVEL * 100:.0f} tarihsel: %{_n(self.var * 100, 1)} "
            f"(~{_n(self.var * self.total, 0)} TL; {self.days} seans)"
        ]
        if self.effective_n is not None:
            parts.append(f"etkin pozisyon sayısı {_n(self.effective_n, 1)}")
        if self.top_pair:
            a, b, c = self.top_pair
            parts.append(f"en yüksek korelasyon {_code(a)}–{_code(b)} {_n(c, 2)}")
        return "; ".join(parts)


def _code(symbol: str) -> str:
    return symbol.removesuffix(".IS")


def portfolio_risk(values: dict[str, float], frames: dict[str, pd.DataFrame], total: float) -> PortfolioRisk:
    """
    values: market value of each holding (NaN when it has no price).
    frames: split-adjusted final candles per holding.
    total: account value (cash included for the paper account).
    """

    risk = PortfolioRisk(total=total)
    risk.unpriced = [s for s, v in values.items() if v is None or pd.isna(v)]
    if not values or risk.unpriced or total <= 0:
        return risk

    risk.weights = {s: v / total for s, v in values.items()}
    returns = pd.concat(
        {s: frames[s]["close"].pct_change() for s in values if s in frames and not frames[s].empty},
        axis=1,
        sort=True,
    )
    if returns.shape[1] < len(values):
        risk.unpriced = [s for s in values if s not in returns.columns]
        return risk

    common = returns.dropna().tail(cfg.VAR_DAYS)
    risk.days = len(common)
    if risk.days >= cfg.VAR_MIN_DAYS:
        daily = common @ pd.Series(risk.weights)[common.columns]
        risk.var = float(max(0.0, -np.quantile(daily, 1 - cfg.VAR_LEVEL)))

    recent = common.tail(cfg.CORR_DAYS)
    if len(values) > 1 and len(recent) >= cfg.VAR_MIN_DAYS // 2:
        corr = recent.corr()
        pairs = [
            (a, b, float(corr.at[a, b]))
            for i, a in enumerate(corr.columns)
            for b in corr.columns[i + 1:]
            if not pd.isna(corr.at[a, b])
        ]
        if pairs:
            risk.top_pair = max(pairs, key=lambda p: p[2])
        risk.pairs = [
            p for p in pairs
            if p[2] >= cfg.CORR_HIGH and risk.weights[p[0]] + risk.weights[p[1]] >= cfg.CORR_PAIR_WEIGHT
        ]

    return risk


def evaluate_portfolio(account: str, risk: PortfolioRisk, day: date) -> list[Alert]:
    out = []
    if risk.unpriced:
        out.append(Alert(
            account, "HESAP", "fiyatsiz_pozisyon", 2, len(risk.unpriced), 0, day,
            f"fiyatı olmayan pozisyon: {', '.join(_code(s) for s in risk.unpriced)}; hesap değeri, "
            "yoğunlaşma ve portföy riski eksik hesaplandı",
        ))
    if risk.var is not None and risk.var > cfg.VAR_LIMIT:
        out.append(Alert(
            account, "HESAP", "portfoy_risk", 2, risk.var, cfg.VAR_LIMIT, day,
            f"geçmiş {risk.days} seansa göre kötü bir günde (%{cfg.VAR_LEVEL * 100:.0f}) hesabın "
            f"%{_n(risk.var * 100, 1)}'i (~{_n(risk.var * risk.total, 0)} TL) kaybedilebilir",
        ))
    for a, b, c in risk.pairs:
        share = risk.weights[a] + risk.weights[b]
        out.append(Alert(
            account, f"{_code(a)}+{_code(b)}", "korelasyon", 2, c, cfg.CORR_HIGH, day,
            f"son {cfg.CORR_DAYS} seansta birlikte hareket ediyor (korelasyon {_n(c, 2)}); "
            f"ikisi hesabın %{share * 100:.0f}'i, tek büyük pozisyon gibi davranır",
        ))
    return out


__all__ = ["PortfolioRisk", "portfolio_risk", "evaluate_portfolio"]
