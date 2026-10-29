"""
QuantBIST
Model validation status (Talimat F §F5–F6, DECISIONS K-58). Each independent validation report is
docs/validation/<model>.md with a "Tarih: YYYY-MM-DD" and a "Karar: ..." line. High-risk models
are revalidated every year, medium-risk ones every two years (MAINTENANCE.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from core.config.paths import ROOT_DIR

VALIDATION_DIR = ROOT_DIR / "docs" / "validation"
# the high-risk models of docs/MODELS.md (a test keeps the two in step)
HIGH_RISK = ("M1", "M5", "M8", "M11", "M12", "M14", "M15", "M16", "M24", "M27", "M28")
VALID_FOR = timedelta(days=365)


@dataclass(frozen=True)
class Report:
    model: str
    day: date
    verdict: str


def reports(folder: Path | None = None) -> dict[str, Report]:
    folder = Path(folder or VALIDATION_DIR)
    out = {}
    for path in sorted(folder.glob("M*.md")) if folder.exists() else []:
        text = path.read_text(encoding="utf-8")
        day = re.search(r"^\**Tarih:?\**:?\s*(\d{4}-\d{2}-\d{2})", text, flags=re.M)
        verdict = re.search(r"^\**Karar:?\**:?\s*(.+)$", text, flags=re.M)
        if day and verdict:
            out[path.stem] = Report(path.stem, date.fromisoformat(day.group(1)), verdict.group(1).strip().rstrip("."))
    return out


def status(today: date, folder: Path | None = None) -> tuple[str, str]:
    """(state 'ok' / 'info' / 'warn', text) for /durum."""

    found = reports(folder)
    done = [m for m in HIGH_RISK if m in found]
    expired = [m for m in done if today - found[m].day > VALID_FOR]
    unusable = [m for m in done if found[m].verdict.lower().startswith("kullanılamaz")]
    text = f"yüksek riskli modellerin {len(done)}/{len(HIGH_RISK)}'i bağımsız doğrulandı"
    if done:
        text += " (" + ", ".join(f"{m} {found[m].verdict}" for m in done) + ")"
    if expired:
        text += f"; süresi geçen: {', '.join(expired)}"
    if expired or unusable:
        return "warn", text
    return ("ok" if len(done) == len(HIGH_RISK) else "info"), text


__all__ = ["HIGH_RISK", "Report", "reports", "status"]
