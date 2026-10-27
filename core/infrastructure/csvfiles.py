"""
QuantBIST
Reading the personal CSV files: a damaged file is reported, never guessed around.

A file this system wrote always has a header line, so an empty (0 byte)
file means something went wrong. A row with fewer fields than the header
is a line cut off while it was being written; a row with more fields
does not belong to this file. Both stop reading with the line number.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from core.infrastructure.exceptions import PersonalFileError


def read_rows(path: Path, required: Iterable[str] = (), encoding: str = "utf-8-sig") -> list[tuple[int, dict]]:
    """[(line number, row)]; [] when the file does not exist."""

    path = Path(path)
    if not path.exists():
        return []
    if path.stat().st_size == 0:
        raise PersonalFileError(path, "dosya boş (0 bayt); başlık satırı bile yok")
    try:
        with open(path, encoding=encoding, newline="") as fh:
            reader = csv.DictReader(fh)
            missing = set(required) - set(reader.fieldnames or [])
            if missing:
                raise PersonalFileError(path, f"eksik sütunlar {sorted(missing)}", line=1)
            rows = []
            for row in reader:
                line = reader.line_num
                if None in row:
                    raise PersonalFileError(path, "başlıktan fazla alan var", line=line)
                if any(v is None for v in row.values()):
                    raise PersonalFileError(path, "satır yarım kalmış (alan eksik)", line=line)
                if "\x00" in "".join(row.values()):
                    raise PersonalFileError(path, "satırda okunamayan karakterler var", line=line)
                rows.append((line, row))
            return rows
    except (UnicodeDecodeError, csv.Error) as exc:
        raise PersonalFileError(path, f"dosya okunamıyor: {exc}") from exc


def open_append(path: Path):
    """(file, new_file) for appending rows. If the last row was cut off (power loss: no newline
    at the end), a newline is added first, so the new row does not glue onto the broken one.
    Existing bytes are never changed."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    cut = False
    if not new_file and path.stat().st_size > 0:
        with open(path, "rb") as fh:
            fh.seek(-1, 2)
            cut = fh.read(1) != b"\n"
    fh = open(path, "a", encoding="utf-8", newline="")
    if cut:
        fh.write("\n")
    return fh, new_file


__all__ = ["open_append", "read_rows"]
