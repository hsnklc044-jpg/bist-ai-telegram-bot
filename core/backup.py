"""
QuantBIST
Backups of the personal records.

    python -m core.backup                     # back up now
    python -m core.backup --list              # list backups
    python -m core.backup --restore FILE.zip  # restore (current files are backed up first)
    python -m core.backup --test-restore      # restore the newest backups into a temporary folder and read them
    python -m core.backup --market-db         # snapshot data/market.db now

The personal records (ledger, paper orders, watchlist and the logs) exist
only on this machine and are not in git. The daily report backs them up
after every run into a dated zip with a SHA-256 manifest; every zip is
read back and verified after writing. The newest BACKUP_KEEP daily
backups are kept (default 30).

Backups go to data/backups, or to BACKUP_DIR from .env: point it at a
synced folder (e.g. OneDrive) so a disk failure does not take the
backups with it. .env (the bot token) is never backed up.

The price store (data/market.db) is re-downloadable only for the last
five years, so it is snapshotted weekly as well (quantbist_marketdb_*.zip,
newest MARKET_DB_KEEP kept) with SQLite's online backup API, which gives
a consistent copy even while the bot is reading or writing it.

test_restore() restores the newest backups into a temporary folder,
checks every hash and reads every file with the code that uses it
(ledger, paper orders, signal log, equity, alerts, watchlist, SQLite
integrity_check). It never touches the live files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from core.config.paths import (
    ALERTS_LOG_FILE,
    DATA_DIR,
    EQUITY_LOG_FILE,
    LEDGER_FILE,
    MARKET_DB,
    PAPER_ORDERS_FILE,
    SIGNAL_LOG_FILE,
    WATCHLIST_FILE,
)
from core.infrastructure import settings as _settings  # noqa: F401 - loads .env (BACKUP_DIR)
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

PERSONAL_FILES = (
    LEDGER_FILE,
    PAPER_ORDERS_FILE,
    WATCHLIST_FILE,
    ALERTS_LOG_FILE,
    SIGNAL_LOG_FILE,
    EQUITY_LOG_FILE,
)
MANIFEST = "manifest.json"
PREFIX = "quantbist_"
DEFAULT_KEEP = 30
MARKET_DB_PREFIX = f"{PREFIX}marketdb_"
MARKET_DB_KEEP = 4


class BackupError(Exception):
    pass


@dataclass
class Backup:
    path: Path
    files: list[str]

    def line(self) -> str:
        return f"💾 Yedek: {self.path.name} ({len(self.files)} dosya, doğrulandı)"


def backup_dir() -> Path:
    raw = os.getenv("BACKUP_DIR", "").strip()
    return Path(raw) if raw else DATA_DIR / "backups"


def keep_count() -> int:
    raw = os.getenv("BACKUP_KEEP", "").strip()
    return int(raw) if raw else DEFAULT_KEEP


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(path: Path) -> dict[str, str]:
    """Check every file in a backup against its manifest; returns the manifest."""

    try:
        with zipfile.ZipFile(path) as zf:
            manifest = json.loads(zf.read(MANIFEST))
            for name, digest in manifest["files"].items():
                if _sha256(zf.read(name)) != digest:
                    raise BackupError(f"{path.name}: {name} bozuk (özet tutmuyor)")
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as exc:
        raise BackupError(f"{path.name} okunamadı: {exc}") from exc

    return manifest["files"]


def create_backup(
    files: tuple[Path, ...] | list[Path] = PERSONAL_FILES,
    target: Path | None = None,
    name: str | None = None,
    keep: int | None = None,
) -> Backup | None:
    """Zip the existing personal files; None when there is nothing to back up."""

    present = [Path(f) for f in files if Path(f).exists()]

    if not present:
        return None

    target = Path(target or backup_dir())
    target.mkdir(parents=True, exist_ok=True)
    path = target / (name or f"{PREFIX}{date.today():%Y-%m-%d}.zip")
    tmp = path.with_suffix(".tmp")

    manifest = {"created": datetime.now().isoformat(timespec="seconds"), "files": {}}

    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in present:
            data = f.read_bytes()
            zf.writestr(f.name, data)
            manifest["files"][f.name] = _sha256(data)
        zf.writestr(MANIFEST, json.dumps(manifest, indent=2))

    verify(tmp)
    tmp.replace(path)

    if name is None:
        _rotate(target, keep if keep is not None else keep_count())

    logger.info("Backup written | %s | %d files", path, len(present))

    return Backup(path=path, files=sorted(manifest["files"]))


def _daily_backups(target: Path) -> list[Path]:
    """Dated daily backups only (not the safety copies made before a restore)."""

    return sorted(target.glob(f"{PREFIX}????-??-??.zip"))


def _rotate(target: Path, keep: int) -> None:
    for old in _daily_backups(target)[:-keep] if keep > 0 else []:
        old.unlink()
        logger.info("Old backup removed | %s", old.name)


def list_backups(target: Path | None = None) -> list[Path]:
    target = Path(target or backup_dir())
    return sorted(target.glob(f"{PREFIX}*.zip")) if target.exists() else []


def daily_backups(target: Path | None = None) -> list[Path]:
    """Dated backups of the personal records, oldest first."""

    target = Path(target or backup_dir())
    return _daily_backups(target) if target.exists() else []


def market_db_backups(target: Path | None = None) -> list[Path]:
    target = Path(target or backup_dir())
    return sorted(target.glob(f"{MARKET_DB_PREFIX}????-??-??.zip")) if target.exists() else []


def backup_market_db(db: Path | None = None, target: Path | None = None, keep: int = MARKET_DB_KEEP) -> Backup | None:
    """Consistent SQLite snapshot (online backup API), zipped with a manifest."""

    import sqlite3
    import tempfile

    db = Path(db or MARKET_DB)
    if not db.exists():
        return None
    target = Path(target or backup_dir())
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / db.name
        source = sqlite3.connect(db, timeout=60)
        dest = sqlite3.connect(copy)
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()
        backup = create_backup([copy], target=target, name=f"{MARKET_DB_PREFIX}{date.today():%Y-%m-%d}.zip")
    for old in market_db_backups(target)[:-keep] if keep > 0 else []:
        old.unlink()
    return backup


def _check_file(path: Path) -> str:
    """Read one restored file with the code that uses it; returns a short description."""

    import csv as _csv
    import sqlite3

    name = path.name
    if name == LEDGER_FILE.name:
        from core.ledger.book import load_ledger, replay

        entries = load_ledger(path)
        replay(entries)  # books must still balance (no sale above holdings)
        return f"defter {len(entries)} satır"
    if name == PAPER_ORDERS_FILE.name:
        from core.ledger.paper import load_orders

        return f"sanal emir {len(load_orders(path))}"
    if name == WATCHLIST_FILE.name:
        return f"takip listesi {len(json.loads(path.read_text(encoding='utf-8')))} kullanıcı"
    if name == MARKET_DB.name:
        conn = sqlite3.connect(path)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise BackupError(f"{name}: SQLite bütünlük kontrolü: {result}")
            tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        finally:
            conn.close()
        return f"fiyat veritabanı bütünlük ok ({tables} tablo)"
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(_csv.DictReader(fh))
    return f"{path.stem} {len(rows)} satır"


def test_restore(paths: list[Path] | None = None) -> list[str]:
    """
    Restore backups into a temporary folder and read every file back.
    Default: the newest daily backup and the newest price store snapshot.
    Raises BackupError on any problem; returns one line per checked file.
    """

    import tempfile

    if paths is None:
        paths = [p for p in (daily_backups()[-1:] + market_db_backups()[-1:])]
    if not paths:
        raise BackupError("test edilecek yedek yok")
    lines = []
    for path in paths:
        names = verify(path)
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(path) as zf:
                for name in names:
                    (Path(tmp) / name).write_bytes(zf.read(name))
            for name in sorted(names):
                try:
                    lines.append(f"{path.name}: {_check_file(Path(tmp) / name)}")
                except BackupError:
                    raise
                except Exception as exc:  # noqa: BLE001 - any unreadable file fails the test
                    raise BackupError(f"{path.name}: {name} geri yüklendi ama okunamadı: {exc}") from exc
    return lines


def restore_backup(path: Path, data_dir: Path = DATA_DIR) -> tuple[list[str], Backup | None]:
    """
    Restore a backup into data_dir. The backup is verified first, and the
    current files are saved to a safety backup before anything is replaced.
    Returns (restored file names, safety backup).
    """

    path = Path(path)
    names = verify(path)
    data_dir = Path(data_dir)

    safety = create_backup(
        [data_dir / n for n in names],
        target=path.parent,
        name=f"{PREFIX}before_restore_{datetime.now():%Y%m%d-%H%M%S}.zip",
    )

    with zipfile.ZipFile(path) as zf:
        for name in names:
            (data_dir / name).write_bytes(zf.read(name))

    logger.info("Backup restored | %s | %d files", path.name, len(names))

    return sorted(names), safety


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up / restore QuantBIST personal records")
    parser.add_argument("--list", action="store_true", help="yedekleri listele")
    parser.add_argument("--restore", metavar="ZIP", help="bu yedeği geri yükle")
    parser.add_argument("--test-restore", action="store_true", help="son yedekleri geçici klasöre açıp oku")
    parser.add_argument("--market-db", action="store_true", help="fiyat veritabanını şimdi yedekle")
    args = parser.parse_args(argv)

    try:
        if args.list:
            backups = list_backups()
            for p in backups:
                print(f"{p.name}  {len(verify(p))} dosya")
            print(f"{len(backups)} yedek, klasör: {backup_dir()}")
            return 0

        if args.test_restore:
            for line in test_restore():
                print(line)
            print("Geri yükleme testi başarılı (canlı dosyalara dokunulmadı).")
            return 0

        if args.market_db:
            backup = backup_market_db()
            print(backup.line() + f"\n{backup.path}" if backup else "Fiyat veritabanı yok.")
            return 0

        if args.restore:
            names, safety = restore_backup(Path(args.restore))
            print(f"Geri yüklendi: {', '.join(names)}")
            if safety:
                print(f"Önceki hâl şuraya yedeklendi: {safety.path}")
            return 0

        backup = create_backup()
        print(backup.line() + f"\n{backup.path}" if backup else "Yedeklenecek kişisel dosya yok.")
        return 0
    except BackupError as exc:
        print(f"HATA: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PERSONAL_FILES",
    "Backup",
    "BackupError",
    "backup_dir",
    "backup_market_db",
    "create_backup",
    "daily_backups",
    "list_backups",
    "market_db_backups",
    "test_restore",
    "restore_backup",
    "verify",
]
