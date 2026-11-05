"""
QuantBIST
K-64 hourly forward test (DECISIONS K-80, written before any holdout data was read; 05.11.2026).

The frozen K-64 code (core.ml.signal_filter, K-79) is used as it is: `events`, `fit`, `_bootstrap`,
`APPROVE`, `MIN_APPROVED`, SPEC["saatlik"]. Nothing in it is changed. This module only adds the
forward split that `main()` does not have (it always cuts at HOLDOUT_START):

- training: the frozen snapshot A (Actions 41880444802, data sha256 4fc8a1bc…), events whose label
  was known before HOLDOUT_START; one model;
- test: events of a download made on or after 03.02.2027 whose time is on or after HOLDOUT_START and
  whose label ended before the common end date; the same rule as K-64 (approve at APPROVE, at least
  MIN_APPROVED approvals, the lower end of the day-bootstrap interval above the base rate);
- exactly two downloads at least 7 days apart, both cut to the same end date; each must pass the
  quality gate below first; the verdict table combines them (no choosing, no averaging).

    python -m core.ml.k64_forward --egitim A --test1 D1 --test2 D2 --indirme1 2027-02-03 \\
        --indirme2 2027-02-10 --son 2027-02-02
"""

from __future__ import annotations

import argparse
import math
from dataclasses import asdict, dataclass, field
from datetime import date, time

import pandas as pd

# K-80 quality gate (fixed 05.11.2026 before any count of a forward download was seen)
MAX_LAST_MISSING = 0.05   # share of sessions without their last hourly candle (17:30; half day 11:30)
MAX_SHORT_SESSIONS = 0.05  # share of full sessions with fewer than 9 candles
MAX_EMPTY_SESSIONS = 0     # sessions with no candle at all, per stock
MAX_ZERO_VOLUME = 0.02     # share of candles with zero volume
FULL_CANDLES = 9
MIN_GAP_DAYS = 7
EARLIEST = date(2027, 2, 3)
TRAIN_SHA256 = "4fc8a1bc97045caebb14a914097df181418883e841eb96bfee3e23474c506a0b"  # snapshot A

PASSED, SENSITIVE, FAILED, UNMEASURED = "GEÇTİ", "VERİYE DUYARLI", "GEÇMEDİ", "ÖLÇÜLEMEDİ"


@dataclass
class Quality:
    sessions: int = 0
    last_missing: float = 0.0
    short_sessions: float = 0.0
    empty_sessions: int = 0
    zero_volume: float = 0.0
    passed: bool = False
    reason: str = ""


def quality(frames: dict[str, pd.DataFrame], start: date, end: date) -> Quality:
    """The gate on the forward window [start, end] (BIST calendar; every stock)."""

    from core.market.calendar import is_session_day, session_final

    sessions = [d.date() for d in pd.bdate_range(start, end) if is_session_day(d.date())]
    q = Quality(sessions=len(sessions))
    if not sessions or not frames:
        q.reason = "pencerede seans ya da veri yok"
        return q
    last_missing = short = candles = zeros = full = 0
    for df in frames.values():
        local = df.index.tz_convert("Europe/Istanbul") if df.index.tz is not None else df.index
        part = df[(local.date >= start) & (local.date <= end)]
        lp = local[(local.date >= start) & (local.date <= end)]
        days = {d: set(t) for d, t in pd.Series(lp.time, index=lp.date).groupby(level=0)}
        candles += len(part)
        zeros += int((part["volume"] == 0).sum())
        for d in sessions:
            have = days.get(d)
            if not have:
                q.empty_sessions += 1
                continue
            half = session_final(d).hour < 18
            if (time(11, 30) if half else time(17, 30)) not in have:
                last_missing += 1
            if not half:
                full += 1
                short += len(have) < FULL_CANDLES
    n = len(sessions) * len(frames)
    q.last_missing = last_missing / n
    q.short_sessions = short / full if full else 0.0
    q.zero_volume = zeros / candles if candles else 1.0
    fails = []
    if q.last_missing > MAX_LAST_MISSING:
        fails.append(f"son mum eksik %{q.last_missing * 100:.1f} > %{MAX_LAST_MISSING * 100:.0f}")
    if q.short_sessions > MAX_SHORT_SESSIONS:
        fails.append(f"eksik saatli seans %{q.short_sessions * 100:.1f} > %{MAX_SHORT_SESSIONS * 100:.0f}")
    if q.empty_sessions > MAX_EMPTY_SESSIONS:
        fails.append(f"mumsuz seans {q.empty_sessions}")
    if q.zero_volume > MAX_ZERO_VOLUME:
        fails.append(f"hacmi 0 mum %{q.zero_volume * 100:.1f} > %{MAX_ZERO_VOLUME * 100:.0f}")
    q.passed, q.reason = (not fails), ("; ".join(fails) or "kapıdan geçti")
    return q


@dataclass
class Result:
    events: int = 0
    tested: int = 0
    base_rate: float | None = None
    approved: int = 0
    hits: int = 0
    precision: float | None = None
    interval: tuple[float, float] = (math.nan, math.nan)
    params: dict = field(default_factory=dict)
    passed: bool = False
    reason: str = ""


