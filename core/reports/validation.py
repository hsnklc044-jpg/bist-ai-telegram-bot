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


VERDICTS = ("kısıtlı kullanılabilir", "kullanılamaz", "kullanılabilir")  # the longest match first


def _day(text: str) -> date | None:
    m = re.search(r"^[-*\s]*\**Tarih\**:?\**\s*(\d{4})-(\d{2})-(\d{2})", text, flags=re.M) or \
        re.search(r"^[-*\s]*\**Tarih\**:?\**\s*(\d{2})\.(\d{2})\.(\d{4})", text, flags=re.M)
    if not m:
        return None
    a, b, c = (int(x) for x in m.groups())
    return date(a, b, c) if a > 31 else date(c, b, a)


def _verdict(text: str) -> str | None:
    """'Karar: …' on one line, or the first verdict word under a '## … Karar' heading."""

    lowered = text.replace("İ", "i").replace("I", "ı").lower()
    m = re.search(r"^[-*\s]*\**karar\**:\**\s*(.+)$", lowered, flags=re.M)
    part = m.group(1) if m else None
    if part is None:
        h = re.search(r"^#+[^\n]*karar[^\n]*\n(.*?)(?=^#|\Z)", lowered, flags=re.M | re.S)
        part = h.group(1) if h else None
    if part is None:
        return None
    return next((v for v in VERDICTS if v in part), None)


def reports(folder: Path | None = None) -> dict[str, Report]:
    folder = Path(folder or VALIDATION_DIR)
    out = {}
    for path in sorted(folder.glob("M*.md")) if folder.exists() else []:
        text = path.read_text(encoding="utf-8")
        day, verdict = _day(text), _verdict(text)
        if day and verdict:
            out[path.stem] = Report(path.stem, day, verdict)
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
