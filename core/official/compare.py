"""Using Borsa İstanbul's official end-of-day data (K madde 2–3, the user's 11.11.2026 decision).

- Closed months: Yahoo is checked against the official closes on daily returns with the unchanged crosscheck rules
  (RETURN_TOLERANCE, market-wide days, one-day wrong closes). The exchange's own corporate action code
  (OZSERMAYE HALI) and our corporate_actions.csv explain a difference. The summary goes to the file the
  "Veri doğruluğu" objective reads, with the source "Borsa İstanbul resmî gün sonu"; the names of the stocks that
  differ are in the report (logs/resmi_karsilastirma_YYYY-MM.txt). In research the official close stands.
- The current month stays on Yahoo, level 3 (core.market.trust); a month's days become level 1 when its file is in.
  The monthly official check never lifts the current month (trust.price_trust ignores it).
- Corporate actions: the official coded days against corporate_actions.csv (matched, a different day, only one side).
  The request's idea (the raw price against ONCEKI KAPANIS FIYATI) does not work on the new system's files: that
  field is the raw previous close and REFERANS FIYAT is 0 on those days (checked on 11.11.2026); the code does.
- Membership: the official daily BIST 100 flags against our list after the ticker renames (membership.ALIASES). The
  flag is only on the rows of shares that traded, so a day without a row is not "not a member".
- Reminder: from the first trading day of a month, until last month's price and index files are in the inbox, one
  line in the daily report."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from core.config.paths import DATA_DIR, LOG_DIR
from core.infrastructure.logger import get_logger
from core.official import prices

logger = get_logger(__name__)

SOURCE = "Borsa İstanbul resmî gün sonu"
KIND = "resmi_aylik"  # trust.price_trust does not count this check for the current month
REPORT_DIR = LOG_DIR
INDEX_INBOX = DATA_DIR / "inbox" / "bist_endeks"
REMINDER = "Senden beklenen: geçen ayın borsa fiyat ve endeks dosyalarını indir"
NEAR_DAYS = 3  # a corporate action in our file this many days from the official day is the same action


def _previous_month(day: date) -> tuple[date, date]:
    end = day.replace(day=1) - timedelta(days=1)
    return end.replace(day=1), end


def _official_frame(start: date, end: date, db: Path | None = None) -> pd.DataFrame:
    with prices._connect(db) as conn:
        return pd.read_sql_query(
            "SELECT code, date, close, corp_action FROM official_prices WHERE date BETWEEN ? AND ? ORDER BY date",
            conn, params=(start.isoformat(), end.isoformat()), parse_dates=["date"])


def yahoo_check(now: datetime, bars=None, codes: list[str] | None = None, db: Path | None = None) -> dict | None:
    """Last closed month: Yahoo against the official closes. None when that month's official file is not in."""

    from core.market import crosscheck, second_source
    from core.market.corrections import load_corporate_actions

    start, end = _previous_month(now.date())
    frame = _official_frame(start, end, db)
    if frame.empty:
        return None
    if bars is None:
        from core.reports.daily import raw_bars as bars
    if codes is None:
        from core.market import store

        codes = sorted({s.removesuffix(".IS") for s in store.symbols()} & set(frame["code"]))
    explained: dict[str, set[date]] = {}
    for a in load_corporate_actions():
        explained.setdefault(a.symbol.removesuffix(".IS"), set()).add(a.ex_date)
    for code, day in frame.loc[frame["corp_action"].notna(), ["code", "date"]].itertuples(index=False):
        explained.setdefault(code, set()).add(day.date())
    results = []
    for code in codes:
        theirs = frame.loc[frame["code"] == code].set_index("date")[["close"]]
        if theirs.empty:
            continue
        try:
            ours = bars(f"{code}.IS")
            results.append(crosscheck.compare(f"{code}.IS", ours, theirs, explained.get(code)))
        except Exception as exc:  # noqa: BLE001 - one stock must not stop the check
            logger.exception("Official comparison failed | %s", code)
            results.append(crosscheck.CrossCheck(f"{code}.IS", error=f"karşılaştırma hatası: {type(exc).__name__}"))
    period = f"{start:%Y-%m}"
    text = crosscheck.format_report(results, f"{start:%m.%Y}")
    text = text.replace("İkinci kaynak kontrolü (İş Yatırım,", f"Resmî gün sonu kontrolü ({SOURCE},", 1)
    summary = crosscheck.summary(results, now.date())
    summary.update({"source": SOURCE, "period": period, "kind": KIND})
    second_source.save_summary(summary)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"resmi_karsilastirma_{period}.txt").write_text(text + "\n", encoding="utf-8")
    logger.info("Official check of Yahoo | %s | checked %s differing %s", period, summary["checked"],
                summary["differing"])
    return summary


def yahoo_index_check(now: datetime, bars=None, db: Path | None = None) -> str | None:
    """Last closed month: Yahoo's XU100 against the official index, on daily returns (crosscheck rules)."""

    from core.market import crosscheck
    from core.market.universe import BENCHMARK
    from core.official import indices

    start, end = _previous_month(now.date())
    official = indices.series("XU100", start, end, db=db)
    if official.empty:
        return None
    if bars is None:
        from core.reports.daily import raw_bars as bars
    result = crosscheck.compare(BENCHMARK, bars(BENCHMARK), official.to_frame("close"))
    if result.error:
        line = f"XU100 (resmî, {start:%m.%Y}): kontrol edilemedi ({result.error})"
    else:
        line = (f"XU100 (resmî, {start:%m.%Y}, {result.days} gün): "
                + ("tutarlı" if not result.mismatched else f"{len(result.mismatched)} günde fark"))
    details = [line] + [f"  {d:%d.%m.%Y} Yahoo {a * 100:+.2f}% / resmî {b * 100:+.2f}%"
                        for d, a, b, _ in result.mismatched]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"resmi_xu100_{start:%Y-%m}.txt").write_text("\n".join(details) + "\n", encoding="utf-8")
    logger.info("Official check of Yahoo XU100 | %s", line)
    return line


