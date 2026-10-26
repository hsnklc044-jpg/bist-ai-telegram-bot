# Veri düzeltmeleri kayıt defteri

Fiyat deposu (`data/market.db`) hiçbir zaman değiştirilmez. Bütün düzeltmeler okuma sırasında,
git ile sürümlenen ayrı dosyalardan uygulanır. Hiçbir düzeltme depoya geri yazılmaz.

| Katman | Dosya | Varsayılan | Etkilediği sütunlar | Geri alma |
|---|---|---|---|---|
| Şirket işlemleri | `data/corporate_actions.csv` | açık | İşlem tarihinden **önceki** tüm günlerde açılış, en yüksek, en düşük ve kapanış × katsayı; hacim ÷ katsayı | Satırı silmek (git geçmişinde kalır) |
| Seanssız günler | `data/bist_holidays.csv` + `core/market/corrections.py` | açık | O gün tamamen çıkarılır | Satırı silmek |
| Tek gün kapanış düzeltmeleri | `research-results` dalı, `datacheck/latest_price_fixes.csv` | **kapalı** | Yalnız kapanış; en yüksek ve en düşük bu kapanışı içerecek şekilde genişletilir | Kullanılmaz; yalnız `--price-fixes` ile izole deneyde açılır |

Katsayı hesabı:
- bedelsiz: 1 / (1 + oran);
- bedelli: (P + oran × fiyat) / ((1 + oran) × P). Burada P, işlemden önceki kapanış.

## İkinci kaynak kontrolünden eklenen satırlar (v0.34.0, commit 5f2d0f0, 26.10.2026)

### KCAER.IS — 28.11.2024, katsayı 0,8650

- **Olay:** %191,22 bedelsiz; sermaye 657,57 milyondan 1.915 milyon TL'ye. SPK onayı 21.11.2024 (bülten 2024/53), bölünme 28.11.2024.
- **Bileşenler:** Borsa İstanbul fiyat düzeltmesine göre %151,784 iç kaynaklardan, %39,440 kâr payından bedelsiz. Bölünme sonrası teorik fiyat 14,182 TL, yani önceki kapanış 41,30 TL.
- **Kaynaklar:** ikincil haber kopyaları (Midas, Rota Borsa, Borsanın Gündemi). KAP'taki özgün metne doğrudan erişilemedi.
- **Yahoo:** o gün −%13,7. Yahoo katsayıyı 1/2,5178 almış; olması gereken 1/2,9122. Yani yalnız iç kaynak kısmını (%151,78) uygulamış, kâr payından gelen %39,44'ü atlamış.
- **İş Yatırım:** o gün −%0,2.
- **Teorik kalan düzeltme:** 2,5178 / 2,9122 = **0,8646**.
- **Uygulanan katsayı:** 0,8650. Gözlenen getirilerden hesaplandı: 0,8633 / 0,998.
- **Fark:** %0,05. Değiştirilmedi; teorik değere geçmek kullanıcı kararı.
- **Durum:** olay doğrulandı, katsayı yaklaşık doğru.

### CANTE.IS — 26.01.2026, katsayı 0,8408

- **Yahoo:** −%15,9. Bu, günlük ±%10 fiyat sınırını aşar; dolayısıyla gerçek piyasa hareketi değildir.
- **İş Yatırım:** %0,0.
- **Olay:** %42,857 bedelli, 1 TL; sermaye 7 milyardan 10 milyar TL'ye. SPK onayı 29.01.2026 bülteninde. Hak kullanımı 03.02–17.02.2026 (KAP bildirimi, haberlerle doğrulandı).
- **Sonuç:** SPK onayı 29.01'de, yani 26.01'de hak kullanımı başlamış olamaz. Yahoo'nun 26.01'deki düşüşü veri hatası: düzeltme 6 işlem günü erken uygulanmış.
- **Katsayı kontrolü:** gerçek hak kullanım günü 03.02 alınırsa, teorik katsayı son hak içeren kapanışa (02.02) göre hesaplanmalı. Yahoo'nun 02.02 değeri 1,791 / 0,8408 = 2,130 TL'lik bir işlem fiyatına karşılık gelir. Bu fiyatla teorik katsayı (2,130 + 0,4286) / (1,4286 × 2,130) = **0,8408**, uygulanan katsayıyla aynı. 23.01 kapanışı (2,08 TL) kullanılırsa 0,8442 çıkar; o gün hak kullanım öncesi son gün olmadığı için doğru referans değildir.
- **Sınır:** 02.02'deki işlem fiyatı (2,130) ham veriden görülmedi, katsayıdan geri hesaplandı. Bu yüzden katsayı teoriyle *tutarlı*, ama bağımsız olarak kanıtlanmış değil.
- **Seviye karşılaştırması:** düzeltmeden sonra 19–23.01 kapanışları İş Yatırım ile birebir aynı (ör. 23.01: 1,749 / 1,749). Ancak İş Yatırım fiyatları da düzeltilmiş fiyatlardır, bu yüzden iki kaynak bağımsız sayılmaz. 26.01–02.02 arasındaki gerçek işlem fiyatı her iki seride de görülmüyor.
- **Düzeltmenin gerekçesi:** sonraki bedelli işlem değil, sınır ihlali ve iki kaynak arasındaki fark. Bedelli işlem yalnız büyüklüğün tutarlı olduğunu gösterir.
- **Tarih:** satır 26.01'de duruyor, gerçek tarih 03.02. Yahoo 26.01–02.02 fiyatlarını zaten düzeltilmiş seviyede verdiği için düzeltilmiş getiri serisi her iki tarihte de aynı çıkar. Satırı 03.02'ye taşımak bu günlere ikinci kez katsayı uygular; bu yüzden tarih değiştirilmemeli.
- **Durum:** olay ve tarih KAP ile doğrulandı; katsayı teoriyle tutarlı. Satırın 26.01'de durması Yahoo'nun hatasını telafi ediyor.

## Tek gün kapanış düzeltmeleri (635 satır) — uygulanmadı

Sınıflandırma ve gerekçe: docs/RESEARCH_LOG.md. Özet:
- 158 satır doğrulanmış veri hatası (05.01.2023).
- 35 satır fiyat türü uyuşmazlığı (09.04.2024 yarım gün).
- 442 satır belirsiz.

Satırların 448'inde düzeltilmiş kapanış o günün en düşük–en yüksek aralığının dışına düşüyor. Yani o günlerde mumun tamamı yanlış; yalnız kapanışı değiştirmek yapay mum üretir. Bu yüzden düzeltmeler varsayılan olarak kapalı kalıyor. Açılmaları kullanıcı onayı gerektirir.

## Değişmez yedek

- Kullanıcının fiyat deposu `python -m core.backup --market-db` ile yedeklenir.
- Yedek SQLite'ın kendi yedekleme yöntemiyle alınır; içinde SHA-256 manifesti bulunur.
- Haftalık otomatik yedekten sonra geri yükleme testi yapılır.
- İzole senaryo deneyi, deponun SHA-256 özetini çalışmadan önce ve sonra yazdırır; deneyin depoyu değiştirmediği böylece kanıtlanır.
