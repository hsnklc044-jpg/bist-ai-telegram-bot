# Araştırma programı: deneme bütçesi, holdout ve ön kayıt

MATURITY S4 ("deneme bütçesi, holdout ve ön kayıtla en az bir tam döngü"). 27.10.2026'da, **yeni hiçbir test görülmeden** yazıldı (DECISIONS K-22). Amaç: bir kuralın maliyet sonrası XU100'den gerçekten ayrılıp ayrılmadığını, aynı veride tekrar tekrar deneyerek kendimizi kandırmadan öğrenmek. Çıktı her zaman bilgi amaçlıdır; gerçek para, emir ya da al/sat önerisi yoktur.

## 1. Neden holdout geçmişte olamaz

2022 – 27.10.2026 arasındaki bütün veri 13 kuralın testinde görüldü ([RESEARCH_LOG](RESEARCH_LOG.md), "Reddedilen fikir türleri"). Bu dönemden bir parçayı sonradan "ayrılmış" saymak dürüst olmaz: hangi fikirlerin denenmeye değer olduğu o veriye bakılarak seçildi. Geçmişi 2015'e uzatmak kaynak yokluğundan engelli (K-16). Bu yüzden:

- **Holdout = ileri veri: 02.11.2026 seansından itibaren.** Bu tarihten önce hiçbir kural bu dönemde değerlendirilmedi.
- Holdout sonucu, bir kural için belirlenen tarihten önce **hesaplanmaz ve bakılmaz**. Haftalık araştırma yalnız tarama dönemini (aşağıda) yeniden hesaplar.
- **Kodda zorunlu (v0.59.0):** bütün araştırma araçları fiyatı `core.backtest.run.load_frames` ile yükler; o fonksiyon veriyi 30.10.2026'da keser (`SCREEN_END`, `HOLDOUT_START`). Holdout'u yalnız ön kayıtlı bir holdout kararı `include_holdout=True` ile açar (`test_holdout`). Bu yüzden 02.11.2026'dan sonra haftalık araştırma sonuçları sabit kalır; değişirse nedeni veri düzeltmesidir. Günlük rapor ve canlı ölçüm etkilenmez.

## 2. Bir döngü

1. **Ön kayıt** (testten önce, git commit'iyle zaman damgalı; yeni hipotez onayı 28.10.2026'dan beri Claude'da, K-28): hipotez, kural, sabit parametreler, evren, maliyet (komisyon %0,10 + kayma %0,05 her yön), nakit varsayımı ve kaynağı, birincil ölçüt, sağlamlık kapıları, holdout karar tarihi. Ön kayıt RESEARCH_LOG'a yazılır; sonra değiştirilmez.
2. **Tarama** (2023-08-01 – 30.10.2026, geçmiş BIST 100 üyeliği): Aşama 3'teki birincil ölçüt (XU100'e göre fazla getirinin blok bootstrap GA'sı, döngüdeki hipotez sayısına Bonferroni) ve üç kapı. Geçemeyen reddedilir, ayarlanmaz.
3. **Holdout kararı** (yalnız taramayı geçenler; en az **250 seans** ileri veri, yani en erken Kasım 2027): aynı kural, aynı parametre, aynı ölçüt; tek yönlü test, Bonferroni yalnız holdout'a giren hipotez sayısına. Bu arada kural canlı ölçümde ve sanal hesapta izlenebilir (gerçek para yok).
4. **Kayıt**: sonuç ne olursa olsun RESEARCH_LOG'a olduğu gibi; "Reddedilen fikir türleri" tablosu güncellenir.

## 3. Deneme bütçesi

- Bir döngüde **en çok 3 hipotez**; **6 ayda en çok bir döngü**. Böylece yılda en çok 6 yeni hipotez; her biri kayıtlı.
- Tarama aşamasında Bonferroni döngü içinde uygulanır. Holdout'a yılda en çok 2 kural girer (yanlış pozitif olasılığını holdout'ta sınırlamak için).
- Bütçe harcandıysa aynı dönemde yeni test yapılmaz; "biraz farklı" bir varyant da yeni hipotez sayılır.
- Reddedilen türlerin yeni varyantları (RESEARCH_LOG özet tablosu) bütçeden harcanmaya bile değmez: denenmez.

| Döngü | Tarih | Hipotez | Bütçe | Durum |
|---|---|---|---|---|
| a1 (ana tablo) | 26.10.2026 | 6 kural | ön kayıtsız, bütçe öncesi | hepsi red |
| a2 (aday kurallar) | 26.10.2026 | 4 kural | ön kayıtsız, bütçe öncesi | hepsi red |
| a3 (Aşama 3) | 27.10.2026 | H1–H3 | 3/3, ön kayıtlı | hepsi taramada red; holdout'a giren yok |
| a4 | ön kayıt 28.10.2026; tarama en erken 27.04.2027 | H4 eşit ağırlık, H5 düşük işlem hacmi | 2/3 | ön kayıtlı ([RESEARCH_LOG](RESEARCH_LOG.md) "a4 ön kaydı"); onay Claude'da (K-28) |

## 4. S4 için "tam döngü" ne zaman sayılır

Ön kayıt → tarama → (taramayı geçen varsa) holdout kararı → kayıt adımlarının hepsi bitince. Taramada hepsi reddedilen bir döngü de tam döngüdür: holdout'a gerek kalmamıştır, ama holdout kuralı önceden yazılmış olmalıdır. a3 bu kural yazılmadan önce yapıldığı için "kısmi" sayılır; ilk tam döngü a4 olur (en erken Nisan 2027).
