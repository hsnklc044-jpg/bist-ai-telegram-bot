"""QuantBIST – the live /tara ai model check (K-79, user's request 05.11.2026, A1.3 and A1.4).

    .venv\\Scripts\\python scripts\\kart_modeli_kontrol.py

Read-only for the model and the paper book. It prints:
- the saved model's training day and row count (logs/signal_model.joblib);
- whether the installed fit_live is the frozen one (tests/test_k64_freeze.py hash);
- the rows the frozen rule gives on this PC's data for that day, and the newest label end among
  them, which must be before HOLDOUT_START;
- every /tara ai card written from 03.11.2026 (the model trained under the old rule) until the
  saved model's day if that model is newer. Those cards are listed in
  logs/kart_holdout_isareti.csv (append-only, "holdout etkisi olabilir"); signals.db is not changed.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OLD_RULE_MODEL = date(2026, 11, 3)  # trained by the old fit_live (PC output, 05.11.2026)
MARK_FILE = ROOT / "logs" / "kart_holdout_isareti.csv"


def frozen_fit_live() -> bool:
    sys.path.insert(0, str(ROOT / "tests"))
    from test_k64_freeze import FROZEN, parts

    return parts("core/ml/signal_filter.py", ("fit_live",)).get("fit_live") == FROZEN["core/ml/signal_filter.py:fit_live"]


def expected_rows(today: date) -> tuple[int, object]:
    import pandas as pd

    from core.backtest.run import HOLDOUT_START
    from core.ml import signal_filter as S

    frames, members = S._daily()
    x, y = S.SPEC["gunluk"]
    edge = min(pd.Timestamp(today), HOLDOUT_START)
    rows = S.events(frames, x, y, members, before=edge)
    rows = rows[rows["label_end"] < edge]
    return len(rows), (rows["label_end"].max() if len(rows) else None)


def cards_between(first: date, last: date) -> list:
    from core.signals import store

    conn = store.connect()
    try:
        return [s for s in store.signals(conn) if first <= s.created <= last]
    finally:
        conn.close()


def mark(cards, now: datetime) -> int:
    if not cards:
        return 0
    known = set()
    if MARK_FILE.exists():
        with open(MARK_FILE, encoding="utf-8", newline="") as fh:
            known = {r["id"] for r in csv.DictReader(fh)}
    new = [c for c in cards if str(c.id) not in known]
    MARK_FILE.parent.mkdir(parents=True, exist_ok=True)
    first = not MARK_FILE.exists()
    with open(MARK_FILE, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if first:
            w.writerow(["at", "id", "created", "symbol", "status", "note"])
        for c in new:
            w.writerow([now.isoformat(timespec="seconds"), c.id, c.created, c.symbol, c.status,
                        "holdout etkisi olabilir (03.11 modeli eski fit_live kuralıyla; en fazla bir gün, sayı bilinmiyor)"])
    return len(new)


def main() -> int:
    import core
    from core.backtest.run import HOLDOUT_START
    from core.infrastructure.console import utf8_output
    from core.ml import signal_filter as S

    utf8_output()
    print(f"Kurulu sürüm: v{core.__version__}")
    saved = S.load_live()
    if saved is None:
        print("Model kaydı yok ya da okunamadı.")
        return 1
    trained = date.fromisoformat(str(saved.get("trained")))
    print(f"Kayıtlı model: eğitildiği gün {trained:%d.%m.%Y}, satır {saved.get('rows')}")
    ok_code = frozen_fit_live()
    print(f"Kurulu fit_live dondurulmuş kodla aynı: {'EVET' if ok_code else 'HAYIR'}")
    rows, last_end = expected_rows(trained)
    print(f"Dondurulmuş kurala göre o gün beklenen satır: {rows}; en son etiket bitişi: {last_end}")
    before = last_end is None or last_end < HOLDOUT_START
    print(f"En son etiket HOLDOUT_START ({HOLDOUT_START:%d.%m.%Y}) öncesinde: {'EVET' if before else 'HAYIR'}")
    new_rule = trained > OLD_RULE_MODEL
    if not new_rule:
        print("Model hâlâ 03.11 modeli: yeni kuralla eğitim henüz olmadı.")
    same = saved.get("rows") == rows
    print(f"Kayıtlı satır sayısı beklenenle aynı: {'EVET' if same else 'HAYIR'}")
    cards = cards_between(OLD_RULE_MODEL, trained if new_rule else date.today())
    added = mark(cards, datetime.now())
    print(f"03.11'den bu yana /tara ai kartı: {len(cards)}; işaret dosyasına yeni eklenen: {added}")
    verdict = new_rule and ok_code and before and same
    print("SONUÇ: " + ("DOĞRULANDI" if verdict else "DOĞRULANAMADI – çıktıyı sohbete gönderin"))
    return 0 if verdict else 1


if __name__ == "__main__":
    raise SystemExit(main())
