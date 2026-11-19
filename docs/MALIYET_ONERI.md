# Maliyet ve uygulanabilirlik parametreleri: öneri (taslak, 18.11.2026)

**Karar sahibin.** Bu değerler ön kayıt konusudur (ANAYASA Md. 3 ve 7, ARS-1 C-1…C-3).
- Kodda (`core/research/costs.py`) hiçbir varsayılan yoktur; değerleri her çağıran açıkça verir.
- Bu belge yalnız öneridir. K-93 ve K-94'teki maliyetler kesinleşmiştir ve değişmez.

| Parametre | Öneri | Kaynak / gerekçe | Durum |
|---|---|---|---|
| Komisyon (tek yön) | %0,10 | a4 ön kaydı (RESEARCH_LOG:476; 28.10) ile aynı | proje içi tutarlılık |
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

## Ek: Dalga 1 #7, maliyet ve icra modeli taslağı (19.11.2026 09:56; sahibin talimatı, karar yine sahibin)

Kaynak: sahibin araştırma raporu `quantbist-talimatlar/ARASTIRMA_SISTEMLER.md`. Rapordaki sayıların birincil belgesi bu oturumda okunmadı; "doğrulandı" sayılmaz.

| Parametre | Rapordaki değer | Bu belgedeki önceki öneri | Durum |
|---|---|---|---|
| Komisyon (tek yön) | binde 2–3,2 (Garanti BBVA 2026 formunda azami binde 3,2) | %0,10 (a4 ile aynı) | seçenekler: %0,10 / %0,20 / %0,32; **sahibin kararı** |
| BSMV | komisyonun %5'i (komisyon × 1,05) | %5 | iki kaynak aynı; resmî metin hâlâ okunmadı |
| Borsa payı ve takas | hacim üzerinden, tutarı raporda yok (Halk Yatırım tarifesi) | — | **tutar bilinmiyor**; tarife okunacak |
| Stopaj (hisse alım-satım kazancı) | %0 | — | rapordaki değer |
| Kayma | küçük hissede daha yüksek | `base` %0,05 + `impact`·√(emir/hacim) | aynı yöntem; `impact` sahibin |
| "Ertesi açılış" | 09:55–10:00 açılış seansı tek fiyatı | kâğıt portföy ve geri test ertesi günün `open` alanını kullanıyor | **Yahoo `open` alanının açılış seansı fiyatı olduğu doğrulanmadı**; resmî gün sonu dosyasıyla (official.db) karşılaştırılacak |
| Tavan/taban kilidi | tavanda kilitli alınamaz, tabanda kilitli satılamaz | ±%9,5 kilit (K-75, `core/market/limits.py`), geri test ve kâğıt portföyde uygulanıyor | var; günlük fiyat sınırının kesin oranı Pay Piyasası Prosedürü'nden **teyit edilmedi** |
| Yarım günler | arife yarım günü (ör. 28.10.2026, sürekli işlem 12:30'a kadar) | takvim biliyor (`core/market/calendar.py`, `bist_holidays.csv`), geri test ve kâğıt portföy kullanmıyor | **eksik**; 18.12 öncesi araç işi |

**Kodda bugün:** geri test ve kâğıt portföy yalnız `COMMISSION=0,001` ve `SLIPPAGE=0,0005` kullanıyor (`core/config/trading.py`). BSMV ve borsa payı hiçbir yerde düşülmüyor. `core/research/costs.py` bunları hesaplar ama bağlı değil. Değerler sahip onaylamadan bağlanmaz (K-108 madde 6, 18.12 paketi).
