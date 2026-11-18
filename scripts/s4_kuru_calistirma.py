"""S4 dry run on FAKE data (18.11.2026, the user's day order item 4).

Runs the live first-decision path end to end, without the live signal log and without touching logs/:
`s4_decision.check` -> decision JSON, RESEARCH_LOG draft, drift reasons (`core.reports.drift.reasons`) and the
S5 notice; then a second evening to show that nothing is written twice. All numbers are synthetic (seeded); the
output is an example of the format, not a measurement. No threshold is set or changed here (K-93 (1), (4)).

    python scripts/s4_kuru_calistirma.py [OUT_MD]     (default docs/S4_KURU_CALISTIRMA.md)
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.reports import drift, s4_decision  # noqa: E402
from core.reports.forward import VIEW_ORDER  # noqa: E402

SEED = 20261118
DAYS = 46  # the earliest mature length at the 5-session horizon (10 independent periods)
SYMBOLS = ("AAA.IS", "BBB.IS", "CCC.IS", "DDD.IS")
STRONG = VIEW_ORDER[0]  # the one fake view with a clear excess, so the drift and S5 paths run too


def fake_inputs():
    rng = np.random.default_rng(SEED)
    days = [d.date() for d in pd.bdate_range("2026-11-02", periods=DAYS)]
    rows = []
    for v in VIEW_ORDER:
        mean = 0.015 if v == STRONG else 0.0
        for d in days:
            for s in SYMBOLS:
                rows.append({"source": "daily", "view": v, "day": d, "horizon": 5, "symbol": s,
                             "excess": float(rng.normal(mean, 0.01))})
    scored = pd.DataFrame(rows)
    reference = {(v, 5): {"mean": 0.0, "period_start": "2025-01-02", "period_end": "2025-12-31"} for v in VIEW_ORDER}
    index = pd.bdate_range("2025-01-01", "2027-02-26")
    bench = pd.Series(10000 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, len(index)))), index=index)
    actions = [SimpleNamespace(symbol="BBB.IS", ex_date=days[10])]
    return scored, reference, bench, actions, days


def dry_run(work: Path) -> dict:
    scored, reference, bench, actions, days = fake_inputs()
    paths = {"decision": work / "s4_ilk_karar.json", "drafts": work / "research_log_taslak",
             "notice": work / "s5_bildirim.json"}
    day = date(2027, 1, 6)

    def reasons(rows, ref):
        return drift.reasons(rows, ref, bench, actions)

    first = s4_decision.check(day, scored, reference, reasons=reasons, **paths)
    second = s4_decision.check(date(2027, 1, 7), scored, reference, reasons=reasons, **paths)
    drafts = sorted(paths["drafts"].glob("*.md"))
    return {"messages": first, "second": second, "decision": json.loads(paths["decision"].read_text("utf-8")),
            "notice": json.loads(paths["notice"].read_text("utf-8")) if paths["notice"].exists() else None,
            "draft": drafts[0].read_text("utf-8") if drafts else "", "draft_files": [p.name for p in drafts],
            "first_day": days[0], "last_day": days[-1]}


def markdown(result: dict) -> str:
    fence = "```"
    msgs = "\n\n".join(result["messages"])
    return (
        "# S4 kuru çalıştırma (SAHTE VERİ, 18.11.2026)\n\n"
        "**Bu bir ölçüm değildir.** Bütün sayılar sabit tohumla üretilmiş sahte veridir "
        f"(`scripts/s4_kuru_calistirma.py`, tohum {SEED}). Amaç, 06.01.2027'de (en erken, K-93 (1)) çalışacak "
        "yolun uçtan uca çalıştığını ve çıktının biçimini göstermektir. Canlı `data/signal_log.csv` ve `logs/` "
        "kullanılmadı; eşik ya da ölçüt değişmedi.\n\n"
        "## Kurulum\n"
        f"- 5 görünüm × {len(SYMBOLS)} sahte hisse × {DAYS} seans ({result['first_day']:%d.%m.%Y} – "
        f"{result['last_day']:%d.%m.%Y}), 5 seans ufku. Bir görünüm ({STRONG}) bilerek +%1,5 ortalamayla üretildi "
        "ki sapma ve S5 bildirimi yolları da çalışsın; diğer dördünün ortalaması 0.\n"
        "- Geçmiş (backtest) referansı her görünüm için 0; sahte XU100 serisi; sahte bir kurumsal işlem (BBB).\n"
        "- Aynı yol: `s4_decision.check` → `first_decision` (değişmeyen `forward._verdict`) → "
        "`research_log_draft` → `drift.reasons` → S5 bildirimi.\n\n"
        "## Sonuç\n"
        f"- 1. akşam (06.01.2027) gönderilecek mesaj sayısı: {len(result['messages'])} "
        "(ilk karar + S5 bildirimi).\n"
        f"- 2. akşam (07.01.2027): {len(result['second'])} mesaj. Karar, taslak ve bildirim bir kez yazıldı.\n"
        f"- Taslak dosyası: `logs/research_log_taslak/{result['draft_files'][0]}` (bu çalışmada geçici klasörde).\n\n"
        f"## Telegram mesajları (örnek)\n{fence}text\n{msgs}\n{fence}\n\n"
        f"## RESEARCH_LOG taslağı (örnek)\n{fence}markdown\n{result['draft'].rstrip()}\n{fence}\n\n"
        "## Kuru çalıştırmanın bulduğu (düzeltilmedi; bot çıktısını değiştirir, ayrı dal)\n"
        "- Aynı taslakta iki sayı biçimi var: `s4_decision._p` \"%+1.49\" (nokta, işaret % işaretinden sonra) "
        "yazıyor, `drift.reasons` ise \"+%1,4\" (virgül, Türkçe biçim). Düzeltme önerisi: `_p` yerine "
        "`core.reports.daily.pct` kullanmak. Kararın kendisini etkilemez, yalnız metni etkiler.\n"
        "- Kayıt günleri ISO biçiminde (\"2026-11-02 – 2027-01-04\"); belgenin geri kalanı GG.AA.YYYY.\n"
    )


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = Path(argv[0]) if argv else ROOT / "docs" / "S4_KURU_CALISTIRMA.md"
    with tempfile.TemporaryDirectory() as tmp:
        result = dry_run(Path(tmp))
    out.write_text(markdown(result), encoding="utf-8", newline="\n")
    print(f"yazıldı: {out} ({len(result['messages'])} mesaj, 2. akşam {len(result['second'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
