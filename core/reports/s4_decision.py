"""
QuantBIST
S4 live first decision and the S5 notice (DECISIONS K-93, pre-registered 18.11.2026).

    (1) The first evening on which all five technical views of the daily report (source "daily") are
        mature at the 5-session horizon, each view gets the unchanged `forward._verdict`. The decision
        is written once to logs/s4_ilk_karar.json and never rewritten.
    (2) The same evening a RESEARCH_LOG draft (template below) goes to logs/research_log_taslak/;
        the bot never writes into docs/, the robot copies it on a branch.
    (4) S5 threshold: a mature view whose 99% interval (Bonferroni, 5 views) of the mean excess after
        the round-trip cost is above 0. The bot then writes one Telegram notice with the evidence
        and opens nothing: no setting, book or level changes.

No new threshold for (1): MIN_DAYS, MIN_PERIODS and the 95% interval are the forward module's own.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd

from core.config.paths import LOG_DIR
from core.config.trading import COMMISSION, SLIPPAGE
from core.reports.forward import SYSTEMATIC, T95, VIEW_ORDER, _drift, _verdict, summarize

PRIMARY_HORIZON = 5
ROUND_TRIP_COST = 2 * (COMMISSION + SLIPPAGE)  # 0.30%
# two-sided 99% Student t by degrees of freedom 1..30; above 30, 2.576
T99 = (63.657, 9.925, 5.841, 4.604, 4.032, 3.707, 3.499, 3.355, 3.250, 3.169, 3.106, 3.055, 3.012, 2.977,
       2.947, 2.921, 2.898, 2.878, 2.861, 2.845, 2.831, 2.819, 2.807, 2.797, 2.787, 2.779, 2.771, 2.763,
       2.756, 2.750)
DECISION_FILE = LOG_DIR / "s4_ilk_karar.json"
DRAFT_DIR = LOG_DIR / "research_log_taslak"
NOTICE_FILE = LOG_DIR / "s5_bildirim.json"
RULE = "K-93 (1)"
TRIALS = 14  # 9 earlier rules (RESEARCH_LOG) + 5 live views (K-93 (4))


def _t(table: tuple[float, ...], df: int, far: float) -> float:
    return table[df - 1] if 1 <= df <= len(table) else far


def _low99_after_cost(stats) -> float:
    """The 99% lower bound of the mean after cost, on the same independent days as the 95% interval."""

    k = stats.periods or 0
    if k < 2 or math.isnan(stats.high):
        return float("nan")
    se = (stats.high - stats.mean) / _t(T95, k - 1, 1.96)
    return stats.mean - ROUND_TRIP_COST - _t(T99, k - 1, 2.576) * se


def first_decision(scored: pd.DataFrame, reference: dict,
                   reasons: Callable[[pd.DataFrame, dict], list[str]] | None = None) -> dict | None:
    """The decision once all five views are mature at the primary horizon; None before."""

    if scored.empty:
        return None
    part = scored[(scored["source"] == SYSTEMATIC) & (scored["horizon"] == PRIMARY_HORIZON)]
    views = []
    for view in VIEW_ORDER:
        rows = part[part["view"] == view]
        stats = summarize(rows)
        if stats is None or not stats.mature:
            return None
        ref = reference.get((view, PRIMARY_HORIZON))
        drift = _drift(stats, ref).replace(" → ", "", 1)
        views.append({
            "view": view, "verdict": _verdict(stats), "mean": stats.mean, "low": stats.low, "high": stats.high,
            "days": stats.days, "periods": stats.periods, "records": stats.records, "hit_rate": stats.hit_rate,
            "low99_after_cost": _low99_after_cost(stats), "reference": ref["mean"] if ref else None,
            "drift": drift, "reasons": (reasons(rows, ref) if reasons and ref and "sapma" in drift else []),
        })
    return {"rule": RULE, "horizon": PRIMARY_HORIZON, "views": views,
            "first_day": str(part["day"].min()), "last_day": str(part["day"].max())}


def s5_passing(decision: dict | None) -> list[dict]:
    return [v for v in (decision or {}).get("views", []) if v["low99_after_cost"] > 0]


def _p(x) -> str:
    """The report's own format ("+%1,49"), as in the drift reasons of the same draft (dry run 18.11)."""

    from core.reports.daily import pct

    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else pct(x, 2)


TEMPLATE = """## {date} – Canlı ölçüm ilk kararı (K-93)

- **Soru:** Günlük raporun 5 teknik görünümü, kayıttan sonraki 5 seansta XU100'den farklı mı?
- **Veri:** `data/signal_log.csv` kaynak `daily`, kayıt günleri {first_day} – {last_day}; giriş ertesi açılış, \
çıkış 5. seans kapanışı, XU100 aynı seanslar (`core.reports.forward`). İleri veri; holdout'a dokunulmadı.
- **Ölçüt (K-93 (1), değişmedi):** `forward._verdict`: en az {min_days} gün ve {min_periods} bağımsız dönem; \
%95 aralık 0'ın üstünde "geçiyor", altında "gerisinde", içeriyorsa "farkı anlamlı değil". Maliyet öncesi.
- **Sonuç:**
{results}
- **Backtest–canlı sapması (K-30):**
{drift}
- **S5 eşiği (K-93 (4), maliyet %0,30 sonrası %99 alt uç > 0):** {s5}
- **Deneme sayısı:** {trials} (9 önceki kural + 5 canlı görünüm). Sonuca göre ölçüt, ufuk ya da görünüm değiştirilmez.
- **Kaynak:** bot taslağı `logs/research_log_taslak/{file}`; RESEARCH_LOG'a değiştirilmeden taşınır.
"""


