"""
QuantBIST
Live (forward) performance: what happened after the bot spoke.

    python -m core.reports.forward
    /performans   (Telegram)

Backtests can be overfitted; this cannot: it only scores what was
recorded before the outcome was known.

1. Technical views. Every evening the daily report records the score of
   every stock (source "daily", an unbiased sample; /top and /analyze
   rows only reflect what was asked for and are counted separately).
   Each record is scored as if bought at the next session's open and
   held for 5, 20 or 60 sessions, minus XU100 over the same sessions.
   Records from the same day move together, so the confidence interval
   is computed over days (day averages), not over single records. Days
   closer than the holding period share sessions (two 20-session results
   a day apart share 19), so the interval uses only days at least that
   far apart; the mean still uses every day.

2. Paper account. Its recorded value against XU100 over the same days.

No result is shown as a verdict before MIN_DAYS days have matured.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from core.config.paths import EQUITY_LOG_FILE, SIGNAL_LOG_FILE
from core.config.thresholds import SIGNAL_VIEW_LABELS
from core.infrastructure.logger import get_logger
from core.market.universe import BENCHMARK
from core.reports.daily import DISCLAIMER, adjusted_bars, pct, read_equity
from core.signals_log import audit_log, log_signal
from core.strategy.score import score_frame

logger = get_logger(__name__)

HORIZONS = (5, 20, 60)
MIN_DAYS = 20
MIN_PERIODS = 10  # non-overlapping holding periods before a verdict
# two-sided 95% Student t values by degrees of freedom; above 30, 1.96
T95 = (12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179, 2.160, 2.145,
       2.131, 2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048,
       2.045, 2.042)
VIEW_ORDER = tuple(SIGNAL_VIEW_LABELS.values())
SYSTEMATIC = "daily"


# =====================================================
# RECORDING
# =====================================================


def log_daily_scores(
    universe: list[str],
    path: Path | str | None = None,
    bars=adjusted_bars,
) -> int:
    """Record today's score of every stock. Returns the number of rows written."""

    path = Path(path or SIGNAL_LOG_FILE)
    already = {
        (r["symbol"], r["data_date"]) for r in _read_log(path) if r["source"] == SYSTEMATIC
    }
    written = 0

    for symbol in universe:
        df = bars(symbol)
        if df.empty:
            continue

        last = score_frame(df).iloc[-1]
        day = df.index[-1].date()
        if pd.isna(last["score"]) or (symbol, day.isoformat()) in already:
            continue

        log_signal(
            SYSTEMATIC,
            symbol,
            float(last["score"]),
            SIGNAL_VIEW_LABELS.get(last["signal"], str(last["signal"])),
            day,
            float(df["close"].iloc[-1]),
            path=path,
        )
        written += 1

    return written


def _read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# =====================================================
# SCORING
# =====================================================


def forward_excess(
    stock: pd.DataFrame, bench: pd.DataFrame, day: date, horizon: int
) -> float | None:
    """
    Return of buying at the first open after `day` and selling at the close
    `horizon` sessions later, minus XU100 over the same sessions. None until
    those sessions exist.
    """

    after = stock.index[stock.index > pd.Timestamp(day)]
    if len(after) < horizon:
        return None

    entry, exit_ = after[0], after[horizon - 1]
    own = stock.at[exit_, "close"] / stock.at[entry, "open"] - 1

    window = bench.loc[entry:exit_]
    if window.empty or window.index[-1] != exit_:
        return None
    market = window["close"].iloc[-1] / window["open"].iloc[0] - 1

    return float(own - market)


@dataclass
class ViewStats:
    view: str
    records: int
    days: int
    mean: float
    low: float
    high: float
    hit_rate: float
    periods: int | None = None  # days used for the interval: no two share a session

    @property
    def mature(self) -> bool:
        periods = self.days if self.periods is None else self.periods
        return self.days >= MIN_DAYS and periods >= MIN_PERIODS


