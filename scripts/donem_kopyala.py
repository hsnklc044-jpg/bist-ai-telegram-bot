"""Copy the Saturday SLO tables into docs/PERIODS/ (K-17 correction, 18.11.2026).

The bot writes logs/haftalik_slo/YYYY-MM-DD.txt in the live checkout (otonom.save_weekly) and never writes docs/.
The robot runs this from a worktree on a branch; it reads the live logs (read only) and adds one Markdown file per
week that is not there yet. Existing period files are never overwritten.

    python scripts/donem_kopyala.py [SRC_DIR] [DST_DIR]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LIVE_SRC = Path(r"C:\Projeler\QuantBIST-yeni\logs\haftalik_slo")
DST = Path(__file__).resolve().parents[1] / "docs" / "PERIODS"
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.txt$")


def copy_periods(src: Path, dst: Path) -> list[str]:
    if not src.is_dir():
        return []
    created = []
    for f in sorted(src.iterdir()):
        m = NAME.match(f.name)
        if not m:
            continue
        out = dst / f"{m.group(1)}.md"
        if out.exists():
            continue
        body = f.read_text(encoding="utf-8").rstrip("\n")
        dst.mkdir(parents=True, exist_ok=True)
        out.write_text(f"# Dönem {m.group(1)}\n\nKaynak: canlı `logs/haftalik_slo/{f.name}` (cumartesi 21:00 özeti, "
                       f"K-17). Robot dal üzerinden kopyaladı; elle değiştirilmez.\n\n```text\n{body}\n```\n",
                       encoding="utf-8", newline="\n")
        created.append(out.name)
    return created


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [Path(a) for a in sys.argv[1:3]]
    made = copy_periods(args[0] if args else LIVE_SRC, args[1] if len(args) > 1 else DST)
    print("eklendi: " + (", ".join(made) if made else "yok"))
