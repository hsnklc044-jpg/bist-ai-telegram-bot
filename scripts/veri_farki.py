"""QuantBIST – data difference counts between two frozen snapshots (user's request 05.11.2026, K-80 item 6
and the K-78 daily check). Read-only. It never runs K-63/K-64 and computes no return: only counts.

    .venv\\Scripts\\python scripts\\veri_farki.py saatlik A_KLASOR B_KLASOR
    .venv\\Scripts\\python scripts\\veri_farki.py gunluk  A_KLASOR B_KLASOR

saatlik: per snapshot, the BIST sessions in its range (core.market.calendar), how many of them lack the
         last hourly candle (17:30; a half day's last candle is 11:30), how many have fewer candles than
         a full session, and how many candles have zero volume.
gunluk:  candle counts and value-difference counts (no returns), and at every month end the liquidity
         elimination of K-78 v2 (bottom 20% of that day's BIST 100 members by the 20-session median TL
         turnover) in A and in B: on how many month ends the eliminated lists differ, and by how many names.
Neither download is called right or wrong: there is no independent source.
"""

from __future__ import annotations

import sys
from datetime import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LAST_FULL = time(17, 30)
LAST_HALF = time(11, 30)
FULL_CANDLES = 9  # 09:30 … 17:30
LIQUIDITY_SHARE = 0.20


def hourly_counts(frames: dict[str, pd.DataFrame]) -> dict:
    from core.market.calendar import is_session_day, session_final

    stamps = [df.index for df in frames.values() if len(df)]
    first = min(i.min() for i in stamps).date()
    last = max(i.max() for i in stamps).date()
    sessions = [d.date() for d in pd.bdate_range(first, last) if is_session_day(d.date())]
    out = {"seans": len(sessions), "hisse": len(frames), "son_mum_eksik": 0, "eksik_seans": 0,
           "mumsuz_seans": 0, "sifir_hacim": 0, "mum": 0}
    for df in frames.values():
        local = df.index.tz_convert("Europe/Istanbul") if df.index.tz is not None else df.index
        by_day = pd.Series(local.time, index=local.date).groupby(level=0)
        days = {d: set(t) for d, t in by_day}
        out["mum"] += len(df)
        out["sifir_hacim"] += int((df["volume"] == 0).sum())
        for d in sessions:
            have = days.get(d)
            if not have:
                out["mumsuz_seans"] += 1
                continue
            half = session_final(d).hour < 18
            if (LAST_HALF if half else LAST_FULL) not in have:
                out["son_mum_eksik"] += 1
            if not half and len(have) < FULL_CANDLES:
                out["eksik_seans"] += 1
    return out


def eliminated(frames: dict[str, pd.DataFrame], day: pd.Timestamp) -> set[str]:
    """K-78 v2 liquidity rule on `day`: the bottom 20% of that day's BIST 100 members by 20-session median TL turnover."""

    from core.market.membership import members_on

    members = {f"{c}.IS" for c in members_on(day.date())}
    turnover = {}
    for s in members & set(frames):
        df = frames[s].loc[:day]
        if len(df) >= 20:
            turnover[s] = float((df["close"] * df["volume"]).tail(20).median())
    if not turnover:
        return set()
    ranked = pd.Series(turnover).sort_index().sort_values(kind="stable")
    return set(ranked.index[: int(len(ranked) * LIQUIDITY_SHARE)])


def daily_counts(a: dict[str, pd.DataFrame], b: dict[str, pd.DataFrame]) -> dict:
    from core.analytics.provenance import compare

    diff = compare(a, b)
    common = sorted(set().union(*(df.index for df in a.values())) & set().union(*(df.index for df in b.values())))
    ends = pd.Series(common, index=pd.DatetimeIndex(common)).groupby(pd.DatetimeIndex(common).to_period("M")).max()
    ends = [pd.Timestamp(e) for e in ends if pd.Timestamp(e) >= pd.Timestamp("2022-04-01")]
    lists_differ, names_differ = 0, 0
    for e in ends:
        x, y = eliminated(a, e), eliminated(b, e)
        if x != y:
            lists_differ += 1
            names_differ += len(x ^ y)
    return {"hisse_a": len(a), "hisse_b": len(b), "farkli_hisse": len(diff),
            "yalniz_a_mum": int(diff["yalniz_a"].sum()), "yalniz_b_mum": int(diff["yalniz_b"].sum()),
            "degeri_degisen_mum": int(diff["degisen"].sum()), "ay_sonu": len(ends),
            "eleme_listesi_farkli_ay": lists_differ, "eleme_farkli_isim_toplam": names_differ}


def main(argv: list[str] | None = None) -> int:
    from core.analytics.provenance import thaw
    from core.infrastructure.console import utf8_output

    utf8_output()
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3 or argv[0] not in ("saatlik", "gunluk"):
        print(__doc__)
        return 2
    a, b = thaw(Path(argv[1])), thaw(Path(argv[2]))
    if argv[0] == "saatlik":
        for name, frames in (("A", a), ("B", b)):
            print(name, hourly_counts(frames))
    else:
        print(daily_counts(a, b))
    print("Not: yalnız sayım; K-63/K-64 çalıştırılmadı, getiri hesaplanmadı. Hangi indirmenin doğru olduğu bilinmiyor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
