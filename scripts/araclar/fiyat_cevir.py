"""Indirilen fiyat dosyalarini QuantBIST ikinci kaynak bicimine cevirir. Claude kotasi harcamaz.

Kullanim: Her hisse icin CSV dosyasini data/inbox/fiyat_indir klasorune koy (git disinda), dosya adi hisse koduyla
baslasin (ornek: THYAO.csv, ASELS_gecmis.csv). Ya da tek dosyada kod/hisse sutunu olsun.
    python scripts/araclar/fiyat_cevir.py [--klasor KLASOR]
Cikti: KLASOR/../fiyatlar.csv (date,code,close). Hicbir fiyat uretmez; yalnizca dosyadaki degeri tasir.
Sonra: python -m core.market.second_source --dosya data/inbox/fiyatlar.csv --kaynak "nereden geldigi"
(11.11.2026'da C:\Projeler\QuantBIST-araclar'dan depoya alindi; L madde 1.)
"""
import csv
import pathlib
import re
import sys
from datetime import date, datetime

KLASOR = pathlib.Path(__file__).resolve().parents[2] / "data" / "inbox"  # git disinda
TARIH = ("tarih", "date", "gun")
KAPANIS = ("kapanis", "close", "son fiyat", "son")
KOD = ("kod", "code", "hisse", "sembol", "symbol")
BICIMLER = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%y")


def sade(metin: str) -> str:
    return (metin.strip().lower().replace("ı", "i").replace("İ", "i").replace("i̇", "i")
            .replace("ş", "s").replace("ç", "c").replace("ğ", "g").replace("ü", "u").replace("ö", "o"))


def tarih_oku(metin: str) -> date | None:
    parca = metin.strip().split(" ")[0]
    for bicim in BICIMLER:
        try:
            return datetime.strptime(parca, bicim).date()
        except ValueError:
            pass
    return None


def sayi_oku(metin: str) -> float | None:
    s = metin.strip().replace(" ", "").replace("₺", "").replace("TL", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        deger = float(s)
    except ValueError:
        return None
    return deger if deger > 0 else None


def sutun(basliklar: list[str], adaylar: tuple[str, ...]) -> int | None:
    for aday in adaylar:  # once tam eslesme, sonra icinde gecen
        for i, b in enumerate(basliklar):
            if b == aday:
                return i
    for aday in adaylar:
        if len(aday) > 3:
            for i, b in enumerate(basliklar):
                if aday in b:
                    return i
    return None


def dosya_oku(yol: pathlib.Path) -> tuple[list[tuple[date, str, float]], int]:
    for kodlama in ("utf-8-sig", "cp1254"):
        try:
            metin = yol.read_text(encoding=kodlama)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("kodlama okunamadi")
    satirlar = [s for s in metin.splitlines() if s.strip()]
    if not satirlar:
        raise ValueError("dosya bos")
    ayrac = max(";,\t", key=satirlar[0].count)
    tablo = list(csv.reader(satirlar, delimiter=ayrac))
    basliklar = [sade(b) for b in tablo[0]]
    t, k, h = sutun(basliklar, TARIH), sutun(basliklar, KAPANIS), sutun(basliklar, KOD)
    if t is None or k is None:
        raise ValueError(f"tarih veya kapanis sutunu bulunamadi; basliklar: {tablo[0]}")
    ad = re.match(r"[A-Za-z0-9]+", yol.stem)
    varsayilan = ad.group(0).upper() if ad else ""
    cikan, hatali = [], 0
    for satir in tablo[1:]:
        if len(satir) <= max(t, k):
            hatali += 1
            continue
        gun, fiyat = tarih_oku(satir[t]), sayi_oku(satir[k])
        kod = satir[h].strip().upper().removesuffix(".IS") if h is not None and len(satir) > h else varsayilan
        if gun is None or fiyat is None or not kod:
            hatali += 1
            continue
        cikan.append((gun, kod, fiyat))
    return cikan, hatali


def main(girdi: pathlib.Path | None = None, cikti: pathlib.Path | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    girdi = girdi or KLASOR / "fiyat_indir"
    cikti = cikti or KLASOR / "fiyatlar.csv"
    girdi.mkdir(exist_ok=True)
    dosyalar = sorted(p for p in girdi.iterdir() if p.suffix.lower() in (".csv", ".txt"))
    if not dosyalar:
        print(f"Dosya yok. CSV dosyalarini buraya koy: {girdi}")
        return 1
    tum: dict[tuple[date, str], float] = {}
    sorun = False
    for yol in dosyalar:
        try:
            satirlar, hatali = dosya_oku(yol)
        except ValueError as hata:
            print(f"SORUN {yol.name}: {hata}")
            sorun = True
            continue
        if hatali:
            print(f"UYARI {yol.name}: {hatali} satir okunamadi, atlandi")
        for gun, kod, fiyat in satirlar:
            onceki = tum.get((gun, kod))
            if onceki is not None and onceki != fiyat:
                print(f"SORUN {kod} {gun}: iki farkli kapanis ({onceki}, {fiyat})")
                sorun = True
            tum[(gun, kod)] = fiyat
    if sorun or not tum:
        print("fiyatlar.csv yazilmadi." if sorun else "Okunabilen satir yok; fiyatlar.csv yazilmadi.")
        return 1
    with cikti.open("w", encoding="utf-8", newline="") as f:
        yazici = csv.writer(f)
        yazici.writerow(["date", "code", "close"])
        for (gun, kod), fiyat in sorted(tum.items(), key=lambda x: (x[0][1], x[0][0])):
            yazici.writerow([gun.isoformat(), kod, f"{fiyat:.4f}"])
    for kod in sorted({k for _, k in tum}):
        gunler = sorted(g for g, k in tum if k == kod)
        print(f"{kod}: {len(gunler)} gun, {gunler[0]} - {gunler[-1]}")
    print(f"Yazildi: {cikti} ({len(tum)} satir)")
    return 0


if __name__ == "__main__":
    import argparse

    secim = argparse.ArgumentParser(description="Indirilen fiyat dosyalarini ikinci kaynak bicimine cevirir")
    secim.add_argument("--klasor", type=pathlib.Path, default=None, help="girdi klasoru (varsayilan data/inbox/fiyat_indir)")
    a = secim.parse_args()
    raise SystemExit(main(a.klasor, a.klasor.parent / "fiyatlar.csv" if a.klasor else None))
