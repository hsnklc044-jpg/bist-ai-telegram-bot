"""
QuantBIST
Fundamental data with the time each item was PUBLISHED (DECISIONS K-48).

data/fundamentals.csv, one row per item of one report:
    symbol, period_end, published_at, item, value, unit, consolidated, inflation_adjusted, source, recorded_at

- A session sees an item only if it was published BEFORE that session's day (a report sent at
  18:30 is usable from the next session on): no look-ahead.
- A restatement is a new row with a later published_at; the newest publication of the newest
  period wins on each day. Nothing is overwritten (append-only).
- inflation_adjusted marks TMS 29 tables (from the 2023 year-end reports on): 1 / 0 / empty
  (unknown). Growth rates must not mix the two; the cards show them apart.
- Rows come in only by a checked file import (KAP's terms for automated fetching are not
  confirmed, so this module has no network code at all).

    python -m core.fundamentals.store --import FILE      # check and append
    python -m core.fundamentals.store --compare FILE      # differences against a second source
    python -m core.fundamentals.store --status            # what /durum shows
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from core.config.paths import FUNDAMENTALS_FILE
from core.infrastructure.csvfiles import open_append

COLUMNS = ("symbol", "period_end", "published_at", "item", "value", "unit", "consolidated", "inflation_adjusted",
           "source", "recorded_at")
SOURCE_COLUMNS = COLUMNS[:-1]

# the items the professional filters need (Piotroski, Altman, Beneish, Greenblatt, Novy-Marx), in TL
ITEMS = {
    "revenue": "hasılat (satışlar)",
    "cost_of_sales": "satışların maliyeti",
    "gross_profit": "brüt kâr",
    "operating_profit": "esas faaliyet kârı (FVÖK yerine)",
    "ebit": "faiz ve vergi öncesi kâr",
    "net_income": "net dönem kârı (ana ortaklık)",
    "operating_cash_flow": "işletme faaliyetlerinden nakit akışı",
    "depreciation": "amortisman ve itfa",
    "sga": "genel yönetim + pazarlama giderleri",
    "total_assets": "toplam varlıklar",
    "current_assets": "dönen varlıklar",
    "receivables": "ticari alacaklar",
    "ppe": "maddi duran varlıklar",
    "cash": "nakit ve nakit benzerleri",
    "total_liabilities": "toplam yükümlülükler",
    "current_liabilities": "kısa vadeli yükümlülükler",
    "long_term_debt": "uzun vadeli finansal borçlar",
    "financial_debt": "toplam finansal borçlar",
    "total_equity": "özkaynaklar (ana ortaklık)",
    "retained_earnings": "geçmiş yıllar kârları",
    "paid_in_capital": "ödenmiş sermaye (nominal TL = pay adedi)",
    "dividends_paid": "ödenen temettü",
}
CORE_ITEMS = ("revenue", "gross_profit", "net_income", "operating_cash_flow", "total_assets", "total_equity",
              "current_assets", "current_liabilities", "paid_in_capital")
_SYMBOL = re.compile(r"[A-Z0-9]{3,6}")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def _check(r: dict) -> tuple[dict | None, str]:
    """(clean row, "") or (None, reason)."""

    symbol = (r.get("symbol") or "").strip().upper().removesuffix(".IS")
    if not _SYMBOL.fullmatch(symbol):
        return None, f"geçersiz hisse kodu '{r.get('symbol')}'"
    period = (r.get("period_end") or "").strip()
    if not _DAY.fullmatch(period):
        return None, f"dönem sonu tarihi YYYY-AA-GG olmalı ('{period}')"
    try:
        published = datetime.fromisoformat((r.get("published_at") or "").strip())
    except ValueError:
        return None, f"yayın tarihi okunamadı ('{r.get('published_at')}')"
    if published.date() <= date.fromisoformat(period):
        return None, f"yayın tarihi dönem sonundan sonra olmalı ({published:%d.%m.%Y} ≤ {period})"
    item = (r.get("item") or "").strip()
    if item not in ITEMS:
        return None, f"bilinmeyen kalem '{item}'"
    try:
        value = float((r.get("value") or "").strip())
    except ValueError:
        return None, f"değer bir sayı olmalı ('{r.get('value')}')"
    consolidated = (r.get("consolidated") or "").strip()
    inflation = (r.get("inflation_adjusted") or "").strip()
    if consolidated not in ("1", "0") or inflation not in ("1", "0", ""):
        return None, "konsolide 1/0, enflasyon düzeltmesi 1/0/boş olmalı"
    source = (r.get("source") or "").strip()
    if not source:
        return None, "kaynak boş (KAP bildirim bağlantısı ya da sağlayıcı adı)"
    return {"symbol": symbol, "period_end": period, "published_at": published.isoformat(timespec="seconds"),
            "item": item, "value": repr(value), "unit": (r.get("unit") or "TL").strip(),
            "consolidated": consolidated, "inflation_adjusted": inflation, "source": source}, ""


def _key(r: dict) -> tuple:
    return r["symbol"], r["period_end"], r["item"], r["published_at"], r["consolidated"]


def load(path: Path | None = None) -> pd.DataFrame:
    path = Path(path or FUNDAMENTALS_FILE)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    data = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing = set(COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"{path.name}: eksik sütun {sorted(missing)}")
    return data


def import_file(source: Path, path: Path | None = None, now: datetime | None = None) -> tuple[int, list[str]]:
    """Check every row of `source` and append the new valid ones; (added, rejected reasons)."""

    from core.market.calendar import now_istanbul

    path = Path(path or FUNDAMENTALS_FILE)
    known = {_key(r) for r in load(path).to_dict("records")}
    rows, rejected = [], []
    with open(source, encoding="utf-8-sig", newline="") as fh:
        for n, r in enumerate(csv.DictReader(fh), start=2):
            clean, why = _check(r)
            if clean is None:
                rejected.append(f"satır {n}: {why}")
            elif _key(clean) not in known:
                known.add(_key(clean))
                rows.append(clean)
    if rows:
        stamp = (now or now_istanbul()).isoformat(timespec="seconds")
        fh, new_file = open_append(path)
        with fh:
            writer = csv.DictWriter(fh, COLUMNS, lineterminator="\n")
            if new_file:
                writer.writeheader()
            for r in rows:
                writer.writerow({**r, "recorded_at": stamp})
    return len(rows), rejected


def _usable(data: pd.DataFrame, symbol: str, item: str) -> pd.DataFrame:
    part = data[(data["symbol"] == symbol.removesuffix(".IS")) & (data["item"] == item)].copy()
    if part.empty:
        return part
    part["published"] = pd.to_datetime(part["published_at"], utc=True).dt.tz_convert("Europe/Istanbul")
    part["usable"] = part["published"].dt.normalize().dt.tz_localize(None) + pd.Timedelta(days=1)
    part["value"] = part["value"].astype(float)
    # consolidated tables first when a company sends both
    return part.sort_values(["usable", "period_end", "consolidated", "published"])


def as_of(data: pd.DataFrame, symbol: str, item: str, day: date) -> float | None:
    """The value known before `day`'s session: newest period, then its newest publication."""

    part = _usable(data, symbol, item)
    if part.empty:
        return None
    known = part[part["usable"] <= pd.Timestamp(day)]
    if known.empty:
        return None
    best = known.sort_values(["period_end", "consolidated", "published"]).iloc[-1]
    return float(best["value"])


