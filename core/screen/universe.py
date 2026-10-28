"""
QuantBIST
Which stocks a /tara query scans: evren=bist100 (data/universe.csv, the current list),
evren=bist30 (data/bist30.csv, once added with its source; DECISIONS K-33) or evren=izleme
(the user's watchlist). Also the stocks whose prices wait for a correction: the second source
differs (research-results crosscheck/latest.json), read at most once an hour.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

from core.config.paths import DATA_DIR
from core.screen.language import ScreenError

BIST30_FILE = DATA_DIR / "bist30.csv"
SUSPECTS_TTL = 3600
_suspects: dict = {}

LABELS = {"bist100": "BIST 100", "bist30": "BIST 30", "izleme": "izleme listesi"}


def symbols(universe: str, chat_id=None, bist30_path: Path | None = None) -> list[str]:
    if universe == "bist100":
        from core.market.universe import load_universe

        return load_universe()
    if universe == "bist30":
        path = Path(bist30_path or BIST30_FILE)
        if not path.exists():
            raise ScreenError("BIST 30 listesi henüz sistemde yok (kaynağıyla eklenecek). Şimdilik evren=bist100 "
                              "ya da evren=izleme kullanın.")
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return [f"{r['symbol'].strip().upper().removesuffix('.IS')}.IS" for r in csv.DictReader(fh)
                    if r.get("symbol", "").strip()]
    from core.watchlist.service import get_watchlist

    found = get_watchlist(chat_id) if chat_id is not None else get_watchlist()
    if not found:
        raise ScreenError("İzleme listen boş. /watchadd THYAO ile hisse ekle ya da evren=bist100 kullan.")
    return [f"{s.strip().upper().removesuffix('.IS')}.IS" for s in found]


def suspects(fetch=None, now: float | None = None) -> set[str]:
    """Codes whose closes differ from the second source (empty when the summary cannot be read)."""

    now = time.time() if now is None else now
    if _suspects and now - _suspects["at"] < SUSPECTS_TTL:
        return _suspects["codes"]
    from core.reports import slo

    data = (fetch or slo.fetch_accuracy)()
    codes = set(data.get("differing", [])) if isinstance(data, dict) else set()
    _suspects.update(at=now, codes=codes)
    return codes


__all__ = ["BIST30_FILE", "LABELS", "suspects", "symbols"]
