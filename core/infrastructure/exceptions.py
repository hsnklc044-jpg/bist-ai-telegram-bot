"""
QuantBIST
Exceptions.
"""

from __future__ import annotations


class FrameworkError(Exception):
    """Base class for QuantBIST errors."""


class ConfigurationError(FrameworkError):
    """Missing or invalid settings (.env)."""


class MarketError(FrameworkError):
    """Price data missing, too short or unusable."""


class PersonalFileError(FrameworkError, ValueError):
    """
    A personal file (ledger, orders, watchlist, logs) cannot be read.
    The file is left as it is; the message says which file, which line and what to do.
    """

    def __init__(self, path, reason: str, line: int | None = None):
        from pathlib import Path

        self.path, self.reason, self.line = Path(path), reason, line
        where = f"satır {line}: " if line is not None else ""
        super().__init__(
            f"{self.path.name} okunamadı ({where}{reason}). Dosyaya dokunulmadı; o satırı düzeltin "
            "ya da yedekten geri yükleyin (python -m core.backup --list, --restore <zip>)."
        )


__all__ = [
    "PersonalFileError",
    "FrameworkError",
    "ConfigurationError",
    "MarketError",
]
