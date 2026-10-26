"""
QuantBIST
Backups of the personal records.

    python -m core.backup                     # back up now
    python -m core.backup --list              # list backups
    python -m core.backup --restore FILE.zip  # restore (current files are backed up first)

The personal records (ledger, paper orders, watchlist and the logs) exist
only on this machine and are not in git. The daily report backs them up
after every run into a dated zip with a SHA-256 manifest; every zip is
read back and verified after writing. The newest BACKUP_KEEP daily
backups are kept (default 30).

Backups go to data/backups, or to BACKUP_DIR from .env: point it at a
synced folder (e.g. OneDrive) so a disk failure does not take the
backups with it.
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
    args = parser.parse_args(argv)

    try:
        if args.list:
            backups = list_backups()
            for p in backups:
                print(f"{p.name}  {len(verify(p))} dosya")
            print(f"{len(backups)} yedek, klasör: {backup_dir()}")
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
    "create_backup",
    "list_backups",
    "restore_backup",
    "verify",
]