def summarize(rows: pd.DataFrame) -> ViewStats | None:
    """
    rows: columns day, excess, and horizon (sessions held; 1 when missing), one row per record.
    The mean is over all days; the 95% interval only over days `horizon` records apart, counted
    back from the latest, so that no two of them share a session (Student t for few periods).
    """

    if rows.empty:
        return None

    horizon = int(rows["horizon"].iloc[0]) if "horizon" in rows else 1
    daily = rows.groupby("day")["excess"].mean().sort_index()
    n = len(daily)
    mean = float(daily.mean())
    apart = daily.iloc[::-1].iloc[::horizon]
    k = len(apart)
    if k > 1:
        t = T95[k - 2] if k - 1 <= len(T95) else 1.96
        half = t * float(apart.std(ddof=1)) / math.sqrt(k)
    else:
        half = float("nan")

    return ViewStats(
        view=str(rows["view"].iloc[0]),
        records=len(rows),
        days=n,
        mean=mean,
        low=mean - half,
        high=mean + half,
        hit_rate=float((rows["excess"] > 0).mean()),
        periods=k,
    )


def score_log(
    path: Path | str | None = None,
    horizons: tuple[int, ...] = HORIZONS,
    bars=adjusted_bars,
) -> pd.DataFrame:
    """One row per (record, horizon) that has matured: source, view, day, horizon, excess, symbol."""

    records = pd.DataFrame(_read_log(Path(path or SIGNAL_LOG_FILE)))
    if records.empty:
        return pd.DataFrame(columns=["source", "view", "day", "horizon", "excess", "symbol"])

    # unreadable rows (cut-off line, garbage) are skipped here and counted by audit_log (Kayıt sağlığı)
    records["day"] = pd.to_datetime(records["data_date"], format="%Y-%m-%d", errors="coerce")
    records = records[records["day"].notna() & records["symbol"].fillna("").astype(str).str.strip().ne("")]
    records = records.drop_duplicates(["source", "symbol", "data_date"], keep="last")

    bench = bars(BENCHMARK)
    cache: dict[str, pd.DataFrame] = {}
    out = []

    for r in records.itertuples():
        if r.symbol not in cache:
            cache[r.symbol] = bars(r.symbol)
        day = r.day.date()
        for h in horizons:
            excess = forward_excess(cache[r.symbol], bench, day, h)
            if excess is not None:
                out.append(
                    {"source": r.source, "view": r.view, "day": day, "horizon": h, "excess": excess,
                     "symbol": r.symbol}
                )

    return pd.DataFrame(out, columns=["source", "view", "day", "horizon", "excess", "symbol"])


@dataclass
class PaperStats:
    start: date
    end: date
    days: int
    account: float
    market: float


def paper_vs_market(path: Path | str | None = None, bars=adjusted_bars) -> PaperStats | None:
    equity = read_equity(Path(path or EQUITY_LOG_FILE), "paper")
    if len(equity) < 2:
        return None

    bench = bars(BENCHMARK)["close"]
    start, end = equity.index[0], equity.index[-1]
    market = bench.loc[start:end]
    if len(market) < 2:
        return None

    return PaperStats(
        start=start.date(),
        end=end.date(),
        days=len(equity),
        account=float(equity.iloc[-1] / equity.iloc[0] - 1),
        market=float(market.iloc[-1] / market.iloc[0] - 1),
    )


BARS = "▁▂▃▄▅▆▇█"
CHART_MIN_POINTS = 5


def sparkline(values) -> str:
    """A text chart for Telegram (K-25): lowest value ▁, highest █; a flat series sits in the middle."""

    values = [float(v) for v in values]
    if not values:
        return ""
    low, high = min(values), max(values)
    if high - low <= 1e-12:
        return BARS[3] * len(values)
    return "".join(BARS[round((v - low) / (high - low) * (len(BARS) - 1))] for v in values)