def panel(data: pd.DataFrame, item: str, symbols, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Point-in-time values on every session of `index` (NaN until the first publication)."""

    out = {}
    for symbol in symbols:
        code = symbol.removesuffix(".IS")
        part = _usable(data, code, item)
        if part.empty:
            out[code] = pd.Series(float("nan"), index=index)
            continue
        events = [(day, float(as_of(data, code, item, day.date()))) for day in sorted(set(part["usable"]))]
        steps = pd.Series(dict(events)).sort_index()
        out[code] = steps.reindex(index.union(steps.index)).ffill().reindex(index)
    return pd.DataFrame(out, index=index)


def status_text(path: Path | None = None, symbols=None) -> str:
    """The /durum line: last publication, how many stocks have every core item."""

    try:
        data = load(path)
    except (OSError, ValueError) as exc:
        return f"okunamadı ({exc})"
    if data.empty:
        return ("veri yok. KAP'tan otomatik çekme kullanım koşulları teyit edilene kadar kapalı (K-48); "
                "içe aktarma: python -m core.fundamentals.store --import DOSYA")
    codes = [s.removesuffix(".IS") for s in (symbols or sorted(set(data["symbol"])))]
    complete = 0
    for code in codes:
        part = data[data["symbol"] == code]
        if part.empty:
            continue
        latest = part["period_end"].max()
        if set(CORE_ITEMS) <= set(part.loc[part["period_end"] == latest, "item"]):
            complete += 1
    last = pd.to_datetime(data["published_at"], utc=True).max().tz_convert("Europe/Istanbul")
    return (f"son yayın {last:%d.%m.%Y}; {len(codes)} hisseden {complete}'{'inde' if complete else 'inde'} eksiksiz "
            f"({len(CORE_ITEMS)} ana kalem, son dönem); ikinci kaynak karşılaştırması: --compare")


def compare(path: Path | None, other: Path, tolerance: float = 0.005) -> str:
    """Differences between our rows and a second source's file (same columns), item by item."""

    ours = load(path)
    theirs = pd.read_csv(other, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    key = ["symbol", "period_end", "item", "consolidated"]
    for frame in (ours, theirs):
        frame["symbol"] = frame["symbol"].str.upper().str.removesuffix(".IS")
    latest = lambda f: f.sort_values("published_at").groupby(key, as_index=False).last()  # noqa: E731
    both = latest(ours).merge(latest(theirs), on=key, suffixes=("", "_2"))
    same, lines = 0, []
    for r in both.itertuples():
        a, b = float(r.value), float(r.value_2)
        gap = abs(a - b) / max(abs(a), 1e-9)  # relative to our value
        if gap <= tolerance:
            same += 1
        else:
            lines.append(f"  {r.symbol} {r.period_end} {r.item}: {a:,.0f} / {b:,.0f} (fark %{gap * 100:.1f})"
                         .replace(".", "§").replace(",", ".").replace("§", ","))
    band = f"{tolerance * 100:.1f}".replace(".", ",")
    head = (f"Temel veri ikinci kaynak karşılaştırması: {len(both)} ortak kalem, {same} kalem aynı (±%{band}), "
            f"{len(lines)} farklı; {len(set(both['symbol']))} hisse")
    return "\n".join([head, *lines])


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="QuantBIST temel veri deposu (yayın tarihli)")
    parser.add_argument("--import", dest="source", metavar="DOSYA")
    parser.add_argument("--compare", metavar="DOSYA")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    if args.source:
        added, rejected = import_file(Path(args.source))
        print(f"{added} satır eklendi, {len(rejected)} satır reddedildi")
        print("\n".join(rejected))
        return 1 if rejected else 0
    if args.compare:
        print(compare(None, Path(args.compare)))
        return 0
    print(status_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["COLUMNS", "CORE_ITEMS", "ITEMS", "as_of", "compare", "import_file", "load", "panel", "status_text"]
