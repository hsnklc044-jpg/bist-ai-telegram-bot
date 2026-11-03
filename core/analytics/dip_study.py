"""
QuantBIST
The "dip dönüşü" trigger measured on hourly candles (DECISIONS K-63, written before the
measurement). Event: the trigger at an hour's close; a new trigger within GAP candles of the
stock's previous event is not a new event. Result: enter at the next hour's open, exit at the
close HOLD candles later, COST deducted. Baseline: the same entry rule from every hour of the
same stocks. The 95% interval of (events − baseline) resamples whole days.

    python -m core.analytics.dip_study       # BIST 30, last year of hourly candles
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

HOLD = 16
SIDE_HOLD = 8
GAP = 16
COST = 0.0015
MIN_EVENTS = 100
BOOTSTRAP = 2000
DISCLAIMER = "Kural çıktısıdır, öneri değildir. Geçmiş sonuç geleceği göstermez."


def forward(df: pd.DataFrame, hold: int) -> pd.Series:
    """Net return of 'enter at the next open, exit at the close `hold` candles later' for each candle."""

    entry = df["open"].shift(-1)
    exit_ = df["close"].shift(-hold)
    return (exit_ / entry - 1 - COST).where(entry > 0)


def events(mask: pd.Series, gap: int = GAP) -> pd.Series:
    """The first trigger of each cluster: a trigger within `gap` candles of the last event is dropped."""

    out = np.zeros(len(mask), dtype=bool)
    last = -gap - 1
    for i in np.flatnonzero(mask.to_numpy(dtype=bool)):  # the triggers only (a handful per stock)
        if i - last > gap:
            out[i], last = True, i
    return pd.Series(out, index=mask.index)


@dataclass
class Result:
    events: int
    stocks: int
    mean_event: float | None
    mean_base: float | None
    diff: float | None
    interval: tuple[float, float]
    hit_rate: float | None
    side_diff: float | None
    passed: bool
    reason: str


def collect(frames: dict[str, pd.DataFrame], before: pd.Timestamp | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(event rows, baseline rows) with the day, the 16- and 8-candle results."""

    from core.market.extended import add_indicators, trigger_mask

    picked, base = [], []
    for symbol, df in frames.items():
        if df is None or len(df) < 250:
            continue
        if before is not None:
            df = df[df.index < before]
        ind = add_indicators(df)
        r, side = forward(df, HOLD), forward(df, SIDE_HOLD)
        table = pd.DataFrame({"r": r, "side": side, "day": df.index.normalize(), "symbol": symbol}, index=df.index)
        table = table[ind["ema200"].notna()]  # every indicator warmed up
        ev = events(trigger_mask(ind).reindex(table.index, fill_value=False))
        picked.append(table[ev].dropna(subset=["r"]))
        base.append(table.dropna(subset=["r"]))
    empty = pd.DataFrame(columns=["r", "side", "day", "symbol"])
    return (pd.concat(picked) if picked else empty), (pd.concat(base) if base else empty)


def day_bootstrap(picked: pd.DataFrame, base_mean: float, repeats: int = BOOTSTRAP, seed: int = 0):
    by_day = picked.groupby("day")["r"].agg(["sum", "count"])
    if by_day.empty:
        return (math.nan, math.nan)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(by_day), size=(repeats, len(by_day)))
    means = by_day["sum"].to_numpy()[pick].sum(axis=1) / by_day["count"].to_numpy()[pick].sum(axis=1)
    lo, hi = np.percentile(means - base_mean, [2.5, 97.5])
    return (float(lo), float(hi))


def study(frames: dict[str, pd.DataFrame], before: pd.Timestamp | None = None) -> Result:
    if before is None:
        from core.backtest.run import HOLDOUT_START

        before = HOLDOUT_START.tz_localize("Europe/Istanbul")
    picked, base = collect(frames, before)
    if picked.empty or base.empty:
        return Result(0, 0, None, None, None, (math.nan, math.nan), None, None, False, "olay yok")
    mean_event, mean_base = float(picked["r"].mean()), float(base["r"].mean())
    interval = day_bootstrap(picked, mean_base)
    side = picked["side"].dropna()
    result = Result(len(picked), picked["symbol"].nunique(), mean_event, mean_base, mean_event - mean_base, interval,
                    float((picked["r"] > 0).mean()),
                    float(side.mean() - base["side"].mean()) if len(side) else None, False, "")
    if result.events < MIN_EVENTS:
        result.reason = f"olay sayısı az ({result.events} < {MIN_EVENTS})"
    elif not interval[0] > 0:
        result.reason = "olaylar, aynı hisselerin rastgele saatlerinden ayırt edilemiyor"
    elif not mean_event > 0:
        result.reason = "olayların maliyet sonrası ortalaması pozitif değil"
    else:
        result.passed, result.reason = True, "koşullar sağlandı"
    return result


def text(result: Result) -> str:
    def pct(x):
        return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"%{x * 100:+.2f}".replace(".", ",")

    return "\n".join([
        f"🔬 Dip dönüşü (saatlik, K-63): {'GEÇTİ' if result.passed else 'GEÇMEDİ'} – {result.reason}",
        f"{result.events} olay, {result.stocks} hisse. {HOLD} mum sonra ortalama {pct(result.mean_event)}, "
        f"rastgele saatler {pct(result.mean_base)}; fark {pct(result.diff)} "
        f"(%95 aralık {pct(result.interval[0])} – {pct(result.interval[1])}).",
        f"Kazançlı olay oranı {'—' if result.hit_rate is None else f'%{result.hit_rate * 100:.0f}'}; "
        f"{SIDE_HOLD} mumda fark {pct(result.side_diff)} (yan sonuç).",
        DISCLAIMER,
    ])


def main() -> int:
    import json

    from core.config.paths import LOG_DIR
    from core.infrastructure.console import utf8_output
    from core.market.hourly import load_hourly

    utf8_output()
    data = load_hourly()
    result = study(data.frames)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "dip_study.json").write_text(json.dumps(asdict(result), ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print(data.summary())
    print(text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["GAP", "HOLD", "Result", "collect", "day_bootstrap", "events", "forward", "study", "text"]
