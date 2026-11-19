"""Market note template (piyasa notu şablonu, DECISIONS K-110).

For stock and index notes only; management reports keep their own format (CHARTER_2028 §7).
Every field is written; a missing value is written as "henüz ölçülmedi" or "veri yok", never
dropped. Vague adjectives and buy/sell words are refused, the note writes scenarios.
Not wired into the bot yet: that is a behaviour change and needs the owner's approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

WARNING = "Uyarı: Bu not bir senaryo kaydıdır; yatırım tavsiyesi değildir."
NOT_MEASURED = "henüz ölçülmedi"
NO_DATA = "veri yok"

# Whole words only: "sat" must not hit "satır", "al" must not hit "alt".
BANNED = ("al", "sat", "alın", "satın", "alım fırsatı", "satış fırsatı", "güçlü", "güçlüce", "kalıcı",
          "sert", "kesin", "kesinlikle", "fırsat")
_BANNED_RE = re.compile(r"(?<![\wçğıöşü])(" + "|".join(re.escape(w) for w in BANNED) + r")(?![\wçğıöşü])",
                        re.IGNORECASE)


@dataclass(frozen=True)
class Note:
    varlik: str
    fiyat: float | None
    fiyat_zamani: str            # "2026-11-19 18:10 (günlük kapanış)"
    sure: str                    # "Günlük, 10 işlem günü"
    konum_tl: str | None         # trend and position against 20/50/200-day averages, TL basis
    konum_usd: str | None        # the same in USD basis
    bekleme_bolgesi: str | None  # "345–350"
    teyit: str | None            # "350 üstü günlük kapanış"
    hedefler: str | None         # "360 / 365–370"
    gecersizlik: float | None    # one number: a close beyond it ends the scenario
    gecersizlik_yonu: str        # "altı" or "üstü"
    hedef_atr: float | None      # distance to the first target in ATRs
    gecmis_oran: str | None      # "%X (N örnek)"; None -> "henüz ölçülmedi"
    ozet: str


def problems(text: str) -> list[str]:
    """Banned words found in a note (case-insensitive, whole words)."""
    return sorted({m.group(1).lower() for m in _BANNED_RE.finditer(text)})


def render(n: Note) -> str:
    if n.gecersizlik_yonu not in {"altı", "üstü"}:
        raise ValueError("geçersizlik yönü 'altı' ya da 'üstü' olmalı")
    if n.fiyat is not None and not n.fiyat_zamani:
        raise ValueError("fiyat tarih ve saatsiz yazılmaz")
    if not n.ozet or len(re.findall(r"[.!?](\s|$)", n.ozet.strip())) > 1:
        raise ValueError("özet tek cümle olmalı")
    price = NO_DATA if n.fiyat is None else f"{n.fiyat:,.2f} ({n.fiyat_zamani})"
    inv = NO_DATA if n.gecersizlik is None else f"{n.gecersizlik:,.2f} {n.gecersizlik_yonu} günlük kapanış"
    if n.hedef_atr is None:
        atr = NOT_MEASURED
    else:
        atr = f"{n.hedef_atr:.1f} ATR" + (" (1'in altı: gürültü)" if n.hedef_atr < 1 else "")
    lines = [
        f"{n.varlik}",
        f"Fiyat: {price}",
        f"Süre: {n.sure}",
        f"Konum (TL): {n.konum_tl or NO_DATA}",
        f"Konum (USD): {n.konum_usd or NO_DATA}",
        f"Bekleme bölgesi: {n.bekleme_bolgesi or NO_DATA}; teyit: {n.teyit or NO_DATA}",
        f"Hedefler: {n.hedefler or NO_DATA}",
        f"Geçersizlik: {inv}",
        f"Hedef / ATR: {atr}",
        f"Geçmiş oran: {n.gecmis_oran or NOT_MEASURED}",
        f"Özet: {n.ozet}",
        WARNING,
    ]
    text = "\n".join(lines)
    bad = problems(text.replace(WARNING, ""))
    if bad:
        raise ValueError(f"notta yasak sözcük: {', '.join(bad)}")
    return text
