"""
QuantBIST RC7 API Layer

Bu paket, QuantBIST servislerini dış dünyaya tek bir giriş
noktasından sunar.

Katmanlar
---------
Dashboard  -> core.dashboard.service
Decision   -> core.decision.service
Reports    -> core.reports.service
Export     -> core.export.service

Bu pakette iş mantığı bulunmaz.
Sadece mevcut servisleri dışarı açan API katmanıdır.
"""

from .dashboard import get_dashboard
from .decision import get_decision
from .reports import get_report
from .export import (
    export_report,
    save_report,
    export_file,
)

__all__ = [
    "get_dashboard",
    "get_decision",
    "get_report",
    "export_report",
    "save_report",
    "export_file",
]
