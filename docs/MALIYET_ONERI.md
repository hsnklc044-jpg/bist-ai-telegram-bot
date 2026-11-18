# Maliyet ve uygulanabilirlik parametreleri: öneri (taslak, 18.11.2026)

**Karar sahibin.** Bu değerler ön kayıt konusudur (ANAYASA Md. 3 ve 7, ARS-1 C-1…C-3).
- Kodda (`core/research/costs.py`) hiçbir varsayılan yoktur; değerleri her çağıran açıkça verir.
- Bu belge yalnız öneridir. K-93 ve K-94'teki maliyetler kesinleşmiştir ve değişmez.

| Parametre | Öneri | Kaynak / gerekçe | Durum |
|---|---|---|---|
| Komisyon (tek yön) | %0,10 | a4 ön kaydı (RESEARCH_LOG:479; 28.10) ile aynı | proje içi tutarlılık |
| Komisyon üzerine BSMV | %5 | BSMV oranı | **resmî kaynaktan doğrulanacak** |
| Borsa payı (tek yön) | — | Borsa İstanbul tarifesi | **kaynaktan alınacak**; bu gece okunamadı |
| Yarım alış-satış farkı | hissenin son 60 seanslık medyan farkının yarısı; yoksa bir fiyat adımı / fiyat | ölçülebilir, likiditeye bağlı | yöntem önerisi |
| Kayma tabanı (`base`) | %0,05 | K-94 (c) model varsayımı ve a4 | proje içi tutarlılık |
| Kayma etkisi (`impact`) | ön kayıtta sabitlenir; sahip için iki seçenek: 0,1 ve 0,3 | karekök etki modeli, `slippage = base + impact·√(emir/ortalama günlük hacim)` | **karar sahibin** |
| Kapasite (`max_share`) | ortalama günlük işlem hacminin %1'i | K-94 (c) ile aynı | proje içi tutarlılık |
| Fiyat adımı tablosu | Borsa İstanbul Pay Piyasası Prosedürü'ndeki tablo (`cikti/pay-piyasasi-proseduru.pdf`) | resmî | **bu gece okunamadı**: PDF'i metne çevirecek araç yok, program kurulmaz. Değerler kaynaktan elle ya da sahip onaylı bir araçla alınacak |
| Tavan/taban kilidi | ±%9,5 hareket kilit sayılır (K-75, `core/market/limits.py`) | proje kararı | var; değişmez |

**Sahibe sorulanlar:**
- `impact` için seçenek 0,1 ya da 0,3;
- yarım fark yöntemi;
- BSMV ve borsa payının resmî değerlerini kimin, hangi kaynaktan alacağı.
