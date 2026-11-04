# Faz B kapanış özeti (04.11.2026)

Faz B, tavan ve taban kuralını tek yerde topladı ve kilitli günlerde dolumu kaldırdı (K-75). Kapanış koşulları sağlandı:
- Üç yeniden ölçüm kayda geçti: RESEARCH_LOG "04.11.2026 – Faz B yeniden ölçümleri".
- Yedek doğrulandı: 04.11 18:30 raporu, `quantbist_2026-11-04.zip`, 6 dosya, doğrulandı.

## Ne değişti
- **v0.99.73:** `core/market/limits.py`. %9,5 sınırı her yerde aynı ve 1e-9 pay taşıyor. 10 modül bu kuralı kullanıyor. Bir test modüllerin kendi karşılaştırmasını yasaklıyor.
- **v0.99.74:**
  - Tabanda kilitli günde satış dolmuyor. Defter, ML etiketleri ve senaryolar ilk kilitsiz açılıştan çıkıyor.
  - Tavanda kilitli günde alış dolmuyor; karne o olayı saymıyor.
- K-64 saatlik için kural ve pencere etkisini ayırmak üzere açıklayıcı bir iş akışı eklendi (`k64-split.yml`). Sonucu geçersiz.

## Ne değişmedi
- Bütün kararlar aynı:
  - K-68, K-63, K-64 (günlük ve saatlik): GEÇMEDİ.
  - K-59, K-62: KAPALI.
  - Senaryo karneleri: sıfırdan ayırt edilemiyor.
- Hiçbir eşik, kural ya da önceden yazılmış koşul değişmedi.
- K-64'ün 50 onay koşulu 41 ya da 36 onayla karşılanmış sayılmadı.
- 03.02.2027 ileri testi ve ölçütü değişmedi.
- Üretime bu sonuçlara bağlı kural değişikliği alınmadı. Kilitli gün kuralı bir dolum düzeltmesidir, karar kuralı değildir.

## Açık kalan riskler
1. **Tekrarlanabilirlik (en önemlisi):** Aynı gün 1 saat arayla K-64 saatlik 41 ve 36 onay verdi; olay sayısı 575 ve 570. Nedeni bilinmiyor. Mum sayıları farklı (63.362 ve 62.870), ama 15:39 çalışmasının K-64 adımı kendi veri aralığını yazmadı. Aynı veriden aynı sonucun çıktığı kanıtlanmadan 03.02.2027 sonucu tartışmalı olur.
2. **K-64 ayrım ölçümü geçersiz:** Değerlendirme adımları kendi veri aralığını ve satır sayısını yazmadı. Kod kontrolüne göre iki adım kendi klasörlerinden çalıştı; ama bu çalışma anında kanıtlanmadı. Kural etkisi hakkında sonuç yok.
3. **Önce ve sonra karşılaştırmaları farklı kod sürümleri arasında:** Faz B ölçümlerinde "önce" sütunu ilk çalışmadır. Arada başka düzeltmeler de var; farklar yalnız K-75'e ait değil.
4. **Saatlik veri kaynağı kayan bir pencere** (yaklaşık 1 yıl). Aynı dönem daha sonra yeniden indirilemeyebilir; donmuş bir görüntü saklanmazsa ileri test yeniden üretilemez.
5. **Bugünkü BIST 30 listesi geçmişe uygulandı** (K-68, K-63, K-64 saatlik). Hayatta kalanlar yanlılığı var.

## 03.02.2027 ileri testinde bakılacak sayılar (K-64 saatlik)
- Kural ve ölçüt değişmez:
  - Ertesi açılışta giriş, 16 mum sonra kapanış ≥ +%1,5.
  - Onay eşiği olasılık ≥ 0,60.
  - Geçme: en az 50 onay ve onaylı isabet aralığının alt ucu tabanın üstünde.
- Veri yalnız 02.11.2026 sonrası, yani holdout sonrası.
- Raporlanacaklar:
  - olay ve test sayısı;
  - onay sayısı (koşul ≥ 50);
  - onaylı isabet ve %95 aralığı (gün blok bootstrap, 2000 tekrar, tohum 0);
  - taban oran;
  - kullanılan veri aralığı, mum sayısı ve veri özeti (hash);
  - çalışan kodun commit'i.
- 04.11 referansı (bağlayıcı değil, holdout öncesi): 41 onay, %46,3 (%32,8–69,0), taban %24,5. Aynı gün ikinci görüntü: 36 onay, %44,4 (%30,0–70,0), taban %23,4.
