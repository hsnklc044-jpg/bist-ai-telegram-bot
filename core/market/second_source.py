"""
QuantBIST
Independent second price source (v0.99.42, docs/AUDIT.md EVRE 1 bulgu 3).

The only job of a second source is to check the primary one (Yahoo) independently, so:
- a source whose numbers come from the primary is refused (Yahoo checked against Yahoo would
  always read "100% right");
- a network source runs only after the user approved it with its terms on record, and never
  against robots.txt (İş Yatırım stays closed, K-54);
- sources fall back only to other independent sources; with none the answer is "ölçülemiyor",
  never a success.

The first source needs no network: a price file the user downloaded (an intermediary's export,
Borsa İstanbul's bulletin...). Columns: date, code, close (comma or semicolon separated, a
decimal comma is accepted).

    python -m core.market.second_source --dosya FIYATLAR.csv --kaynak "aracı kurum dışa aktarımı"
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Protocol

import pandas as pd

from core.config.paths import LOG_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

PRIMARY_ORIGIN = "yahoo"  # the price store's own source
SUMMARY_FILE = LOG_DIR / "price_second_source.json"  # read by the "Veri doğruluğu" SLO


class Status(str, Enum):
    OK = "ok"
    UNMEASURABLE = "olculemiyor"


@dataclass(frozen=True)
class SourceInfo:
    name: str
    origin: str  # who produces the numbers; must not be the primary
    network: bool
    approved_on: date | None = None  # the user's approval after reading the terms
    terms_doc: str | None = None  # where the terms are recorded (docs/DATA_SOURCES.md)


class SecondSource(Protocol):
    info: SourceInfo

    async def closes(self, codes: list[str], start: date, end: date) -> dict[str, pd.Series]: ...


class SourceRefused(RuntimeError):
    """Not independent, or a network source without the user's recorded approval."""


def usable(source: SecondSource) -> None:
    info = source.info
    if info.origin.strip().lower() == PRIMARY_ORIGIN:
        raise SourceRefused(f"{info.name}: kökeni birincil kaynakla aynı ({info.origin}); doğrulama olmaz")
    if info.network and (info.approved_on is None or not info.terms_doc):
        raise SourceRefused(f"{info.name}: kullanım koşulları onaylanmadı; çalıştırılmaz")


def read_price_file(path: Path) -> pd.DataFrame:
    """date, code, close; ',' or ';' separated; a decimal comma is accepted; codes without .IS."""

    text = Path(path).read_text(encoding="utf-8-sig")
    first = text.splitlines()[0] if text else ""
    sep = ";" if first.count(";") > first.count(",") else ","
    df = pd.read_csv(Path(path), sep=sep, dtype=str, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    missing = {"date", "code", "close"} - set(df.columns)
    if missing:
        raise ValueError(f"eksik sütun: {', '.join(sorted(missing))} (gereken: date, code, close)")
    close = df["close"].str.strip()
    if sep == ";":
        close = close.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    out = pd.DataFrame({
        "date": pd.to_datetime(df["date"].str.strip(), dayfirst="." in str(df["date"].iloc[0]) if len(df) else False),
        "code": df["code"].str.strip().str.upper().str.removesuffix(".IS"),
        "close": pd.to_numeric(close, errors="coerce"),
    })
    bad = out["close"].isna() | ~(out["close"] > 0)
    if bad.any():
        raise ValueError(f"{int(bad.sum())} satırda kapanış okunamadı ya da sıfır/negatif")
    return out


class FileSource:
    """A price file the user downloaded: no network, so no terms question."""

    def __init__(self, path: Path | str, origin: str) -> None:
        self.path = Path(path)
        self.info = SourceInfo(f"dosya:{self.path.name}", origin, network=False)

    async def closes(self, codes: list[str], start: date, end: date) -> dict[str, pd.Series]:
        return await asyncio.to_thread(self._read, codes, start, end)

    def _read(self, codes: list[str], start: date, end: date) -> dict[str, pd.Series]:
        df = read_price_file(self.path)
        df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end) & df["code"].isin(codes)]
        return {c: g.set_index("date")["close"].sort_index() for c, g in df.groupby("code")}


async def verify(sources: list[SecondSource], codes: list[str], start: date, end: date
                 ) -> tuple[Status, str, dict[str, pd.Series]]:
    """The first usable independent source that answers; none: UNMEASURABLE (never the primary)."""

    for source in sources:
        try:
            usable(source)
            got = await source.closes(codes, start, end)
        except SourceRefused as exc:
            logger.warning("Second source refused | %s", exc)
            continue
        except Exception:  # noqa: BLE001 - network or file trouble: the next independent source
            logger.exception("Second source failed | %s", source.info.name)
            continue
        if got:
            return Status.OK, source.info.name, got
    return Status.UNMEASURABLE, "bağımsız ikinci kaynak yok", {}


def check(sources: list[SecondSource], codes: list[str], start: date, end: date, bars=None,
          today: date | None = None) -> tuple[Status, str, list, dict | None]:
    """(status, source, CrossCheck results, the SLO summary) with the unchanged comparison rules."""

    from core.market import crosscheck
    from core.market.corrections import load_corporate_actions

    if bars is None:
        from core.reports.daily import raw_bars as bars
    status, name, got = asyncio.run(verify(sources, codes, start, end))
    if status is not Status.OK:
        return status, name, [], None
    actions: dict[str, set[date]] = {}
    for a in load_corporate_actions():
        actions.setdefault(a.symbol.removesuffix(".IS"), set()).add(a.ex_date)
    results = []
    for code in sorted(got):
        symbol = f"{code}.IS"
        try:
            results.append(crosscheck.compare(symbol, bars(symbol), got[code].to_frame("close"), actions.get(code)))
        except Exception as exc:  # noqa: BLE001 - one stock must not stop the check
            logger.exception("Comparison failed | %s", symbol)
            results.append(crosscheck.CrossCheck(symbol, error=f"karşılaştırma hatası: {type(exc).__name__}"))
    crosscheck.format_report(results, f"{start:%d.%m.%Y} – {end:%d.%m.%Y}")  # marks market-wide dates
    summary = crosscheck.summary(results, today or end)
    summary["source"] = name
    return status, name, results, summary


def save_summary(summary: dict, path: Path | None = None) -> None:
    path = Path(path or SUMMARY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse

    from core.infrastructure.console import utf8_output
    from core.market import crosscheck

    utf8_output()
    parser = argparse.ArgumentParser(description="Fiyatları bağımsız ikinci kaynakla karşılaştır (dosya)")
    parser.add_argument("--dosya", required=True, help="date, code, close sütunlu fiyat dosyası")
    parser.add_argument("--kaynak", required=True, help="dosyanın geldiği yer (ör. 'aracı kurum dışa aktarımı')")
    args = parser.parse_args(argv)
    frame = read_price_file(Path(args.dosya))
    codes = sorted(frame["code"].unique())
    start, end = frame["date"].min().date(), frame["date"].max().date()
    status, name, results, summary = check([FileSource(args.dosya, args.kaynak)], codes, start, end)
    if summary is None:
        print(f"Veri doğruluğu ölçülemiyor: {name}")
        return 1
    print(crosscheck.format_report(results, f"{start:%d.%m.%Y} – {end:%d.%m.%Y}"))
    save_summary(summary)
    print(f"Özet kaydedildi ({args.kaynak}): {summary['checked']} hisse, {len(summary['differing'])} farklı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["FileSource", "PRIMARY_ORIGIN", "SecondSource", "SourceInfo", "SourceRefused", "Status", "check",
           "read_price_file", "save_summary", "usable", "verify"]
