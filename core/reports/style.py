"""Message style for every user message (A and B, the user's 11.11.2026 decision; docs/MESAJ_STILI.md).

A message answers three questions: is everything fine, what important changed, does the user need to do something.
Everything else goes to a "detay" command. First line: title and date in capitals; second line: a status mark
(✅ ⚠️ ❌) or a score class colour and one sentence. Problems only when there are problems; "Senden beklenen:" only
when something is expected. Turkish numbers. No internal codes or developer terms; never AL or SAT."""

from __future__ import annotations

import re
from datetime import date

# B: score classes (fixed; an explanation, not a recommendation)
CLASSES = ((80, "🟢", "Güçlü"), (60, "🟢", "Olumlu"), (40, "🟡", "Karışık"), (20, "🟠", "Zayıf"), (0, "🔴", "Çok zayıf"))

# A: line limits (non-empty lines); (no problem, with problems)
LIMITS = {"gunluk": (7, 7), "robot": (3, 6), "haftalik": (3, 6), "uyari": (4, 4), "abonelik": (9, 9)}
TABLE_WIDTH = 32
ALLOWED_EMOJI = set("✅⚠❌🟢🟡🟠🔴🔔█░") | {"\ufe0f"}  # █ ░: the 10-box bars of /karne (D)
_EMOJI = re.compile("[←-⇿⌀-⏿①-➿⤀-⥿⬀-⯿\U0001f000-\U0001faff️]")

FORBIDDEN = (
    ("sürüm numarası", re.compile(r"\bv\d+\.\d+")),
    ("CI", re.compile(r"\bCI\b")),
    ("SLO", re.compile(r"\bSLO\b")),
    ("SHA", re.compile(r"\bSHA(-?256)?\b")),
    ("K-numarası", re.compile(r"\bK-\d+")),
    ("D-numarası", re.compile(r"\bD-?\d{1,3}\b")),
    ("HTTP hata adı", re.compile(r"\bHTTP\b")),
    ("dosya yolu", re.compile(r"[A-Za-z]:\\|\b[\w.-]+/[\w./-]+\.(py|log|csv|json|jsonl|txt|md|db|zip)\b")),
    ("ATR", re.compile(r"\bATR\b")),
    ("CHARTER", re.compile(r"\bCHARTER\b")),
    ("AL", re.compile(r"(?<![\wÇĞİÖŞÜçğıöşü])AL(?![\wÇĞİÖŞÜçğıöşü])")),
    ("SAT", re.compile(r"(?<![\wÇĞİÖŞÜçğıöşü])SAT(?![\wÇĞİÖŞÜçğıöşü])")),
)


def number(x: float, decimals: int = 2) -> str:
    text = f"{x:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def percent(x: float) -> str:
    """Signed, one decimal: +1,2% / -4,6% / 0,0%."""

    value = round(x * 100, 1)
    if value == 0:
        return "0,0%"
    return ("+" if value > 0 else "") + number(value, 1) + "%"


def price(x: float) -> str:
    return f"{number(x, 0 if abs(x) >= 1000 else 2)} TL"


def score_class(score: float | None) -> tuple[str, str] | None:
    if score is None:
        return None
    if not 0 <= score <= 100:
        raise ValueError(f"puan 0–100 dışında: {score}")
    for limit, colour, name in CLASSES:
        if score >= limit:
            return colour, name
    raise AssertionError(score)


def upper_tr(text: str) -> str:
    return text.replace("i", "İ").replace("ı", "I").upper()


def header(title: str, day: date, mark: str | None = None, sentence: str | None = None) -> str:
    first = f"{upper_tr(title)} · {day:%d.%m.%Y}"
    if mark is None and sentence is None:
        return first
    return f"{first}\n{' '.join(x for x in (mark, sentence) if x)}"


def forbidden(text: str) -> list[str]:
    """The internal codes and developer terms (and AL / SAT) found in a user message."""

    return [name for name, pattern in FORBIDDEN if pattern.search(text)]


def problems(text: str, kind: str, sorun: bool = False) -> list[str]:
    """What breaks the style rules: line count for the kind, table width, emojis, forbidden terms."""

    found = []
    counted = re.sub(r"<pre>.*?</pre>", "<tablo>", text, flags=re.S)  # a table counts as one line
    lines = [line for line in counted.splitlines() if line.strip()]
    if kind in LIMITS:
        limit = LIMITS[kind][1 if sorun else 0]
        if len(lines) > limit:
            found.append(f"{len(lines)} satır; en fazla {limit}")
    for block in re.findall(r"<pre>(.*?)</pre>", text, flags=re.S):
        for row in block.splitlines():
            if len(row) > TABLE_WIDTH:
                found.append(f"tablo satırı {len(row)} karakter; en fazla {TABLE_WIDTH}: {row}")
    extra = sorted({c for c in _EMOJI.findall(text) if c not in ALLOWED_EMOJI})
    if extra:
        found.append("izin dışı emoji: " + " ".join(extra))
    found += [f"yasak terim: {name}" for name in forbidden(text)]
    return found


__all__ = ["CLASSES", "LIMITS", "TABLE_WIDTH", "forbidden", "header", "number", "percent", "price", "problems",
           "score_class", "upper_tr"]