def weekly_chart(path: Path | str | None = None, bars=adjusted_bars, sessions: int = 20) -> str:
    """The paper account and XU100 over its last `sessions` records, side by side; "" when too short."""

    equity = read_equity(Path(path or EQUITY_LOG_FILE), "paper").tail(sessions)
    if len(equity) < CHART_MIN_POINTS:
        return ""
    market = bars(BENCHMARK)["close"].reindex(equity.index, method="ffill").dropna()
    parts = [f"Sanal hesap {sparkline(equity)} {pct(equity.iloc[-1] / equity.iloc[0] - 1)}"]
    if len(market) >= CHART_MIN_POINTS:
        parts.append(f"XU100 {sparkline(market)} {pct(market.iloc[-1] / market.iloc[0] - 1)}")
    return f"📈 Son {len(equity)} seans: " + " | ".join(parts)


# =====================================================
# REPORT
# =====================================================


def _verdict(stats: ViewStats) -> str:
    if stats.days < MIN_DAYS:
        return f"henüz karar yok ({stats.days}/{MIN_DAYS} gün)"
    if not stats.mature:
        return f"henüz karar yok ({stats.periods}/{MIN_PERIODS} bağımsız dönem)"
    if stats.low > 0:
        return "XU100'ü anlamlı şekilde geçiyor"
    if stats.high < 0:
        return "XU100'ün anlamlı şekilde gerisinde"
    return "XU100'den farkı anlamlı değil"


def _drift(stats: ViewStats, ref: dict | None) -> str:
    """Live versus the backtest reference (MATURITY S4), only once the measurement is mature:
    a reference outside the live 95% interval is a significant drift whose reasons must be reported."""

    if ref is None or not stats.mature:
        return ""
    if stats.low <= ref["mean"] <= stats.high:
        return " → geçmişle uyumlu"
    return " → ⚠️ geçmişten anlamlı sapma (nedeni RESEARCH_LOG'a yazılır)"


def _drift_reasons(rows: pd.DataFrame, ref: dict, bars) -> list[str]:
    """The tested causes of a drift (core.reports.drift); never fatal to the report."""

    from core.market.corrections import load_corporate_actions
    from core.reports.drift import reasons

    try:
        return reasons(rows, ref, bars(BENCHMARK)["close"], load_corporate_actions())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Drift reasons failed")
        return [f"nedenler hesaplanamadı: {exc}"]


