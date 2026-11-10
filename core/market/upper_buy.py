"""
QuantBIST
The user's upper buy price per stock, kept between sessions (the 6-12 month model's entry rule: the price must
not be above it). It is the user's own limit, never computed here and never a recommendation.

data/upper_buy.csv is personal and append-only: a row per set or clear (columns at, symbol, price, note); the
last row of a symbol decides and an empty price closes the record. Backed up, health-checked, never in git.

    /uzun_ust THYAO 250     set        /uzun_ust THYAO sil     clear        /uzun_ust    the list
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path

from core.config.paths import UPPER_BUY_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.infrastructure.exceptions import PersonalFileError

FILE = UPPER_BUY_FILE
COLUMNS = ("at", "symbol", "price", "note")
MAX_PRICE = 1_000_000.0  # a typing slip (an extra zero) is caught, not stored
USAGE = ("Kullanım:\n/uzun_ust THYAO 250  (üst alım fiyatını kaydet)\n/uzun_ust THYAO sil  (kaydı kapat)\n"
         "/uzun_ust  (kayıtlı fiyatlar)")
CLEAR_WORDS = ("sil", "kapat", "iptal")


def _n(value: float) -> str:
    return f"{value:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _parse(raw: str) -> float:
    text = raw.strip().replace(" ", "")
    if "," in text and "." in text:  # 1.250,50
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        raise ValueError("Fiyat sayı olmalı: /uzun_ust THYAO 250") from None
    if not math.isfinite(value) or not 0 < value <= MAX_PRICE:
        raise ValueError(f"Fiyat 0'dan büyük ve en fazla {_n(MAX_PRICE)} olmalı.")
    return value


def history(path: Path | None = None) -> list[tuple[str, str, float | None]]:
    """(at, symbol, price) in file order; price None for a clear. A broken price names its line."""

    path = Path(path or FILE)
    out = []
    for line, row in read_rows(path, COLUMNS):
        raw = (row["price"] or "").strip()
        try:
            price = float(raw) if raw else None
        except ValueError:
            raise PersonalFileError(path, f"{line}. satır: fiyat sayı değil ({raw!r})") from None
        if price is not None and not (math.isfinite(price) and price > 0):
            raise PersonalFileError(path, f"{line}. satır: fiyat sıfırdan büyük olmalı ({raw!r})")
        out.append((row["at"], row["symbol"].strip().upper(), price))
    return out


def load(path: Path | None = None) -> dict[str, tuple[float, str]]:
    """symbol -> (price in force, the day it was set); the last row for a symbol decides."""

    found: dict[str, tuple[float, str]] = {}
    for at, symbol, price in history(path):
        if price is None:
            found.pop(symbol, None)
        else:
            found[symbol] = (price, at[:10])
    return found


def latest(symbol: str, path: Path | None = None) -> float | None:
    """The price in force for a symbol (with or without the .IS suffix), or None."""

    key = symbol.strip().upper()
    found = load(path).get(key if key.endswith(".IS") else key + ".IS")
    return found[0] if found else None


def _append(symbol: str, price: float | None, path: Path | None, now: datetime | None) -> None:
    from core.market.calendar import now_istanbul

    path = Path(path or FILE)
    fh, new_file = open_append(path)
    with fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(COLUMNS)
        writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), symbol,
                         "" if price is None else repr(price), ""])


def command_text(words: list[str], path: Path | None = None, now: datetime | None = None) -> str:
    """The /uzun_ust answer. Raises ValueError for a bad symbol or price (the message is the answer)."""

    from core.watchlist.service import normalize_symbol

    if not words:
        found = load(path)
        if not found:
            return "Kayıtlı üst alım fiyatı yok.\n" + USAGE
        lines = [f"{s.removesuffix('.IS')}: {_n(price)} TL (kayıt {day[8:10]}.{day[5:7]}.{day[:4]})"
                 for s, (price, day) in sorted(found.items())]
        return "📌 Üst alım fiyatların:\n" + "\n".join(lines) + "\nSınır senindir; öneri değildir."
    if len(words) != 2:
        return USAGE
    symbol = normalize_symbol(words[0])
    code = symbol.removesuffix(".IS")
    if words[1].strip().lower() in CLEAR_WORDS:
        if symbol not in load(path):
            return f"{code} için kayıtlı üst alım fiyatı yok."
        _append(symbol, None, path, now)
        return f"🗑 {code} üst alım fiyatı kaydı kapatıldı."
    price = _parse(words[1])
    before = load(path).get(symbol)
    _append(symbol, price, path, now)
    changed = f" (önceki: {_n(before[0])})" if before else ""
    return (f"✅ {code} üst alım fiyatı {_n(price)} TL olarak kaydedildi{changed}. /uzun {code} bunu kullanır; "
            f"komutta verdiğin fiyat bu çağrı için kaydı geçersiz kılar. Sınır senindir; öneri değildir.")
