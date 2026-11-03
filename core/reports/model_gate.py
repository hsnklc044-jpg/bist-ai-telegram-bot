"""
QuantBIST
Model gate (the user's "ModelGovernor", DECISIONS K-70 madde 5).

A high-risk model may change something on its own (write a paper signal, open a position) only with
a current independent validation (docs/validation/<model>.md) whose verdict is "kullanılabilir".
"Kısıtlı kullanılabilir", "kullanılamaz", an expired report or no report: the model only informs and
says so. Validation produces a verdict, not a percentage, so the user's "below 90% is quarantined"
is this rule; the gate is read from the reports, never from the model's own results.

Models that act on their own are listed in AUTO_ACTIONS; the others (alerts, risk lines, the ledger)
only inform already, the gate has nothing to close for them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from core.infrastructure.logger import get_logger
from core.reports import validation

logger = get_logger(__name__)

# model -> what it would do on its own
AUTO_ACTIONS: dict[str, str] = {
    "M30": "günlük adımda kendiliğinden sanal sinyal yazmak (K-60)",
}
USABLE = "kullanılabilir"


@dataclass(frozen=True)
class Decision:
    model: str
    allowed: bool
    reason: str


def decide(model: str, today: date, folder: Path | None = None) -> Decision:
    if model not in validation.HIGH_RISK:
        return Decision(model, True, "yüksek riskli değil")
    try:
        report = validation.reports(folder).get(model)
    except OSError as exc:  # unreadable reports: closed, never open by accident
        logger.warning("Validation reports unreadable | %s", exc)
        return Decision(model, False, "doğrulama raporları okunamadı")
    if report is None:
        return Decision(model, False, "bağımsız doğrulanmadı")
    if today - report.day > validation.VALID_FOR:
        return Decision(model, False, f"doğrulamanın süresi geçmiş ({report.day:%d.%m.%Y})")
    if report.verdict != USABLE:
        why = "kısıtlı: yalnız bilgi verir" if report.verdict.startswith("kısıtlı") else report.verdict
        return Decision(model, False, why)
    return Decision(model, True, f"doğrulandı ({report.day:%d.%m.%Y}, {USABLE})")


def allowed(model: str, today: date) -> bool:
    d = decide(model, today)
    if not d.allowed:
        logger.info("Model gate closed | %s | %s", model, d.reason)
    return d.allowed


def status(today: date, folder: Path | None = None) -> tuple[str, str]:
    """(state, text) for /durum: every automatic action and whether its model may run it."""

    parts = []
    for model, action in AUTO_ACTIONS.items():
        d = decide(model, today, folder)
        parts.append(f"{model} {'açık' if d.allowed else 'kapalı'} ({d.reason}): {action}")
    return "info", "otomatik eylemler: " + "; ".join(parts)


__all__ = ["AUTO_ACTIONS", "Decision", "allowed", "decide", "status"]
