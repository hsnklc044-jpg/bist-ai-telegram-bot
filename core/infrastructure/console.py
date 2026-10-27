"""
QuantBIST
Printing on Windows.

When Windows redirects output (a scheduled task, `| Out-Null` in a script, a file), Python
uses the ANSI code page (cp1254), which has no emoji: a report line such as "🩺" then crashes
the print. Every command the user runs on the PC calls utf8_output() first.
"""

from __future__ import annotations


def utf8_output(stream=None) -> None:
    import sys

    stream = stream or sys.stdout
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


__all__ = ["utf8_output"]
