"""
QuantBIST
BIST 30 list as the user gave it (03.11.2026), Yahoo Finance format. data/bist30.csv carries the
same list for /tara evren=bist30 (tests/test_data.py keeps the two equal).

The list has no official source attached yet: when Borsa İstanbul changes the index (quarterly),
update both. A ticker Yahoo does not know is reported by core.market.hourly, never silently
dropped.
"""

BIST30_TICKERS = [
    "AKBNK.IS", "ALARK.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "BRSAN.IS", "EKGYO.IS", "ENKAI.IS",
    "EREGL.IS", "FROTO.IS", "GARAN.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KONTR.IS", "TRALT.IS", "KRDMD.IS",
    "MGROS.IS", "ODAS.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TAVHL.IS", "TCELL.IS",
    "THYAO.IS", "TOASO.IS", "TUPRS.IS",
]
SOURCE = "kullanıcı listesi, 03.11.2026"
# Two codes of the given list do not exist on Yahoo (checked 03.11.2026, Actions run 41637982348):
# EKOY.IS -> EKGYO.IS (Emlak Konut) and KOZAL.IS -> TRALT.IS (Koza Altın's code; its data starts 24.11.2025).

__all__ = ["BIST30_TICKERS", "SOURCE"]
