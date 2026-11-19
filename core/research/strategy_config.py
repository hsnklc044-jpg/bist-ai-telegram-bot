"""Strategy config files with a hash (#8, K-113 Dalga 2).

A strategy's settings live in one file (TOML read with the stdlib `tomllib`, or JSON) so that a run can
name exactly which settings it used. Fields:

- `ad` (text), `surum` (text), `evren` (text, e.g. "BIST100"), `olusturma_tarihi` (date, YYYY-MM-DD);
- `parametreler`: a table of the strategy's parameters (text, whole number, decimal, true/false,
  lists and nested tables of these);
- `maliyet`: a table of cost assumptions; every value is a non-negative number;
- optional: `aciklama` (text), `ornek` (true/false; true marks an example, not a real strategy).

Unknown top-level fields are refused (a typo must not pass silently). The hash is the SHA-256 of the
canonical form: JSON with sorted keys, no spaces, UTF-8, the date as YYYY-MM-DD. Key order and file
format do not change it; any change of a value (also 20 -> 20.0, a different type) does.

Pure tools: nothing here runs a strategy, reads market data or is called by the bot.
"""

from __future__ import annotations

import hashlib
import json
import math
import tomllib
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

REQUIRED = ("ad", "surum", "evren", "olusturma_tarihi", "parametreler", "maliyet")
OPTIONAL = ("aciklama", "ornek")
TEXT_FIELDS = ("ad", "surum", "evren")


class StrategyConfigError(ValueError):
    """A strategy config file or mapping is not valid; the message says which field and why."""


def _value(value: Any, where: str) -> Any:
    """A copy of one parameter value, or an error if its type cannot be hashed the same way everywhere."""

    if isinstance(value, bool) or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StrategyConfigError(f"{where}: sonlu bir sayı olmalı (NaN ya da sonsuz olamaz)")
        return value
    if isinstance(value, list):
        return [_value(v, f"{where}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, Mapping):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str) or not k.strip():
                raise StrategyConfigError(f"{where}: anahtarlar boş olmayan metin olmalı ({k!r})")
            out[k] = _value(v, f"{where}.{k}")
        return out
    raise StrategyConfigError(
        f"{where}: desteklenmeyen değer türü {type(value).__name__} "
        "(metin, tam sayı, ondalık, true/false, liste ya da tablo olmalı)"
    )


def validate(data: Mapping[str, Any]) -> dict:
    """Check a config mapping and return a clean copy; the input is not changed."""

    if not isinstance(data, Mapping):
        raise StrategyConfigError("strateji ayarı bir tablo (anahtar = değer) olmalı")
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise StrategyConfigError(f"eksik alan: {', '.join(missing)}")
    unknown = sorted(k for k in data if k not in REQUIRED + OPTIONAL)
    if unknown:
        raise StrategyConfigError(
            f"bilinmeyen alan: {', '.join(map(str, unknown))} (izinli: {', '.join(REQUIRED + OPTIONAL)})"
        )

    out: dict[str, Any] = {}
    for key in TEXT_FIELDS:
        value = data[key]
        if not isinstance(value, str) or not value.strip():
            raise StrategyConfigError(f"{key}: boş olmayan metin olmalı ({value!r})")
        out[key] = value

    created = data["olusturma_tarihi"]
    if isinstance(created, str):
        try:
            created = date.fromisoformat(created)
        except ValueError:
            raise StrategyConfigError(
                f"olusturma_tarihi: YYYY-AA-GG biçiminde tarih olmalı ({created!r})"
            ) from None
    if isinstance(created, datetime) or not isinstance(created, date):
        raise StrategyConfigError(f"olusturma_tarihi: saatsiz tarih olmalı ({created!r})")
    out["olusturma_tarihi"] = created

    params = data["parametreler"]
    if not isinstance(params, Mapping):
        raise StrategyConfigError("parametreler: bir tablo olmalı ([parametreler])")
    out["parametreler"] = _value(params, "parametreler")

    costs = data["maliyet"]
    if not isinstance(costs, Mapping):
        raise StrategyConfigError("maliyet: bir tablo olmalı ([maliyet])")
    clean_costs = {}
    for k, v in costs.items():
        where = f"maliyet.{k}"
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise StrategyConfigError(f"{where}: negatif olmayan sonlu bir sayı olmalı ({v!r})")
        clean_costs[str(k)] = v
    out["maliyet"] = clean_costs

    if "aciklama" in data:
        if not isinstance(data["aciklama"], str):
            raise StrategyConfigError("aciklama: metin olmalı")
        out["aciklama"] = data["aciklama"]
    if "ornek" in data:
        if not isinstance(data["ornek"], bool):
            raise StrategyConfigError("ornek: true ya da false olmalı")
        out["ornek"] = data["ornek"]
    return out


def load(path: Path | str) -> dict:
    """Read and validate a .toml or .json config file."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in (".toml", ".json"):
        raise StrategyConfigError(f"{path.name}: yalnız .toml ya da .json strateji ayarı okunur")
    try:
        if suffix == ".toml":
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
        else:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh, parse_constant=_no_constant)
    except (OSError, tomllib.TOMLDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise StrategyConfigError(f"{path.name} okunamadı: {exc}") from None
    try:
        return validate(data)
    except StrategyConfigError as exc:
        raise StrategyConfigError(f"{path.name}: {exc}") from None


def _no_constant(name: str):
    raise ValueError(f"{name} geçerli bir sayı değil")


def canonical(config: Mapping[str, Any]) -> str:
    """The canonical text of a validated config: sorted keys, no spaces, the date as YYYY-MM-DD."""

    clean = validate(config)
    clean["olusturma_tarihi"] = clean["olusturma_tarihi"].isoformat()
    return json.dumps(clean, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def config_hash(config: Mapping[str, Any]) -> str:
    """SHA-256 (hex) of the canonical form; any value change changes it."""

    return hashlib.sha256(canonical(config).encode("utf-8")).hexdigest()


__all__ = ["StrategyConfigError", "canonical", "config_hash", "load", "validate"]
