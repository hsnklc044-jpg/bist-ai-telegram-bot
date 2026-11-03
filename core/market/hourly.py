"""
QuantBIST
Hourly candles of the BIST 30 from Yahoo Finance (03.11.2026 request: "son 1 yıllık 1h veri").

One batched yfinance call for all tickers (threads inside yfinance), retried on network errors;
a ticker the batch leaves empty is asked once more on its own.
Each frame is cleaned: lower-case OHLCV, Istanbul time, no empty / NaN / non-positive candles,
no high < low, no duplicate stamps, and the still-open last hour dropped (its close is not final).
A ticker with no data is reported in `missing`, never silently left out. Yahoo keeps 1h data
for about 730 days; its candles are delayed (about 15 minutes) and are research data, not quotes.

    python -m core.market.hourly            # summary of the BIST 30 download
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

ISTANBUL = "Europe/Istanbul"
COLUMNS = ("open", "high", "low", "close", "volume")
RETRIES = 3
PAUSE = 2.0


@dataclass
class HourlyData:
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    missing: dict[str, str] = field(default_factory=dict)  # ticker -> why
    fetched_at: datetime | None = None

    def summary(self) -> str:
        lines = [f"Saatlik veri: {len(self.frames)} hisse"
                 + (f", {sum(len(f) for f in self.frames.values())} mum" if self.frames else "")]
        if self.missing:
            lines.append("Verisi gelmeyen: " + ", ".join(f"{t} ({why})" for t, why in sorted(self.missing.items())))
        return "\n".join(lines)


def clean(frame: pd.DataFrame | None, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """A safe hourly frame (see the module text); an empty frame for anything unusable."""

    empty = pd.DataFrame(columns=list(COLUMNS), dtype=float)
    if frame is None or frame.empty:
        return empty
    out = frame.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    if not {"open", "high", "low", "close"}.issubset(out.columns):
        return empty
    if "volume" not in out.columns:
        out["volume"] = 0.0
    out = out[list(COLUMNS)].apply(pd.to_numeric, errors="coerce")
    index = pd.to_datetime(out.index)
    index = index.tz_localize("UTC") if index.tz is None else index
    out.index = index.tz_convert(ISTANBUL)
    out.index.name = "time"
    prices = out[["open", "high", "low", "close"]]
    ok = prices.notna().all(axis=1) & (prices > 0).all(axis=1) & (out["high"] >= out["low"])
    out = out[ok]
    out["volume"] = out["volume"].fillna(0.0).clip(lower=0.0)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    now = pd.Timestamp.now(tz=ISTANBUL) if now is None else now
    if len(out) and out.index[-1] + pd.Timedelta(hours=1) > now:
        out = out.iloc[:-1]  # the current hour is still trading
    return out


def _split(raw: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    if raw is None or raw.empty:
        return {}
    if isinstance(raw.columns, pd.MultiIndex):
        level = raw.columns.get_level_values(0)
        return {t: raw[t] for t in tickers if t in level}
    return {tickers[0]: raw} if len(tickers) == 1 else {}


def load_hourly(tickers: list[str] | None = None, period: str = "1y", download=None, now=None,
                sleep=time.sleep) -> HourlyData:
    """Hourly candles of `tickers` (default: the BIST 30) for `period`; never raises for data problems."""

    from core.config.bist30 import BIST30_TICKERS

    tickers = list(dict.fromkeys(tickers or BIST30_TICKERS))
    result = HourlyData(fetched_at=datetime.now())
    if download is None:
        import yfinance as yf

        download = yf.download

    def fetch(wanted: list[str]):
        for attempt in range(1, RETRIES + 1):
            try:
                return download(wanted, period=period, interval="1h", auto_adjust=True, group_by="ticker",
                                progress=False, threads=True)
            except Exception as exc:  # noqa: BLE001 - network or Yahoo errors: retried, then reported
                logger.warning("Hourly download failed | attempt %d/%d | %s", attempt, RETRIES, exc)
                if attempt < RETRIES:
                    sleep(PAUSE * attempt)
        return None

    def take(parts: dict, t: str) -> pd.DataFrame:
        try:
            return clean(parts.get(t), now)
        except Exception as exc:  # noqa: BLE001 - one bad frame must not stop the others
            logger.warning("Hourly clean failed | %s | %s", t, exc)
            return pd.DataFrame()

    raw = fetch(tickers)
    if raw is None:
        result.missing = {t: "indirme başarısız" for t in tickers}
        return result
    parts = _split(raw, tickers)
    for t in tickers:
        frame = take(parts, t)
        if frame.empty:  # Yahoo sometimes leaves one ticker empty in a batch (ISCTR, 03.11.2026): ask it alone
            alone = fetch([t])
            single = _split(alone, [t]) if alone is not None else {}
            frame = take(single, t)
            parts = parts | single
        if frame.empty:
            result.missing[t] = "veri yok" if t not in parts else "kullanılabilir mum yok"
        else:
            result.frames[t] = frame
    logger.info("Hourly data | %d ok, %d missing", len(result.frames), len(result.missing))
    return result


def main() -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    data = load_hourly()
    print(data.summary())
    return 0 if data.frames else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["HourlyData", "clean", "load_hourly"]
