"""
QuantBIST
Weekly SLO series (DECISIONS K-93 (3), (7)): every Saturday 21:00 measurement is one row of
logs/haftalik_slo/seri.csv, so that the "4 weeks in a row" counts of S2 (all seven SLOs) and S4
(two-source data accuracy) accumulate by themselves.

The row also keeps the first heartbeat record. When the bot records start after the beginning of
the measured week (as after the 03.11.2026 move of the live folder, whose logs/ did not follow),
the row says "kayıt eksik" and that week never counts in the series.
"""

from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from core.config.paths import LOG_DIR
from core.market.calendar import ISTANBUL
from core.reports.health import CRIT, OK, UNKNOWN, WARN
from core.reports.slo import BRANCH, CI_API, HEARTBEATS_FILE, TARGETS, WINDOW, SloResult

SERIES_FILE = LOG_DIR / "haftalik_slo" / "seri.csv"
NEEDED = 4  # K-88 (3) for S2, K-93 (3) for two sources
ACCURACY = "Veri doğruluğu"
QUALITY = "Kalite (CI, kapsam)"
FIELDS = ["hafta", *TARGETS, "dogruluk_degeri", "dogruluk_metni", "kayit_basi", "not", "not_k92"]
WEEKLY_DIR = LOG_DIR / "haftalik_slo"
SAVED_LINE = re.compile(rf"^\s*({OK}|{WARN}|{CRIT}|{UNKNOWN}) ([^:]+): (—|%([0-9.]+)) \(hedef [^)]*\) · (.*)$")


def _first_beat(path: Path) -> str:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("at"):
                    return row["at"]
    except OSError:
        pass
    return ""


def read(path: Path = SERIES_FILE) -> list[dict]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def network_error(result: SloResult) -> bool:
    """K-92: only a network error (no answer, or 5xx) is asked again; never a spent quota or a 4xx."""

    text = result.text
    if result.state != UNKNOWN or "sorgulanamadı" not in text or "kota" in text:
        return False
    status = re.search(r"HTTP (\d{3})", text)
    return status is None or status.group(1).startswith("5")


def requery_quality(now: datetime, get=None) -> tuple[SloResult | None, str]:
    """K-92: the last finished CI run that started before the measurement; (OK result, note) when it is green."""

    try:
        get = get or __import__("httpx").get
        response = get(CI_API, params={"branch": BRANCH, "per_page": 50,
                                       "created": f"<={now.astimezone(UTC):%Y-%m-%dT%H:%M:%SZ}"}, timeout=10)
        response.raise_for_status()
        runs = response.json().get("workflow_runs", [])
    except Exception as exc:  # noqa: BLE001 - not asked: stays unknown
        return None, f"K-92 yeniden sorgu yapılamadı ({type(exc).__name__})"
    before = [r for r in runs if r.get("status") == "completed"
              and datetime.fromisoformat(r["run_started_at"].replace("Z", "+00:00")) < now]
    if not before:
        return None, "K-92 yeniden sorgu: ölçümden önce çalışma yok"
    last = max(before, key=lambda r: r["run_started_at"])
    note = f"K-92 yeniden sorgu: {last['id']} {last['head_sha']} {last['run_started_at']} {last.get('conclusion')}"
    if last.get("conclusion") != "success":
        return None, note
    return SloResult(QUALITY, OK, None, note), note


def record(now: datetime, results: list[SloResult], beats: Path = HEARTBEATS_FILE,
           path: Path = SERIES_FILE, get=None) -> dict:
    """Add (or replace) this week's row; returns it. A quality row unknown from a network error is asked
    again (K-92) when `get` is given or in live use."""

    k92 = ""
    for i, r in enumerate(results):
        if r.name == QUALITY and network_error(r):
            fixed, k92 = requery_quality(now, get)
            if fixed is not None:
                results = [*results[:i], fixed, *results[i + 1:]]
    by_name = {r.name: r for r in results}
    first = _first_beat(beats)
    start = now - WINDOW
    note = ""
    if not first:
        note = "kayıt eksik: heartbeats.csv yok"
    elif datetime.fromisoformat(first) > start:
        note = f"kayıt eksik: bot kaydı {datetime.fromisoformat(first):%d.%m %H:%M}'de başlıyor, hafta {start:%d.%m %H:%M}"
    acc = by_name.get(ACCURACY)
    row = {"hafta": now.date().isoformat(), **{n: (by_name[n].state if n in by_name else "") for n in TARGETS},
           "dogruluk_degeri": "" if acc is None or acc.value is None else f"{acc.value:.4f}",
           "dogruluk_metni": acc.text if acc else "", "kayit_basi": first, "not": note, "not_k92": k92}
    rows = [r for r in read(path) if r["hafta"] != row["hafta"]] + [row]
    rows.sort(key=lambda r: r["hafta"])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)
    return row


def parse_saved(text: str) -> list[SloResult]:
    """The SLO lines of a saved Saturday summary (logs/haftalik_slo/YYYY-MM-DD.txt)."""

    out = []
    for line in text.splitlines():
        m = SAVED_LINE.match(line)
        if m and m.group(2) in TARGETS:
            value = float(m.group(4)) / 100 if m.group(4) else None
            out.append(SloResult(m.group(2), m.group(1), value, m.group(5)))
    return out


def backfill(folder: Path = WEEKLY_DIR, beats: Path = HEARTBEATS_FILE, path: Path = SERIES_FILE,
             get=None) -> list[str]:
    """Saturdays saved before the series existed (from 14.11.2026) become rows; returns the weeks added."""

    have = {r["hafta"] for r in read(path)}
    added = []
    for saved in sorted(Path(folder).glob("????-??-??.txt")):
        week = saved.stem
        results = parse_saved(saved.read_text(encoding="utf-8"))
        if week in have or len(results) != len(TARGETS):
            continue
        y, m, d = map(int, week.split("-"))
        record(datetime(y, m, d, 21, 0, tzinfo=ISTANBUL), results, beats, path, get)
        added.append(week)
    return added


def _streak(rows: list[dict], names) -> int:
    n = 0
    for r in reversed(rows):
        if r.get("not") or any(r.get(name) != OK for name in names):
            break
        n += 1
    return n


def slo_streak(rows: list[dict]) -> int:
    """Consecutive latest weeks with all seven SLOs on target and complete records (K-88 (3))."""

    return _streak(rows, TARGETS)


def two_source(rows: list[dict]) -> tuple[int, bool, str]:
    weeks = _streak(rows, [ACCURACY])
    holds = weeks >= NEEDED
    text = (f"İki kaynak (Borsa İstanbul resmî): {weeks}/{NEEDED} ardışık hafta ✅"
            + (" → tutuyor (K-93 (3))" if holds else ""))
    return weeks, holds, text


def summary_lines(rows: list[dict]) -> list[str]:
    s = slo_streak(rows)
    lines = [f"SLO serisi: {s}/{NEEDED} ardışık hafta 7/7" + (" → S2 SLO maddesi tamam" if s >= NEEDED else ""),
             two_source(rows)[2]]
    if rows and rows[-1].get("not"):
        lines.append(f"⚠️ {rows[-1]['not']}")
    return lines


__all__ = ["NEEDED", "SERIES_FILE", "backfill", "network_error", "parse_saved", "read", "record", "requery_quality", "slo_streak", "summary_lines", "two_source"]
