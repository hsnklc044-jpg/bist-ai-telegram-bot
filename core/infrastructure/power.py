"""Power watch (25.11.2026, repair queue 1; the PC ran out of battery and slept on 19.11, 21.11 and 24.11).

Windows GetSystemPowerStatus is read with ctypes (no new dependency). On battery below 30% the owner gets one
line; below 15% one more. Nothing between 23:00 and 07:00 (not consumed: still on battery at 07:00 means the
message goes then). Back on mains starts a new cycle. Unknown readings stay silent."""

from __future__ import annotations

import sys
from datetime import datetime

LOW = 30
CRITICAL = 15
QUIET_FROM = 23
QUIET_TO = 7
UNKNOWN = 255


def read_status() -> tuple[int | None, int | None]:
    """(ACLineStatus, BatteryLifePercent); (None, None) off Windows or on any failure."""

    if sys.platform != "win32":
        return None, None
    try:
        import ctypes

        class _Status(ctypes.Structure):
            _fields_ = [("ACLineStatus", ctypes.c_ubyte), ("BatteryFlag", ctypes.c_ubyte),
                        ("BatteryLifePercent", ctypes.c_ubyte), ("SystemStatusFlag", ctypes.c_ubyte),
                        ("BatteryLifeTime", ctypes.c_ulong), ("BatteryFullLifeTime", ctypes.c_ulong)]

        status = _Status()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return None, None
        return status.ACLineStatus, status.BatteryLifePercent
    except Exception:  # noqa: BLE001 - a failed read must never stop the bot
        return None, None


def message(percent: int) -> str:
    return f"Bilgisayar pilde, %{percent}; prize takın"


class PowerWatch:
    def __init__(self) -> None:
        self.low_sent = False
        self.critical_sent = False

    def check(self, ac_line: int | None, percent: int | None, now: datetime) -> str | None:
        """The line to send now, or None. Flags are consumed only when a message is returned."""

        if ac_line == 1:
            self.low_sent = self.critical_sent = False
            return None
        if ac_line != 0 or percent is None or percent == UNKNOWN or percent > 100:
            return None
        if now.hour >= QUIET_FROM or now.hour < QUIET_TO:
            return None
        if percent < CRITICAL and not self.critical_sent:
            self.low_sent = self.critical_sent = True
            return message(percent)
        if percent < LOW and not self.low_sent:
            self.low_sent = True
            return message(percent)
        return None
