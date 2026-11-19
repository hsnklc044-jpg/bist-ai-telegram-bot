"""Corporate-actions event table: schema and validator only (#1, K-113 Dalga 2).

`data/kurumsal_islemler.csv` is a register of company events; it is tracked with its header only and
is filled by hand later, each row with its source. It does not replace `data/corporate_actions.csv`
(the price-adjustment table read by core.market.corrections); nothing reads this table yet.

Columns (UTF-8, comma separated, header exactly in this order):

| column       | content                                                                 |
|--------------|-------------------------------------------------------------------------|
| symbol       | BIST code, capital letters and digits, optional ".IS" (e.g. ABCDE)      |
| event_type   | bolunme, bedelsiz, bedelli, temettu, kod_degisikligi, birlesme          |
| ex_date      | the ex / effective date, YYYY-MM-DD                                     |
| ratio        | new shares per old share (1 = %100); bolunme, bedelsiz, bedelli need it |
| amount       | TL per share: bedelli subscription price, temettu gross dividend        |
| new_symbol   | kod_degisikligi: the new code; birlesme: the code that remains          |
| source_url   | http(s) address of the source (KAP or the company's announcement)       |
| note         | free text                                                               |

Rules: event type from the list; a real date; the numbers the type needs are positive and finite;
a source address on every row; one row per (symbol, event_type, ex_date).
"""

from __future__ import annotations

import csv
import math
import re
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

TABLE_FILE = Path(__file__).resolve().parents[2] / "data" / "kurumsal_islemler.csv"
COLUMNS = ("symbol", "event_type", "ex_date", "ratio", "amount", "new_symbol", "source_url", "note")
EVENT_TYPES = ("bolunme", "bedelsiz", "bedelli", "temettu", "kod_degisikligi", "birlesme")
NEEDS_RATIO = ("bolunme", "bedelsiz", "bedelli")
NEEDS_AMOUNT = ("bedelli", "temettu")
NEEDS_NEW_SYMBOL = ("kod_degisikligi", "birlesme")
_SYMBOL = re.compile(r"^[A-Z0-9]{2,8}(\.IS)?$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _positive(text: str) -> bool:
    try:
        value = float(text)
    except ValueError:
        return False
    return math.isfinite(value) and value > 0


def _row_problems(row: Mapping[str, str]) -> list[str]:
    get = {c: (row.get(c) or "").strip() for c in COLUMNS}
    problems = []
    if not _SYMBOL.match(get["symbol"]):
        problems.append(f"symbol geçersiz ({get['symbol']!r}; büyük harf ve rakam, isteğe bağlı .IS)")
    kind = get["event_type"]
    if kind not in EVENT_TYPES:
        problems.append(f"event_type bilinmiyor ({kind!r}; izinli: {', '.join(EVENT_TYPES)})")
    text = get["ex_date"]
    try:
        if not _ISO_DATE.match(text):
            raise ValueError
        date.fromisoformat(text)
    except ValueError:
        problems.append(f"ex_date geçerli bir YYYY-AA-GG tarihi değil ({text!r})")
    for column in ("ratio", "amount"):
        if get[column] and not _positive(get[column]):
            problems.append(f"{column} pozitif ve sonlu bir sayı olmalı ({get[column]!r})")
    if kind in NEEDS_RATIO and not get["ratio"]:
        problems.append(f"{kind} için ratio gerekli")
    if kind in NEEDS_AMOUNT and not get["amount"]:
        problems.append(f"{kind} için amount (TL/pay) gerekli")
    if kind in NEEDS_NEW_SYMBOL:
        new = get["new_symbol"]
        if not _SYMBOL.match(new):
            problems.append(f"{kind} için geçerli bir new_symbol gerekli ({new!r})")
        elif new.removesuffix(".IS") == get["symbol"].removesuffix(".IS"):
            problems.append("new_symbol eski kodla aynı olamaz")
    if not re.match(r"^https?://\S+$", get["source_url"]):
        problems.append("source_url gerekli (http:// ya da https:// ile başlayan kaynak adresi)")
    return problems


def validate_rows(rows: Iterable[Mapping[str, str]], first_line: int = 2) -> list[str]:
    """Problems of the rows, one text per bad row; an empty list means every row is valid.
    `first_line` is the file line of the first row (2: right after the header)."""

    problems, seen = [], set()
    for line, row in enumerate(rows, start=first_line):
        found = _row_problems(row)
        key = tuple((row.get(c) or "").strip().removesuffix(".IS") if c == "symbol"
                    else (row.get(c) or "").strip() for c in ("symbol", "event_type", "ex_date"))
        if not found and key in seen:
            found = [f"tekrar eden satır ({', '.join(key)})"]
        seen.add(key)
        if found:
            problems.append(f"satır {line}: " + "; ".join(found))
    return problems


def validate_file(path: Path | str | None = None) -> list[str]:
    """Problems of the whole file (header first); an empty list means the file is valid."""

    path = Path(path or TABLE_FILE)
    if not path.exists():
        return [f"{path.name} bulunamadı"]
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            header = tuple(reader.fieldnames or ())
            if header != COLUMNS:
                return [f"{path.name} başlık satırı şema ile aynı değil: beklenen {','.join(COLUMNS)}"]
            rows = [r for r in reader if any((v or "").strip() for v in r.values() if isinstance(v, str))]
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return [f"{path.name} okunamadı: {exc}"]
    return [f"{path.name} {p}" for p in validate_rows(rows)]


__all__ = ["COLUMNS", "EVENT_TYPES", "TABLE_FILE", "validate_file", "validate_rows"]