def research_log_draft(day: date, decision: dict) -> str:
    from core.reports.forward import MIN_DAYS, MIN_PERIODS

    results = "\n".join(
        f"  - {v['view']}: {_p(v['mean'])} [{_p(v['low'])}, {_p(v['high'])}], {v['days']} gün, "
        f"{v['periods']} bağımsız dönem, isabet %{v['hit_rate'] * 100:.0f} → {v['verdict']}"
        for v in decision["views"])
    drift = "\n".join(
        f"  - {v['view']}: geçmiş {_p(v['reference'])} → {v['drift'] or 'referans yok'}"
        + "".join(f"\n    - neden? {r}" for r in v["reasons"])
        for v in decision["views"])
    passing = s5_passing(decision)
    s5 = ", ".join(f"{v['view']} ({_p(v['low99_after_cost'])})" for v in passing) or "geçen görünüm yok"
    def dmy(text: str) -> str:
        return f"{date.fromisoformat(str(text)[:10]):%d.%m.%Y}"

    return TEMPLATE.format(date=f"{day:%d.%m.%Y}", first_day=dmy(decision["first_day"]),
                           last_day=dmy(decision["last_day"]),
                           min_days=MIN_DAYS, min_periods=MIN_PERIODS, results=results, drift=drift, s5=s5,
                           trials=TRIALS, file=f"{day:%Y-%m-%d}_canli_ilk_karar.md")


def _decision_text(day: date, decision: dict) -> str:
    lines = [f"📏 S4 canlı ölçüm: ilk karar ({day:%d.%m.%Y}, K-93, 5 seans, maliyet öncesi)"]
    lines += [f"• {v['view']}: {_p(v['mean'])} [{_p(v['low'])}, {_p(v['high'])}] → {v['verdict']}"
              for v in decision["views"]]
    lines.append("Karar bir kez yazıldı (logs/s4_ilk_karar.json); RESEARCH_LOG taslağı hazır. "
                 "Ölçümdür, yatırım önerisi değildir.")
    return "\n".join(lines)


def _notice_text(day: date, passing: list[dict]) -> str:
    lines = [f"🔔 Kural anlamlı çıktı (K-93 (4), {day:%d.%m.%Y}): maliyet (%0,30 gidiş-dönüş) düşüldükten sonra "
             "%99 güven aralığının alt ucu 0'ın üstünde."]
    lines += [f"• {v['view']}: ortalama {_p(v['mean'])}, maliyet sonrası %99 alt uç {_p(v['low99_after_cost'])}, "
              f"{v['days']} gün, {v['periods']} bağımsız dönem" for v in passing]
    lines.append("Kanıt: logs/s4_ilk_karar.json ve logs/s5_bildirim.json. Bu yalnız bildirimdir: hiçbir şey açılmadı, "
                 "hiçbir ayar değişmedi. S5 kullanıcı kararıdır ve S4'ün tamamen kapanmasını gerektirir. "
                 "Yatırım önerisi değildir.")
    return "\n".join(lines)


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    tmp.replace(path)


def check(day: date, scored: pd.DataFrame, reference: dict, decision: Path = DECISION_FILE,
          drafts: Path = DRAFT_DIR, notice: Path = NOTICE_FILE,
          reasons: Callable[[pd.DataFrame, dict], list[str]] | None = None) -> list[str]:
    """Evening check: messages to send (the first decision once, the S5 notice once); [] otherwise."""

    current = first_decision(scored, reference, reasons)
    if current is None:
        return []
    messages = []
    if not decision.exists():
        _write(decision, {"date": day.isoformat(), **current})
        drafts.mkdir(parents=True, exist_ok=True)
        (drafts / f"{day:%Y-%m-%d}_canli_ilk_karar.md").write_text(research_log_draft(day, current),
                                                                   encoding="utf-8", newline="\n")
        messages.append(_decision_text(day, current))
    passing = s5_passing(current)
    if passing and not notice.exists():
        _write(notice, {"date": day.isoformat(), "rule": "K-93 (4)", "views": passing})
        messages.append(_notice_text(day, passing))
    return messages


def run(day: date) -> list[str]:
    """Live wiring: the signal log scored as /performans scores it, with the backtest reference."""

    from core.backtest.expectations import load as load_expectations
    from core.reports.forward import _drift_reasons, adjusted_bars, score_log

    scored = score_log(horizons=(PRIMARY_HORIZON,))
    return check(day, scored, load_expectations(),
                 reasons=lambda rows, ref: _drift_reasons(rows, ref, adjusted_bars))


__all__ = ["DECISION_FILE", "DRAFT_DIR", "NOTICE_FILE", "PRIMARY_HORIZON", "ROUND_TRIP_COST", "T99", "TEMPLATE",
           "check", "first_decision", "research_log_draft", "run", "s5_passing"]
