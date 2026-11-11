"""One interface for price and fundamental data sources (J madde 4, the user's 11.11.2026 decision).

Today the only price source is Yahoo (level 3, core.market.trust). A licensed source (the user's broker API, a
licensed vendor) connects when three things exist: an adapter registered here (written only after its terms are
recorded in docs/DATA_SOURCES.md), its name in .env as QUANTBIST_PRICE_SOURCE and its key as
QUANTBIST_PRICE_SOURCE_KEY. Choosing and paying for a source is the user's decision; nothing is scraped.

When a source connects, its first job is a comparison against the stored (Yahoo) data with the unchanged
crosscheck rules; the summary goes to the file the "Veri doğruluğu" objective reads, so the second-source check
opens again. The key is never written anywhere."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd

from core.config.paths import LOG_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

NAME_ENV = "QUANTBIST_PRICE_SOURCE"
KEY_ENV = "QUANTBIST_PRICE_SOURCE_KEY"
STATE_DIR = LOG_DIR  # kaynak_<name>.json: when the first comparison ran
COMPARE_DAYS = 60


class PriceSource(Protocol):
    """Daily candles; the same shape as core.market.provider.PriceProvider plus where the numbers come from."""

    name: str
    level: int  # core.market.trust level
    origin: str

    def fetch(self, symbols: list[str], start: date) -> dict[str, pd.DataFrame]: ...


class FundamentalSource(Protocol):
    """Financial statement items in the data/fundamentals.csv columns (core.fundamentals.store)."""

    name: str
    level: int
    origin: str

    def statements(self, codes: list[str], period_end: date) -> pd.DataFrame: ...


@dataclass(frozen=True)
class Described:
    name: str
    level: int
    origin: str


YAHOO = Described("yahoo", 3, "yahoo")  # core.market.provider.YahooProvider; unofficial, unchecked

# adapter name -> factory(key); empty until the user picks a source and its adapter is written
REGISTRY: dict[str, Callable[[str], PriceSource]] = {}


def configured(env: Mapping[str, str] | None = None) -> PriceSource | None:
    env = os.environ if env is None else env
    name = (env.get(NAME_ENV) or "").strip()
    if not name:
        return None
    factory = REGISTRY.get(name)
    if factory is None:
        logger.warning("Price source named in .env has no adapter yet | %s", name)
        return None
    key = env.get(KEY_ENV) or ""
    if not key:
        logger.warning("Price source has no key in .env | %s", name)
        return None
    return factory(key)


class _AsSecondSource:
    """A connected source seen through core.market.second_source (independence and terms checks apply)."""

    def __init__(self, source: PriceSource, today: date) -> None:
        from core.market.second_source import SourceInfo

        self.source = source
        # the key in .env is the user's act after reading the terms the adapter's author recorded
        self.info = SourceInfo(source.name, source.origin, network=True, approved_on=today,
                               terms_doc=getattr(source, "terms_doc", None))

    async def closes(self, codes: list[str], start: date, end: date) -> dict[str, pd.Series]:
        got = await asyncio.to_thread(self.source.fetch, [f"{c}.IS" for c in codes], start)
        out = {}
        for symbol, df in got.items():
            close = df["close"]
            close = close[(close.index.date >= start) & (close.index.date <= end)]
            if not close.empty:
                out[symbol.removesuffix(".IS")] = close
        return out


def first_connection(now: datetime, codes: list[str] | None = None, env: Mapping[str, str] | None = None,
                     bars=None) -> str | None:
    """The comparison report the first time a source is connected; None when none is connected or it already ran."""

    from core.market import second_source

    source = configured(env)
    if source is None:
        return None
    marker = Path(STATE_DIR) / f"kaynak_{source.name}.json"
    if marker.exists():
        return None
    if codes is None:
        from core.market.membership import members_on

        codes = sorted(s.removesuffix(".IS") for s in members_on(now.date()))
    end = now.date()
    start = end - timedelta(days=COMPARE_DAYS)
    status, name, results, summary = second_source.check([_AsSecondSource(source, end)], codes, start, end,
                                                         bars=bars, today=end)
    if summary is None:
        text = f"Yeni kaynak {source.name}: karşılaştırma yapılamadı ({name})."
    else:
        second_source.save_summary(summary)
        text = (f"Yeni kaynak {source.name} bağlandı: son {COMPARE_DAYS} gün {summary['checked']} hisse "
                f"karşılaştırıldı, {len(summary['differing'])} farklı"
                + (f" ({', '.join(summary['differing'])})" if summary["differing"] else "") + ".")
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"source": source.name, "compared_on": end.isoformat(),
                                      "checked": summary["checked"], "differing": summary["differing"]},
                                     ensure_ascii=False), encoding="utf-8")
    logger.info("First connection of a price source | %s", text)
    return text


__all__ = ["COMPARE_DAYS", "FundamentalSource", "KEY_ENV", "NAME_ENV", "PriceSource", "REGISTRY", "YAHOO",
           "configured", "first_connection"]
