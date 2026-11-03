from pathlib import Path
import hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parent
DECISIONS = ROOT / "price_fix_safety_decisions.csv"
DATABASE = ROOT / "market_research.db"
EXPECTED_SHA = "fdc98f2fb96f764dc5639bc36cb3975986cf75ff279bcee64cdc822d4ac4d5ab"
DECISIONS_SHA256 = "553c76f5fd52e2f7e79ca0f461818608aabe342aa8aff606396aba85225bedb9"

class PriceFixGateError(ValueError):
    pass

def validate_price_fixes(candidate):
    candidate = Path(candidate).resolve()

    for path in (candidate, DECISIONS, DATABASE):
        if not path.is_file():
            raise PriceFixGateError(f"Eksik dosya: {path}")

    digest = hashlib.sha256(DATABASE.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA:
        raise PriceFixGateError("Arastirma veritabani surumu farkli.")

    current_sha = hashlib.sha256(DECISIONS.read_bytes()).hexdigest()
    if current_sha != DECISIONS_SHA256:
        raise PriceFixGateError("Guvenlik karar dosyasi degistirilmis.")

    decisions = pd.read_csv(
        DECISIONS, dtype={"symbol": str, "date": str}
    )
    proposed = pd.read_csv(
        candidate, dtype={"symbol": str, "date": str}
    )

    required = {"symbol", "date", "factor"}
    if not required.issubset(proposed.columns):
        raise PriceFixGateError("Duzeltme CSV sutunlari eksik.")

    if not required.union(
        {"approved_for_application"}
    ).issubset(decisions.columns):
        raise PriceFixGateError("Guvenlik CSV sutunlari eksik.")

    if proposed.empty:
        raise PriceFixGateError("Bos duzeltme dosyasi reddedildi.")
    if decisions.empty:
        raise PriceFixGateError("Bos guvenlik karar dosyasi reddedildi.")

    keys = ["symbol", "date"]
    if (
        proposed.duplicated(keys).any()
        or decisions.duplicated(keys).any()
    ):
        raise PriceFixGateError("Tekrarlanan kayit bulundu.")

    merged = proposed.merge(
        decisions[
            ["symbol", "date", "factor", "approved_for_application"]
        ],
        on=keys,
        how="left",
        suffixes=("_candidate", "_approved"),
        validate="one_to_one"
    )

    if merged["approved_for_application"].isna().any():
        raise PriceFixGateError("Onay listesinde olmayan kayit var.")

    f1 = pd.to_numeric(
        merged["factor_candidate"], errors="coerce"
    )
    f2 = pd.to_numeric(
        merged["factor_approved"], errors="coerce"
    )

    if f1.isna().any() or f2.isna().any():
        raise PriceFixGateError("Gecersiz fiyat carpani.")

    if not (f1 == f2).all():
        raise PriceFixGateError("Carpan uyusmazligi.")

    approved = (
        merged["approved_for_application"]
        .astype(str).str.lower().eq("true")
    )

    if not approved.all():
        raise PriceFixGateError(
            f"ENGELLENDI: {int((~approved).sum())} "
            "onaysiz fiyat duzeltmesi."
        )

    return True

if __name__ == "__main__":
    sample = (
        Path.home()
        / "AppData/Local/Temp/QuantBIST-OHLC-Audit-20261027"
        / "latest_price_fixes.csv"
    )

    try:
        validate_price_fixes(sample)
    except PriceFixGateError as exc:
        print("=== GUVENLIK KAPISI TESTI ===")
        print(str(exc))
        print(
            "TEST BASARILI: Onaysiz duzeltmeler reddedildi."
        )
    else:
        raise SystemExit(
            "TEST BASARISIZ: Duzeltmeler engellenmedi."
        )
