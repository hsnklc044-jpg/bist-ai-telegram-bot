"""
QuantBIST
Measurement provenance (DECISIONS K-76; user's request 04.11.2026 after the 41 -> 36 K-64 gap).

Every measurement says which data and which code it ran on, so that two runs can be compared:
- `describe(frames)`: stocks, candles, first and last stamp and a SHA-256 of the data itself
  (ticker, stamp and OHLCV values; independent of the file format and of dict order);
- `code_version()`: core.__version__, the git commit of the checkout `core` was imported from
  (and whether it had uncommitted changes) and that folder's path;
- `freeze(frames, folder, before)` writes one snapshot (data before `before` only, so the holdout
  stays out) as snapshot.csv.gz + manifest.json; `thaw(folder)` reads it back and refuses it when
  the data no longer matches the manifest's hash;
- `compare(a, b)`: stock by stock, what differs between two downloads.

Nothing here changes a rule, a threshold or a decision.

    python -m core.analytics.provenance freeze-hourly FOLDER    # download BIST 30 hourly, freeze < holdout
    python -m core.analytics.provenance daily                   # what the daily price store holds < holdout
    python -m core.analytics.provenance freeze-daily FOLDER     # freeze that store < holdout
    python -m core.analytics.provenance show FOLDER
    python -m core.analytics.provenance compare FOLDER_A FOLDER_B
    python -m core.analytics.provenance pc                      # the whole check on this PC (scripts/olcum.ps1)
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ("open", "high", "low", "close", "volume")
SNAPSHOT = "snapshot.csv.gz"
MANIFEST = "manifest.json"
FORMAT = 1


def _stamps(index) -> np.ndarray:
    idx = pd.DatetimeIndex(index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    return idx.as_unit("ns").asi8


def _frame_digest(df: pd.DataFrame) -> str:
    h = hashlib.sha256()
    h.update(_stamps(df.index).astype("<i8").tobytes())
    for col in COLUMNS:
        values = df[col].to_numpy(dtype="<f8") if col in df.columns else np.full(len(df), np.nan, dtype="<f8")
        h.update(col.encode())
        h.update(np.ascontiguousarray(values).tobytes())
    return h.hexdigest()


def digest(frames: dict[str, pd.DataFrame]) -> str:
    """SHA-256 of the data: the same candles give the same hash whatever order or file they came in."""

    h = hashlib.sha256()
    for ticker in sorted(frames):
        h.update(ticker.encode() + b"\0" + _frame_digest(frames[ticker]).encode())
    return h.hexdigest()


def _cut(frames: dict[str, pd.DataFrame], before) -> dict[str, pd.DataFrame]:
    if before is None:
        return {t: df for t, df in frames.items() if df is not None and len(df)}
    out = {}
    for t, df in frames.items():
        if df is None or not len(df):
            continue
        edge = pd.Timestamp(before)
        if df.index.tz is not None and edge.tz is None:
            edge = edge.tz_localize(df.index.tz)
        part = df[df.index < edge]
        if len(part):
            out[t] = part
    return out


@dataclass
class Data:
    stocks: int
    candles: int
    first: str
    last: str
    sha256: str
    before: str = ""
    per_stock: dict[str, dict] = field(default_factory=dict)

    def line(self) -> str:
        cut = f" ({self.before} öncesi)" if self.before else ""
        return (f"Veri: {self.stocks} hisse, {_thousands(self.candles)} mum, {self.first} – {self.last}{cut}; "
                f"sha256 {self.sha256}")


def _thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _fmt(ts) -> str:
    return pd.Timestamp(ts).strftime("%d.%m.%Y %H:%M")


def describe(frames: dict[str, pd.DataFrame], before=None) -> Data:
    """What the measurement sees: `frames` cut before `before` exactly as the studies cut them."""

    seen = _cut(frames, before)
    per = {t: {"candles": len(df), "first": _fmt(df.index[0]), "last": _fmt(df.index[-1]),
               "sha256": _frame_digest(df)} for t, df in sorted(seen.items())}
    if not seen:
        return Data(0, 0, "—", "—", digest({}), _fmt(before)[:10] if before is not None else "", per)
    return Data(len(seen), sum(len(df) for df in seen.values()),
                _fmt(min(df.index[0] for df in seen.values())), _fmt(max(df.index[-1] for df in seen.values())),
                digest(seen), _fmt(before)[:10] if before is not None else "", per)


@dataclass
class Code:
    version: str
    commit: str
    clean: bool | None
    path: str

    def line(self) -> str:
        state = {True: "temiz", False: "kaydedilmemiş değişiklik var", None: "durum bilinmiyor"}[self.clean]
        return f"Kod: v{self.version}, commit {self.commit} ({state}); core: {self.path}"


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10,
                             encoding="utf-8", check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def code_version() -> Code:
    """The code that is actually running: read from the folder `core` was imported from, not from CWD."""

    import core

    folder = Path(core.__file__).resolve().parent
    root = folder.parent
    commit = _git(root, "rev-parse", "HEAD")
    status = _git(root, "status", "--porcelain", "--untracked-files=no") if commit else None
    return Code(core.__version__, commit or "bilinmiyor", None if status is None else status == "", str(folder))


def stamp(frames: dict[str, pd.DataFrame], before=None) -> str:
    """The two lines every measurement prints first."""

    return describe(frames, before).line() + "\n" + code_version().line()


def report_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- snapshot -------------------------------------------------------------------------------------


def freeze(frames: dict[str, pd.DataFrame], folder: Path, before=None, source: str = "") -> Data:
    """Write the data before `before` as a snapshot; read it back and check the hash before returning."""

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    seen = _cut(frames, before)
    tz = next((str(df.index.tz) for df in seen.values() if df.index.tz is not None), "")
    rows = []
    for t, df in sorted(seen.items()):
        part = pd.DataFrame({c: df[c].astype(float) if c in df.columns else np.nan for c in COLUMNS})
        part.insert(0, "time", pd.DatetimeIndex(df.index).as_unit("ns").strftime("%Y-%m-%dT%H:%M:%S%z")
                    if tz else pd.DatetimeIndex(df.index).as_unit("ns").strftime("%Y-%m-%dT%H:%M:%S"))
        part.insert(0, "ticker", t)
        rows.append(part.reset_index(drop=True))
    table = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["ticker", "time", *COLUMNS])
    path = folder / SNAPSHOT
    table.to_csv(path, index=False, float_format="%.17g", lineterminator="\n",
                 compression={"method": "gzip", "mtime": 0})
    data = describe(seen, before)
    manifest = {"format": FORMAT, "data": asdict(data), "tz": tz, "source": source,
                "code": asdict(code_version()), "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (folder / MANIFEST).write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    thaw(folder)  # round trip: refuse to leave a snapshot that does not read back as the same data
    return data


class SnapshotError(ValueError):
    pass


def thaw(folder: Path) -> dict[str, pd.DataFrame]:
    """The frozen frames; SnapshotError when the file or the data does not match the manifest."""

    folder = Path(folder)
    manifest = json.loads((folder / MANIFEST).read_text(encoding="utf-8"))
    path = folder / SNAPSHOT
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["file_sha256"]:
        raise SnapshotError(f"{path.name}: dosya özeti manifest ile uyuşmuyor")
    table = pd.read_csv(path, dtype={"ticker": str, "time": str}, compression="gzip")
    tz = manifest.get("tz") or None
    frames = {}
    for t, part in table.groupby("ticker", sort=True):
        if tz:
            index = pd.to_datetime(part["time"], format="%Y-%m-%dT%H:%M:%S%z", utc=True).dt.tz_convert(tz)
        else:
            index = pd.to_datetime(part["time"], format="%Y-%m-%dT%H:%M:%S")
        frames[str(t)] = pd.DataFrame(part[list(COLUMNS)].to_numpy(dtype=float), columns=list(COLUMNS),
                                      index=pd.DatetimeIndex(index).as_unit("ns"))
    if digest(frames) != manifest["data"]["sha256"]:
        raise SnapshotError("anlık görüntünün veri özeti manifest ile uyuşmuyor")
    return frames


def manifest(folder: Path) -> dict:
    return json.loads((Path(folder) / MANIFEST).read_text(encoding="utf-8"))


# --- comparison -----------------------------------------------------------------------------------


def compare(a: dict[str, pd.DataFrame], b: dict[str, pd.DataFrame], before=None) -> pd.DataFrame:
    """One row per stock that differs: candles in each, stamps only in one, common stamps whose values differ."""

    a, b = _cut(a, before), _cut(b, before)
    rows = []
    for t in sorted(set(a) | set(b)):
        x, y = a.get(t), b.get(t)
        if x is not None and y is not None and _frame_digest(x) == _frame_digest(y):
            continue
        xi = x.index if x is not None else pd.DatetimeIndex([])
        yi = y.index if y is not None else pd.DatetimeIndex([])
        common = xi.intersection(yi)
        changed = 0
        if len(common):
            cols = [c for c in COLUMNS if x is not None and y is not None and c in x.columns and c in y.columns]
            xv = x.loc[common, cols].to_numpy(dtype=float)
            yv = y.loc[common, cols].to_numpy(dtype=float)
            changed = int((~np.isclose(xv, yv, rtol=0, atol=0, equal_nan=True)).any(axis=1).sum())
        rows.append({"hisse": t, "mum_a": len(xi), "mum_b": len(yi), "yalniz_a": len(xi.difference(yi)),
                     "yalniz_b": len(yi.difference(xi)), "degisen": changed,
                     "ilk_a": _fmt(xi[0]) if len(xi) else "—", "ilk_b": _fmt(yi[0]) if len(yi) else "—",
                     "son_a": _fmt(xi[-1]) if len(xi) else "—", "son_b": _fmt(yi[-1]) if len(yi) else "—"})
    return pd.DataFrame(rows, columns=["hisse", "mum_a", "mum_b", "yalniz_a", "yalniz_b", "degisen", "ilk_a",
                                       "ilk_b", "son_a", "son_b"])


def compare_text(a, b, before=None) -> str:
    da, db = describe(a, before), describe(b, before)
    lines = ["A " + da.line(), "B " + db.line()]
    if da.sha256 == db.sha256:
        lines.append("Sonuç: iki veri birebir aynı.")
        return "\n".join(lines)
    diff = compare(a, b, before)
    lines.append(f"Sonuç: {len(diff)} hissede fark var (A {da.candles} mum, B {db.candles} mum).")
    lines.append(diff.to_string(index=False))
    return "\n".join(lines)


# --- command line ---------------------------------------------------------------------------------


def holdout_edge():
    from core.backtest.run import HOLDOUT_START

    return HOLDOUT_START.tz_localize("Europe/Istanbul")


def load_frozen_or_download(folder: str | None) -> tuple[dict[str, pd.DataFrame], str]:
    """(hourly frames, where they came from): the frozen snapshot when a folder is given, else Yahoo now."""

    if folder:
        return thaw(Path(folder)), f"dondurulmuş görüntü {folder}"
    from core.market.hourly import load_hourly

    return load_hourly().frames, "Yahoo, şimdi indirildi"


def daily_frames() -> dict[str, pd.DataFrame]:
    """Every stock in the daily price store, as stored (the studies apply corporate actions on top)."""

    from core.market import store

    return {s: store.read(s) for s in store.symbols()}


# --- the check on the user's PC (04.11.2026: routine work runs here, not in a chat session) -------------


def _run_study(args: list[str]) -> str:
    out = subprocess.run([sys.executable, "-m", *args], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=3600, check=False)
    return out.stdout


def pc_check(root: Path | None = None, now=None, load=None, run=_run_study, report: Path | None = None) -> int:
    """Freeze the hourly data (and the local daily store) into the backup folder, run K-63 and K-64 twice
    on the frozen hourly data in separate processes, and write one short report to paste into the chat.
    0 = both runs identical; 1 = they differ or something failed. Nothing is tuned or decided here."""

    from datetime import datetime

    from core.backup import backup_dir
    from core.config.paths import LOG_DIR
    from core.market.hourly import load_hourly

    now = now or datetime.now()
    root = Path(root or backup_dir() / "olcum")
    hourly_dir = root / f"saatlik_{now:%Y%m%d_%H%M}"
    lines = [f"QuantBIST ölçüm kontrolü {now:%d.%m.%Y %H:%M}", code_version().line()]
    ok = True
    got = (load or load_hourly)()
    lines.append(got.summary())
    if not got.frames:
        lines.append("SONUÇ: saatlik veri gelmedi; kontrol yapılamadı.")
        ok = False
    else:
        data = freeze(got.frames, hourly_dir, holdout_edge(), source=f"Yahoo 1h, bu PC, {now:%d.%m.%Y %H:%M}")
        lines += [f"Saatlik görüntü: {hourly_dir}", "  " + data.line()]
        for name, args in (("K-63", ["core.analytics.dip_study", "--veri", str(hourly_dir)]),
                           ("K-64 saatlik", ["core.ml.signal_filter", "--zaman", "saatlik", "--veri", str(hourly_dir)])):
            first, second = run(args), run(args)
            digest_line = next((x for x in first.splitlines() if x.startswith("Rapor sha256 ")), "")
            same = bool(digest_line) and first == second
            ok = ok and same
            verdict = next((x for x in first.splitlines() if "GEÇ" in x), "rapor yok")
            lines.append(f"{name}: iki çalıştırma {'AYNI' if same else 'FARKLI ya da eksik'}; {verdict}")
            if digest_line:
                lines.append(f"  {digest_line}")
    try:
        daily = daily_frames()
    except Exception as exc:  # noqa: BLE001 - no local store is reported, not fatal
        daily, why = {}, f"{type(exc).__name__}: {exc}"
    else:
        why = "fiyat deposu boş"
    if daily:
        from core.backtest.run import HOLDOUT_START

        d = freeze(daily, root / f"gunluk_{now:%Y%m%d_%H%M}", HOLDOUT_START, source="bu PC'nin market.db'si")
        lines += [f"Günlük görüntü: {root / f'gunluk_{now:%Y%m%d_%H%M}'}", "  " + d.line()]
    else:
        lines.append(f"Günlük görüntü yok ({why}).")
    lines.append("SONUÇ: " + ("tekrarlanabilir" if ok else "SORUN VAR, raporu sohbete yapıştırın"))
    lines.append("Not: tekrarlanabilirlik kontrolüdür, karar ölçümü değildir; kural ve eşik değişmez.")
    report = Path(report or LOG_DIR / "olcum_report.txt")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    argv = list(sys.argv[1:] if argv is None else argv)
    action = argv[0] if argv else ""
    if action == "pc":
        return pc_check()
    if action == "daily":
        from core.backtest.run import HOLDOUT_START

        print("Günlük fiyat deposu " + stamp(daily_frames(), HOLDOUT_START))
        return 0
    if len(argv) < 2 or action not in ("freeze-hourly", "freeze-daily", "show", "compare"):
        print(__doc__)
        return 2
    if action == "freeze-daily":
        from core.backtest.run import HOLDOUT_START

        data = freeze(daily_frames(), Path(argv[1]), HOLDOUT_START, source="yerel fiyat deposu (market.db)"
                      + (f" ({os.environ['GITHUB_RUN_ID']})" if os.environ.get("GITHUB_RUN_ID") else ""))
        print("Donduruldu: " + data.line())
        print(code_version().line())
        return 0
    if action == "freeze-hourly":
        from core.market.hourly import load_hourly

        got = load_hourly()
        print(got.summary())
        data = freeze(got.frames, Path(argv[1]), holdout_edge(),
                      source=f"Yahoo 1h, period=1y, indirildi {got.fetched_at:%d.%m.%Y %H:%M:%S}"
                             + (f" ({os.environ['GITHUB_RUN_ID']})" if os.environ.get("GITHUB_RUN_ID") else ""))
        print("Donduruldu: " + data.line())
        print(code_version().line())
        for t, row in data.per_stock.items():
            print(f"  {t}: {row['candles']} mum, {row['first']} – {row['last']}, sha256 {row['sha256'][:16]}")
        return 0
    if action == "show":
        m = manifest(Path(argv[1]))
        thaw(Path(argv[1]))
        print(Data(**m["data"]).line())
        print("Kaynak: " + (m.get("source") or "—"))
        print("Donduran " + Code(**m["code"]).line())
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 2
    print(compare_text(thaw(Path(argv[1])), thaw(Path(argv[2]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Code", "Data", "SnapshotError", "code_version", "compare", "compare_text", "describe", "digest",
           "freeze", "load_frozen_or_download", "manifest", "report_digest", "stamp", "thaw"]