def train_model(train_frames: dict[str, pd.DataFrame], make=None):
    """One model on the frozen snapshot's events whose label was known before HOLDOUT_START."""

    from core.backtest.run import HOLDOUT_START
    from core.ml import signal_filter as S

    edge = HOLDOUT_START.tz_localize("Europe/Istanbul")
    x, y = S.SPEC["saatlik"]
    rows = S.events(train_frames, x, y, None, before=edge)
    rows = rows[rows["label_end"] < edge]
    model, params = (make or S.fit)(rows)
    return model, params, len(rows)


def forward(model, test_frames: dict[str, pd.DataFrame], end: date, params: dict | None = None) -> Result:
    """K-64's rule on the forward events of one download (the decision part of evaluate, unchanged)."""

    from core.backtest.run import HOLDOUT_START
    from core.ml import signal_filter as S

    start = HOLDOUT_START.tz_localize("Europe/Istanbul")
    cut = pd.Timestamp(end).tz_localize("Europe/Istanbul") + pd.Timedelta(days=1)
    x, y = S.SPEC["saatlik"]
    rows = S.events(test_frames, x, y, None, before=cut)
    rows = rows[(rows["time"] >= start) & (rows["label_end"] < cut)]
    r = Result(events=len(rows), params=dict(params or {}))
    if rows.empty:
        r.reason = "ileri dönemde olay yok"
        return r
    out = rows.copy()
    out["proba"] = model.predict_proba(out[list(S.FEATURES)].to_numpy())[:, 1]
    approve = out["proba"] >= S.APPROVE
    r.tested = len(out)
    r.base_rate = float(out["label"].mean())
    chosen = out[approve]
    r.approved, r.hits = len(chosen), int(chosen["label"].sum())
    if r.approved:
        r.precision = r.hits / r.approved
        r.interval = S._bootstrap(chosen)
    if r.approved < S.MIN_APPROVED:
        r.reason = f"onaylı sinyal az ({r.approved} < {S.MIN_APPROVED})"
    elif not r.interval[0] > r.base_rate:
        r.reason = "onaylı sinyallerin isabeti, tüm sinyallerin oranından ayırt edilemiyor"
    else:
        r.passed, r.reason = True, "koşullar sağlandı"
    return r


def verdict(q1: Quality, r1: Result | None, q2: Quality, r2: Result | None) -> str:
    """K-80 table: no choosing between the two, no averaging."""

    if not (q1.passed and q2.passed) or r1 is None or r2 is None:
        return UNMEASURED
    if r1.passed and r2.passed:
        return PASSED
    if r1.passed != r2.passed:
        return SENSITIVE
    return FAILED


def check_dates(first: date, second: date, end: date) -> list[str]:
    problems = []
    if first < EARLIEST:
        problems.append(f"ilk indirme {EARLIEST:%d.%m.%Y}'ten önce")
    if (second - first).days < MIN_GAP_DAYS:
        problems.append(f"indirmeler arası {(second - first).days} gün < {MIN_GAP_DAYS}")
    if end >= first:
        problems.append("son tarih ilk indirmeden önce olmalı (ikisi de aynı son tarihe kesilir)")
    return problems


def main(argv: list[str] | None = None) -> int:
    from pathlib import Path

    from core.analytics import provenance as P
    from core.backtest.run import HOLDOUT_START
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="K-64 hourly forward test (K-80)")
    parser.add_argument("--egitim", required=True, help="dondurulmuş eğitim görüntüsü (A)")
    parser.add_argument("--test1", required=True)
    parser.add_argument("--test2", required=True)
    parser.add_argument("--indirme1", required=True, help="1. indirmenin tarihi YYYY-AA-GG (workflow günü)")
    parser.add_argument("--indirme2", required=True, help="2. indirmenin tarihi YYYY-AA-GG")
    parser.add_argument("--son", required=True, help="ortak son tarih YYYY-AA-GG")
    args = parser.parse_args(argv)
    end = date.fromisoformat(args.son)
    problems = check_dates(date.fromisoformat(args.indirme1), date.fromisoformat(args.indirme2), end)
    if problems:
        print("K-80 tarih kuralı sağlanmadı: " + "; ".join(problems) + ". Durdu.")
        return 2
    train = P.thaw(Path(args.egitim))
    if P.digest(train) != TRAIN_SHA256:
        print("Eğitim görüntüsü A değil: veri özeti uyuşmuyor. Durdu.")
        return 2
    tests = [P.thaw(Path(args.test1)), P.thaw(Path(args.test2))]
    stamps = [P.manifest(Path(d)).get("source", "") for d in (args.test1, args.test2)]
    model, params, rows = train_model(train)
    print(f"Eğitim: A (4fc8a1bc…), {rows} olay; {P.code_version().line()}")
    qs, rs = [], []
    for i, frames in enumerate(tests, 1):
        q = quality(frames, HOLDOUT_START.date(), end)
        r = forward(model, frames, end, params) if q.passed else None
        qs.append(q)
        rs.append(r)
        print(f"İndirme {i} ({stamps[i - 1]}; veri {P.digest(frames)[:16]}): kalite {q.reason}")
        if r:
            print(f"  {asdict(r)}")
    print("SONUÇ: " + verdict(qs[0], rs[0], qs[1], rs[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FAILED", "PASSED", "SENSITIVE", "UNMEASURED", "Quality", "Result", "check_dates", "forward",
           "quality", "train_model", "verdict"]
