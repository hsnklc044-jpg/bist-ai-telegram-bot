"""
QuantBIST
Why a live result drifts from its backtest reference (MATURITY S4). For one view and horizon
whose reference lies outside the live 95% interval, the usual causes are tested, not guessed:

- a few stocks: does the reference fall back inside the interval without the 3 stocks that
  moved the result most?
- one day: ... without the single day furthest from the reference?
- the market: XU100's average return over the same holding length, live versus the
  reference period (a view measured against XU100 still feels a different market);
- the data: corporate actions of the measured stocks inside the live window.

Each line is a finding about the records, not a forecast or advice.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

TOP = 3


def _inside(rows: pd.DataFrame, ref_mean: float) -> bool:
    from core.reports.forward import summarize

    stats = summarize(rows)
    return stats is not None and stats.low <= ref_mean <= stats.high


def _forward_mean(close: pd.Series, days, horizon: int) -> float | None:
    returns = (close.shift(-horizon) / close - 1).dropna()
    picked = returns[returns.index.isin(pd.DatetimeIndex(pd.to_datetime(list(days))))]
    return float(picked.mean()) if len(picked) else None


def reasons(rows: pd.DataFrame, ref: dict, bench_close: pd.Series, actions=None, top: int = TOP) -> list[str]:
    """rows: one view and horizon (columns day, symbol, horizon, excess); ref: the expectation row."""

    from core.reports.daily import pct

    ref_mean = float(ref["mean"])
    horizon = int(rows["horizon"].iloc[0])
    lines = []

    gap = (rows["excess"] - ref_mean).groupby(rows["symbol"]).sum()
    movers = list(gap.abs().sort_values(ascending=False).index[:top])
    names = ", ".join(s.removesuffix(".IS") for s in movers)
    if _inside(rows[~rows["symbol"].isin(movers)], ref_mean):
        lines.append(f"Sapma birkaç hisseden geliyor: {names} çıkarılınca sonuç geçmişle uyumlu.")
    else:
        lines.append(f"Sapma en etkili {top} hisse ({names}) çıkarılınca da sürüyor: geniş tabanlı.")

    daily = rows.groupby("day")["excess"].mean()
    worst = (daily - ref_mean).abs().idxmax()
    if _inside(rows[rows["day"] != worst], ref_mean):
        lines.append(f"Sapma tek bir günden ({worst:%d.%m.%Y}) geliyor: o gün çıkarılınca sonuç geçmişle uyumlu.")
    else:
        lines.append("Sapma tek bir güne bağlı değil.")

    days = sorted(rows["day"].unique())
    live = _forward_mean(bench_close, days, horizon)
    span = bench_close.loc[ref["period_start"]: ref["period_end"]]
    past = _forward_mean(bench_close, span.index, horizon)
    if live is not None and past is not None:
        lines.append(f"Piyasa: XU100'ün {horizon} seanslık ortalama getirisi canlı dönemde {pct(live)}, "
                     f"geçmiş dönemde {pct(past)}.")

    if actions is not None:
        start = pd.Timestamp(days[0]).date()
        after = bench_close.index[bench_close.index > pd.Timestamp(days[-1])]
        end = (after[horizon - 1] if len(after) >= horizon else pd.Timestamp(days[-1]) + timedelta(days=2 * horizon)).date()
        measured = set(rows["symbol"])
        found = sorted((a.symbol, a.ex_date) for a in actions
                       if a.symbol in measured and start <= a.ex_date <= end)
        if found:
            lines.append("Kurumsal işlem (fiyat düzeltmesi sonucu etkileyebilir): "
                         + ", ".join(f"{s.removesuffix('.IS')} {d:%d.%m.%Y}" for s, d in found) + ".")
        else:
            lines.append("Ölçülen hisselerde bu dönemde kayıtlı kurumsal işlem yok.")
    return lines


__all__ = ["reasons"]
