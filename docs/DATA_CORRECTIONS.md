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

- **Olay:** %191,22 bedelsiz sermaye artırımı (SPK onayı 21.11.2024). KAP'a doğrudan erişilemedi; doğrulama duyurunun ikincil kopyalarından yapıldı.
- **Yahoo:** o gün −%13,7. Yahoo katsayıyı 1/2,5178 almış; olması gereken 1/2,9122. Yani yalnız %151,78'lik kısmı uygulamış.
- **İş Yatırım:** o gün −%0,2.
- **Teorik kalan düzeltme:** 2,5178 / 2,9122 = **0,8646**.
- **Uygulanan katsayı:** 0,8650. Gözlenen getirilerden hesaplandı: 0,8633 / 0,998.
- **Fark:** %0,05. Değiştirilmedi; teorik değere geçmek kullanıcı kararı.
- **Durum:** olay doğrulandı, katsayı yaklaşık doğru.

### CANTE.IS — 26.01.2026, katsayı 0,8408

- **Yahoo:** −%15,9. Bu, günlük ±%10 fiyat sınırını aşar; dolayısıyla gerçek piyasa hareketi değildir.
- **İş Yatırım:** %0,0.
- **Olay:** %42,86 bedelli (1 TL). Kamuya açık hak kullanım başlangıcı 03.02.2026.
- **Katsayı kontrolü:** 23.01 kapanışı P = 2,08 TL ile teorik bedelli katsayısı (2,08 + 0,4286) / (1,4286 × 2,08) = **0,8442**. Uygulanan **0,8408**, iki kaynağın 26.01 farkından hesaplandı. Fark %0,4. Değiştirilmedi.
- **Seviye karşılaştırması:** düzeltmeden sonra 19–23.01 kapanışları İş Yatırım ile birebir aynı (ör. 23.01: 1,749 / 1,749). Ancak İş Yatırım fiyatları da düzeltilmiş fiyatlardır, bu yüzden iki kaynak bağımsız sayılmaz. 26.01–02.02 arasındaki gerçek işlem fiyatı her iki seride de görülmüyor.
- **Düzeltmenin gerekçesi:** sonraki bedelli işlem değil, sınır ihlali ve iki kaynak arasındaki fark. Bedelli işlem yalnız büyüklüğün tutarlı olduğunu gösterir.
- **Belirsizlik:** Yahoo düzeltmeyi neden 26.01'e koyduğu bilinmiyor. 26.01–02.02 arasındaki fiyat seviyeleri tartışmalı.
- **Durum:** miktar doğrulandı, tarih belirsiz.

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