@dataclass
class ActionsReport:
    matched: list[tuple[str, date]] = field(default_factory=list)
    shifted: list[tuple[str, date, date, str]] = field(default_factory=list)  # code, our day, official day, code
    only_official: list[tuple[str, date, str]] = field(default_factory=list)
    only_ours: list[tuple[str, date]] = field(default_factory=list)


def corporate_actions_report(actions=None, codes: set[str] | None = None, db: Path | None = None) -> ActionsReport:
    """Official coded days against corporate_actions.csv, over the period both cover."""

    if actions is None:
        from core.market.corrections import load_corporate_actions

        actions = load_corporate_actions()
    with prices._connect(db) as conn:
        rows = conn.execute("SELECT code, date, corp_action FROM official_prices WHERE corp_action IS NOT NULL "
                            "ORDER BY date, code").fetchall()
    official = [(c, date.fromisoformat(d), a) for c, d, a in rows if codes is None or c in codes]
    ours = sorted(((a.symbol.removesuffix(".IS"), a.ex_date) for a in actions
                   if codes is None or a.symbol.removesuffix(".IS") in codes), key=lambda x: (x[1], x[0]))
    report = ActionsReport()
    used: set[int] = set()
    for code, day in ours:
        near = [(abs((d - day).days), i) for i, (c, d, _) in enumerate(official)
                if c == code and i not in used and abs((d - day).days) <= NEAR_DAYS]
        if not near:
            report.only_ours.append((code, day))
            continue
        _, i = min(near)
        used.add(i)
        c, d, a = official[i]
        if d == day:
            report.matched.append((code, day))
        else:
            report.shifted.append((code, day, d, a))
    first = min((d for _, d in ours), default=None)
    report.only_official = [(c, d, a) for i, (c, d, a) in enumerate(official)
                            if i not in used and (first is None or d >= first)]
    return report


@dataclass
class MembershipReport:
    days: int = 0
    differences: list[tuple[date, list[str], list[str]]] = field(default_factory=list)  # day, only official, only ours


def membership_report(days: list[date], ours_on, db: Path | None = None) -> MembershipReport:
    """`ours_on(day)` -> our BIST 100 codes. A share with no official row that day did not trade: not compared."""

    from core.market.membership import ALIASES

    report = MembershipReport()
    with prices._connect(db) as conn:
        for day in days:
            rows = conn.execute("SELECT code, bist100 FROM official_prices WHERE date = ?", (day.isoformat(),))
            traded, flagged = set(), set()
            for code, flag in rows:
                code = ALIASES.get(code, code)
                traded.add(code)
                if flag == 1:
                    flagged.add(code)
            if not traded:
                continue
            report.days += 1
            ours = {c.removesuffix(".IS") for c in ours_on(day)}
            only_official = sorted(flagged - ours)
            only_ours = sorted((ours - flagged) & traded)
            if only_official or only_ours:
                report.differences.append((day, only_official, only_ours))
    return report


def reminder(day: date, price_dir: Path | None = None, index_dir: Path | None = None) -> str | None:
    """From the first trading day of a month: one line until last month's price and index files are in."""

    from core.market.calendar import is_session_day

    first = day.replace(day=1)
    while not is_session_day(first):
        first += timedelta(days=1)
    if day < first:
        return None
    month = f"{_previous_month(day)[0]:%Y%m}"
    price_dir = Path(price_dir or prices.INBOX)
    index_dir = Path(index_dir or INDEX_INBOX)
    if not price_dir.is_dir():
        return None  # the official data is not in use on this computer
    has_prices = any(price_dir.glob(f"*PP_GUNSONUFIYATHACIM.M.{month}.*"))
    folder = index_dir / month
    has_index = folder.is_dir() and any(folder.iterdir())
    return None if has_prices and has_index else REMINDER


def main(argv: list[str] | None = None) -> int:
    """python -m core.official.compare   last closed month: Yahoo check, corporate actions, membership (2022–)"""

    import argparse

    from core.infrastructure.console import utf8_output
    from core.market.calendar import now_istanbul

    utf8_output()
    argparse.ArgumentParser(description="Resmî gün sonu karşılaştırmaları").parse_args(argv)
    now = now_istanbul()
    summary = yahoo_check(now)
    print("Yahoo:", json.dumps(summary, ensure_ascii=False) if summary else "geçen ayın resmî dosyası yok")
    acts = corporate_actions_report()
    print(f"Kurumsal işlem: aynı gün {len(acts.matched)}, farklı gün {len(acts.shifted)}, "
          f"yalnız resmî {len(acts.only_official)}, yalnız bizde {len(acts.only_ours)}")
    for code, ours, official, kind in acts.shifted[:30]:
        print(f"  {code}: bizde {ours:%d.%m.%Y}, resmî {official:%d.%m.%Y} (kod {kind})")
    from core.market import membership

    events, stable = membership.load_changes(), membership.load_stable()
    with prices._connect() as conn:
        days = [date.fromisoformat(r[0]) for r in conn.execute(
            "SELECT DISTINCT date FROM official_prices WHERE date >= '2022-01-03' ORDER BY date")]
    got = membership_report(days, lambda d: membership.members_on(d, events, stable))
    print(f"Üyelik: {got.days} gün, farklı {len(got.differences)}")
    for day, only_official, only_ours in got.differences[:30]:
        print(f"  {day:%d.%m.%Y}: yalnız resmî {only_official} · yalnız bizde {only_ours}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
