"""
QuantBIST
K-70 progress, computed (v0.99.48): "yüzde kaç olduk" without asking anyone.

Two numbers, never mixed:
- observation: session days with a report sent since the new setup (OBSERVE_FROM) out of the 20
  the completion rule asks for;
- proof: the completion criteria met now (every SLO on target, 14/14 models validated, a measured
  data accuracy, at least 20 observed sessions). Until all hold the system is not "tam güvenilir".
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

OBSERVE_FROM = date(2026, 11, 3)  # the new folder's first report (AUDIT EVRE 1)
OBSERVE_TARGET = 20  # sessions (K-70)


@dataclass
class Progress:
    observed: int
    slo_met: int
    slo_total: int
    validated: int
    high_risk: int
    missing: list[str] = field(default_factory=list)

    @property
    def reliable(self) -> bool:
        return not self.missing


def observed_sessions(runs_path: Path, since: date = OBSERVE_FROM) -> int:
    """Distinct data days sent since `since` (a re-run of the same day counts once)."""

    try:
        with open(runs_path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return 0
    days = set()
    for r in rows:
        try:
            day = date.fromisoformat((r.get("data_day") or "").strip())
        except ValueError:
            continue
        if r.get("status") == "sent" and day >= since:
            days.add(day)
    return len(days)


def measure(now: datetime, results: list, runs_path: Path | None = None, folder: Path | None = None) -> Progress:
    from core.reports import validation
    from core.reports.health import OK
    from core.reports.runs import RUNS_FILE

    observed = observed_sessions(Path(runs_path or RUNS_FILE))
    found = validation.reports(folder)
    done = sum(m in found for m in validation.HIGH_RISK)
    met = sum(r.state == OK for r in results)
    p = Progress(observed, met, len(results), done, len(validation.HIGH_RISK))
    if observed < OBSERVE_TARGET:
        p.missing.append(f"gözlem {observed}/{OBSERVE_TARGET} seans")
    if met < len(results):
        p.missing.append(f"SLO {met}/{len(results)} hedefte")
    if done < len(validation.HIGH_RISK):
        p.missing.append(f"model doğrulama {done}/{len(validation.HIGH_RISK)}")
    accuracy = next((r for r in results if r.name == "Veri doğruluğu"), None)
    if accuracy is None or accuracy.value is None:
        p.missing.append("veri doğruluğu ölçülmedi")
    return p


def lines(p: Progress) -> list[str]:
    head = (f"🎯 Güvenilirlik (K-70): gözlem {p.observed}/{OBSERVE_TARGET} seans · SLO {p.slo_met}/{p.slo_total} · "
            f"model doğrulama {p.validated}/{p.high_risk}")
    verdict = ("tam güvenilir: evet" if p.reliable else
               "tam güvenilir: hayır (eksik: " + "; ".join(p.missing) + ")")
    return [head, f"  {verdict}"]


__all__ = ["OBSERVE_FROM", "OBSERVE_TARGET", "Progress", "lines", "measure", "observed_sessions"]