def forward_report(
    signal_path: Path | str | None = None,
    equity_path: Path | str | None = None,
    bars=adjusted_bars,
    expectations_path: Path | str | None = None,
) -> str:
    from core.backtest.expectations import load as load_expectations

    scored = score_log(signal_path, bars=bars)
    reference = load_expectations(expectations_path)
    lines = ["📏 Canlı performans (kayıttan sonra olanlar)", ""]

    systematic = scored[scored["source"] == SYSTEMATIC]
    if systematic.empty:
        lines.append(
            "Teknik görünüm: henüz olgunlaşmış kayıt yok. Günlük rapor her akşam tüm hisseleri "
            "kaydeder; ilk sonuç 5 seans sonra, karar için en az "
            f"{MIN_DAYS} işlem günü gerekir."
        )
    else:
        lines.append("Teknik görünüm → sonraki getirinin XU100'den farkı (ortalama, %95 aralık)")
        if reference:
            any_ref = next(iter(reference.values()))
            lines.append(
                f"\"geçmiş\": aynı yöntemle {any_ref['period_start'][:7]} – {any_ref['period_end'][:7]} "
                "(araştırma dönemi; referans, kanıt değil)"
            )
        for h in sorted(systematic["horizon"].unique()):
            lines.append(f"{h} seans:")
            part = systematic[systematic["horizon"] == h]
            for view in VIEW_ORDER:
                stats = summarize(part[part["view"] == view])
                if stats is None:
                    continue
                ref = reference.get((view, int(h)))
                drifted = _drift(stats, ref)
                lines.append(
                    f"  {view:<14} {pct(stats.mean)} [{pct(stats.low)}, {pct(stats.high)}] "
                    f"| {stats.records} kayıt, {stats.days} gün ({stats.periods} bağımsız dönem), "
                    f"isabet %{stats.hit_rate * 100:.0f} "
                    f"→ {_verdict(stats)}"
                    + (f" | geçmiş {pct(ref['mean'])}, isabet %{ref['hit_rate'] * 100:.0f}" if ref else "")
                    + drifted
                )
                if "sapma" in drifted:
                    lines += [f"      neden? {r}" for r in _drift_reasons(part[part["view"] == view], ref, bars)]

    asked = scored[scored["source"] != SYSTEMATIC]
    if not asked.empty:
        matured = int((asked["horizon"] == asked["horizon"].min()).sum())
        lines += [
            "",
            f"/top, /analyze ve /watchscan kayıtları: {matured} olgun kayıt (sadece sorulan hisseler; "
            "yanlı örnek, karar için kullanılmaz).",
        ]

    try:
        audit = audit_log(signal_path)
        lines += ["", f"{'⚠️' if audit.problems else '🧾'} Kayıt sağlığı: {audit.text()}"]
        if audit.missing:
            lines.append("  Kaydı olmayan seanslar örneklemi küçültür; sonuçlar düzeltilmez.")
    except (OSError, ValueError) as exc:
        lines += ["", f"⚠️ Kayıt sağlığı denetlenemedi: {exc}"]

    paper = paper_vs_market(equity_path, bars=bars)
    lines += ["", "💼 Sanal hesap"]
    if paper is None:
        lines.append("Henüz yeterli kayıt yok (günlük rapor her akşam değeri kaydeder).")
    else:
        lines.append(
            f"{paper.start:%d.%m.%Y} → {paper.end:%d.%m.%Y} ({paper.days} gün): "
            f"hesap {pct(paper.account)}, XU100 {pct(paper.market)}, fark {pct(paper.account - paper.market)}"
        )

    lines += ["", DISCLAIMER]

    return "\n".join(lines)


def weekly_line(
    signal_path: Path | str | None = None,
    equity_path: Path | str | None = None,
    bars=adjusted_bars,
) -> str:
    """One or two lines for the Friday report; details stay in /performans."""

    scored = score_log(signal_path, bars=bars)
    systematic = scored[scored["source"] == SYSTEMATIC]

    if systematic.empty:
        lines = ["📏 Canlı ölçüm: kayıtlar birikiyor; ilk sonuç 5 seans sonra (/performans)."]
    else:
        horizon = 20 if (systematic["horizon"] == 20).any() else int(systematic["horizon"].min())
        part = systematic[systematic["horizon"] == horizon]
        days = part["day"].nunique()
        views, computed = [], []
        for view in (VIEW_ORDER[0], VIEW_ORDER[-1]):
            stats = summarize(part[part["view"] == view])
            if stats is not None:
                views.append(f"{view} {pct(stats.mean)}")
                computed.append(stats)
        if computed and all(st.mature for st in computed):
            state = "karar verilebilir"
        elif days < MIN_DAYS:
            state = f"{days}/{MIN_DAYS} gün"
        else:
            state = f"{min(st.periods for st in computed)}/{MIN_PERIODS} bağımsız dönem"
        lines = [
            f"📏 Canlı ölçüm ({horizon} seans, XU100'e göre): {'; '.join(views) or '-'} "
            f"({state}; ayrıntı /performans)"
        ]

    paper = paper_vs_market(equity_path, bars=bars)
    if paper is not None:
        lines.append(f"💼 Sanal hesap {pct(paper.account)}, XU100 {pct(paper.market)} ({paper.days} gün)")
    chart = weekly_chart(equity_path, bars=bars)
    if chart:
        lines.append(chart)

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()  # Windows console / redirected output is cp1254
    argparse.ArgumentParser(description="QuantBIST live performance").parse_args(argv)
    print(forward_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "HORIZONS",
    "MIN_DAYS",
    "forward_excess",
    "forward_report",
    "log_daily_scores",
    "paper_vs_market",
    "score_log",
    "summarize",
    "weekly_line",
]
