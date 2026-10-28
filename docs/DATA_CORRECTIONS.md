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

### KCAER.IS — 28.11.2024, katsayı 0,8646 (v0.45.13'ten önce 0,8650)

- **Olay:** %191,22 bedelsiz; sermaye 657,57 milyondan 1.915 milyon TL'ye. SPK onayı 21.11.2024 (bülten 2024/53), bölünme 28.11.2024.
- **Bileşenler:** Borsa İstanbul fiyat düzeltmesine göre %151,784 iç kaynaklardan, %39,440 kâr payından bedelsiz. Bölünme sonrası teorik fiyat 14,182 TL, yani önceki kapanış 41,30 TL.
- **Kaynaklar:** ikincil haber kopyaları (Midas, Rota Borsa, Borsanın Gündemi). KAP'taki özgün metne doğrudan erişilemedi.
- **Yahoo:** o gün −%13,7. Yahoo katsayıyı 1/2,5178 almış; olması gereken 1/2,9122. Yani yalnız iç kaynak kısmını (%151,78) uygulamış, kâr payından gelen %39,44'ü atlamış.
- **İş Yatırım:** o gün −%0,2.
- **Teorik kalan düzeltme:** 2,5178 / 2,9122 = **0,8646**.
- **İlk katsayı (v0.34.0):** 0,8650, gözlenen getirilerden hesaplanmıştı: 0,8633 / 0,998.
- **Değişiklik (v0.45.13, 27.10.2026):** kullanıcı kararıyla teorik değere, **0,8646**'ya geçildi. Fark %0,05; 28.11.2024 öncesindeki bütün KCAER fiyatları bu oranda değişir.
- **Geri alma:** `data/corporate_actions.csv` dosyasında katsayıyı 0.8650 yapmak.
- **Durum:** olay ve katsayı doğrulandı. Test: `test_corrections.test_kcaer_factor_is_the_missing_part_of_the_bonus`.

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

**Onay kapısı (v0.48.1, kullanıcının 27.10 PC çalışmasından):** `--price-fixes` ile verilen bir dosya yalnız `data/price_fix_approvals.csv` her satırını onaylıyorsa kullanılır.
- Onay satırı: `symbol,date,factor,approved,source,note`. Aynı sembol, tarih ve çarpan; `approved=true`; kaynak zorunlu (ör. İş Yatırım + KAP).
- Listede olmayan, onaysız ya da çarpanı farklı tek bir satır bile dosyanın tamamını durdurur.
- Araştırma raporu bu durumda "Fiyat düzeltmeleri uygulanmadı: ENGELLENDİ …" yazar ve düzeltmeli ölçümü yapmaz. Senaryolar yalnız A ve B'yi çalıştırır.
- Dosya bir kez geçici kopyaya alınır; kontrol ve yükleme aynı kopyadan yapılır. Hata olursa önceki durum korunur.
- Şu an listede onaylı satır yok; 635 düzeltmenin hepsi engelli. Bir testi bunu doğruluyor; bir satırı onaylamak, kaynağıyla birlikte bu dosyaya yazılan ve git geçmişinde görünen bir karardır.

## Değişmez yedek

- Kullanıcının fiyat deposu `python -m core.backup --market-db` ile yedeklenir.
- Yedek SQLite'ın kendi yedekleme yöntemiyle alınır; içinde SHA-256 manifesti bulunur.
- Haftalık otomatik yedekten sonra geri yükleme testi yapılır.
- İzole senaryo deneyi, deponun SHA-256 özetini çalışmadan önce ve sonra yazdırır; deneyin depoyu değiştirmediği böylece kanıtlanır.

## Düz mumlar: 27.06.2022 ve 16.12.2022 (kullanıcının OHLC incelemesi, 27.10.2026)

Kullanıcının PC'deki incelemesi 7 kritik kayıt buldu: açılış = en yüksek = en düşük, kapanış bu aralığın dışında. `crosscheck --inspect` ile İş Yatırım'a karşı bakıldı (Data check çalışması, `research-results` dalı `datacheck/2026-10-27_14-36.txt`):

| Kayıt | Kapanış (bizde / İş Yatırım) | Bizim yüksek–düşük | İş Yatırım yüksek–düşük |
|---|---|---|---|
| BIOEN 27.06.2022 | 7,64 / 7,65 (aynı) | 7,24 – 7,24 | 7,81 – 7,13 |
| BOBET 27.06.2022 | 5,80 / 5,80 (aynı) | 5,81 – 5,81 | 5,92 – 5,74 |
| MIATK 27.06.2022 | 2,50 / 2,50 (aynı) | 2,51 – 2,51 | 2,54 – 2,41 |
| PSGYO 27.06.2022 | 0,5393 / 0,5405 (aynı) | 0,5266 – 0,5266 | 0,5503 – 0,5266 |
| BASGZ 27.06.2022 | 11,28 / 11,22 (+%0,5) | 10,87 – 10,87 | 11,44 – 10,75 |
| KRVGD 16.12.2022 | 2,86 / 2,90 (−%1,2) | 2,86 – 2,86 | 2,93 – 2,65 |
| BERA 27.06.2022 (karşılaştırma) | 7,15 / 7,91 (−%9,6) | 7,15 – 7,15 | 7,91 – 6,95 |
| CLEBI 27.06.2022 (karşılaştırma) | 271,55 / 296,69 (−%8,5) | 271,55 – 271,55 | 298,23 – 270,18 |

- **Neden:** 27.06.2022'de Yahoo birçok hissede gün içi tek bir fiyatı açılış, yüksek ve düşük olarak bırakmış. Bazı hisselerde kapanış doğru (BIOEN, BOBET, MIATK, PSGYO), bazılarında o da yanlış (BERA, CLEBI). Komşu günler iki kaynakta birebir aynı. Yani sorun o güne özgü, kaynak tarafında.
- **ADESE 08.02.2023:** İş Yatırım'da da yok (iptal edilen seans). Bizde `drop_cancelled_sessions` ile zaten çıkarılıyor. Sorun yok.
- **Sonuçlara etkisi:** pratikte yok. Araştırma 2023-08-01'de başlıyor; o gün kullanılan en uzun pencere (200 seans) Ekim 2022'ye kadar gidiyor. 27.06.2022 bunun da öncesinde. KRVGD (16.12.2022) bu pencerenin içinde, ama 01.04.2022'de BIST 100'den çıktı ve geri girmedi; geçmiş üyelik evreninde hiç seçilemez.
- **Karar:** düzeltme uygulanmadı. Gerekirse `data/price_fix_approvals.csv` üzerinden, kaynağıyla, kullanıcı onayıyla yapılır.

## Şüpheli hisseler (ikinci kaynak, haftalık; v0.52.0)

- Haftalık araştırma, son 30 günü İş Yatırım ile karşılaştırır ve özeti `research-results` dalında `crosscheck/latest.json`'a yazar: kontrol edilen hisse sayısı, açıklanamayan farkı olanlar ("şüpheli"), ulaşılamayanlar.
- `/durum`'daki "Veri doğruluğu" hedefi bu özeti okur: şüpheli hisse oranı ≤ %1 ise hedefte; aşarsa hisseler isimle yazılır. Özet 8 günden eskiyse ya da okunamazsa "bilinmiyor".
- Araştırmada dışlama: `python -m core.backtest.research --exclude-suspects <latest.json>`. Rapor dışlanan hisseleri "İkinci kaynakta şüpheli, dışarıda" satırında adıyla yazar. Varsayılan çalıştırmada dışlama yoktur; bir dışlama, bir deneme sayılır (CHARTER G2).

## Haftalık kurumsal işlem şüphesi taraması (v0.52.1)

- Haftalık araştırma `python -m core.market.quality --recent 14` çalıştırır; çıktı `research-results` dalında `runs/<tarih>/corporate.txt` ve iş akışı özetinde.
- Kapsam: 2022'den beri BIST 100'e girmiş her hisse. Son 14 günde ±%20'yi aşan tek günlük hareket ("sıçrama": büyük olasılıkla düzeltilmemiş bedelsiz/bedelli/bölünme) ve günlük fiyat limitinin açıklayamadığı hareket ("limit aşımı": bedelli ya da temettü olabilir). `corporate_actions.csv`'de zaten olanlar ve piyasa geneli hareketler hariç.
- Hiçbir şey otomatik uygulanmaz. Her satır KAP'ta doğrulanır; doğrulanan, kaynağıyla birlikte `data/corporate_actions.csv`'ye ve buraya eklenir.
- **Kanıtlar yan yana (v0.74.0):** haftalık araştırma `python -m core.market.triage --days 14` çalıştırır (`triage.txt`). Her şüphe için: 30 gün içindeki KAP sermaye bildirimleri (bağlantı ve `kap.yml detail` numaraları) ve İş Yatırım'ın düzeltilmiş serisinde aynı günün hareketi. İkisi de varsa ("güçlü") önerilen satır yazılır. Hiçbiri uygulanmaz; KAP metni okunduktan sonra eklenir.
- KAP'taki özgün metin (v0.73.0): Actions → "KAP corporate actions" → Run workflow → `detail` alanına bildirim numaraları (ör. `1685136,1684593`). Metin `research-results` dalında `kap/<tarih>.txt`. Bildirim numarası KAP kontrol çıktısındaki bağlantının sonundaki sayıdır.

## KAP duyuruları (v0.62.0)

Her cumartesi araştırma çalışması `kap.txt`: son 14 günde evrendeki hisseler için KAP'ta yayımlanan sermaye artırımı/azaltımı ve kâr payı duyuruları. Sermaye işleminin `corporate_actions.csv`'de kaydı yoksa "⚠️ kayıtta yok" ve KAP bağlantısı yazılır. Satır, duyuru metnindeki oran ve hak kullanım günüyle elle eklenir (DECISIONS K-24); haftalık sıçrama taraması (`corporate.txt`) aynı işlemi fiyat tarafından yakalar.

## SKBNK %40 bedelli: satır 22.10'dan 19.10'a (v0.73.1, 28.10.2026)

- **Olay (KAP'ın kendi metni, bildirim 1685136, `kap.yml` detail ile alındı):** %40 bedelli, 1 TL; rüçhan hakkı kullanımı 22.10–05.11.2026, kayıt tarihi 23.10, SPK onayı 16.10.
- **Fiyat:** ham kapanış 16.10'da 4,89, 19.10'da 3,69. Kopukluk Yahoo'da ve İş Yatırım'da aynı gün, 19.10 (`research-results` `datacheck/2026-10-28_09-59.txt`). İş Yatırım'ın düzeltilmiş serisi düzeltmeyi 19.10'a koyuyor: katsayı 3,97/5,10 ≈ 0,778. Teorik katsayı (4,89 + 0,4) / (1,4 × 4,89) ≈ 0,773.
- **Sorun:** satır 22.10'daydı (rüçhan başlangıcı). Düzeltilmiş seride iki sahte hareket oluşuyordu: 19.10 −%24,6 (İş −%3,1) ve 22.10 +%15,7 (İş −%7,9). Kaynak: `datacheck/2026-10-28_10-01.txt`.
- **Düzeltme:** satır 19.10'a, yani fiyat kopukluğunun olduğu güne taşındı (projenin kuralı: satır sıçrama gününe konur). KAP tarihleri ve kanıt satırın notunda.
- **Doğrulama ✅:** `datacheck/2026-10-28_10-05.txt` (SKBNK, düzeltilmiş seri, 01.09–bugün): tutarlı, 40 hisse-günde açıklanamayan fark 0.

## ANELE 19–27.10.2026: veri doğru, düzeltme yok (28.10.2026)

- **Bulgu (kullanıcı, PC, /tara):** ATR %45,3 (1 ATR 4,17 TL, kapanış 9,19).
- **Kontrol:** `datacheck/2026-10-28_12-25.txt` (ham mumlar, İş Yatırım ile yan yana). 19–23.10 arası beş gün art arda yaklaşık −%10 (13,99 → 7,60), 26–27.10 iki gün yaklaşık +%10 (9,19). Bütün günler iki kaynakta da aynı; hiçbir hareket ±%10 limitini aşmıyor.
- **Sonuç:** veri gerçek. ATR, fiyat yüksekken oluşan gün içi aralıklardan geliyor. /tara bunu satırda uyarıyla yazar (K-36).

## FENER ve CVKMD bedellileri kayda girdi (v0.88.1, 28.10.2026; öz-denetim 6, D4)

Denetimde 10 hissede 15 çözülmemiş ±%20 sıçrama bulundu. Bunlardan bugünkü BIST 100'de olan ve son 252 seansta kalanlar önce ele alındı. Bu hisseler /tara'da "veri sorunu" olarak eleniyordu.

| Satır | Kaynak | Kontrol |
|---|---|---|
| FENER 23.06.2025, %400 bedelli, 1 TL | KAP 1452776 ve 1466238 (Actions `kap.yml` ile metni alındı): rüçhan 30.06–14.07.2025 | Fiyat kopukluğu −%78,6 |
| FENER 29.12.2025, %400 bedelli, 2 TL | KAP'ı aktaran haber (capital.com.tr): rüçhan 05.01–19.01.2026. KAP metni ayrıca alınmadı. | Kopukluk −%63,7; 2 TL ile tutarlı (1 TL olsaydı önceki kapanış 4,9 TL olmalıydı) |
| CVKMD 03.08.2026, %170 bedelli, 1 TL | KAP 1656455: rüçhan 05.08–19.08.2026. Fiyat, kullanılan 2,374 milyar TL nominal karşılığı 2,374 milyar TL fondan hesaplandı. | Kopukluk −%61,9 |

- Satırlar projenin kuralıyla Yahoo'daki sıçrama gününe yazıldı (BFREN, SKBNK gibi). Yahoo bu hisselerde düzeltmeyi rüçhan başlangıcından yaklaşık bir hafta önce uyguluyor.
- `--apply-suggestions` kullanılmadı: o, oranı kopukluktan tahmin eder ve kaynağı yoktur.
- **Doğrulama:** satırlar eklendikten sonra Actions `datacheck` ikinci kaynakla (İş Yatırım'ın düzeltilmiş fiyatları) karşılaştırır. **Sonuç (datacheck 40682879776, 28.10.2026 14:50):** 01.05.2025'ten bugüne iki hisse de İş Yatırım'la tutarlı. 748 hisse-gün karşılaştırıldı; açıklanamayan fark 0, ertesi gün düzelen tek gün kapanış hatası 1.
- **Kalanlar (açık):** FENER 09.12.2024 (%152,57 bedelli; fiyat doğrulanmadı), ADEL, ASUZU, BJKAS, EUREN, GOLTS, GSRAY, TSPOR, TUKAS. Bunlar bugünkü listede değil ya da sıçramaları 252 seanstan eski. Araştırma ve karne bu hisseleri bütünüyle dışarıda bırakmaya devam eder (FENER'in 2024 satırı da çözülene kadar).

## Veri borcu kapatıldı: 12 sıçrama, KERVT, KPOWR (v0.91.0, 28.10.2026; Özellik Talimatı A'nın giriş kapısı)

**Kurumsal işlemler** (`corporate_actions.csv`, her satır kaynaklı; Yahoo'daki kopukluk gününe yazıldı):

| Hisse | Satır | İşlem | Kaynak |
|---|---|---|---|
| ADEL | 02.01.2024 | %1000 bedelsiz | Fintables; asıl bölünme 04.09.2024. Yahoo 2024 öncesini düzeltmemiş: ikinci kaynakla 02.01.2024 sonrası birebir aynı |
| BJKAS | 03.07.2024 | %400 bedelli, 1 TL | haber |
| BJKAS | 07.04.2025 | %400 bedelli, lot başına 2 TL | haber (KAP metnini aktaran) |
| EUREN | 02.12.2024 | %176,32 bedelsiz | haber |
| FENER | 09.12.2024 | %152,57 bedelli, 1 TL | haber; fiyat KAP'tan değil, ikinci kaynakla doğrulanır |
| GSRAY | 23.12.2024 | %400 bedelli, 1 TL | aracı kurum duyurusu |
| GSRAY | 30.06.2025 | %150 bedelli, 1 TL | KAP 1453492, 1456031 |
| TSPOR | 09.09.2024 | %200 bedelli, 1 TL | KAP 1333938 |
| TSPOR | 19.06.2025 | sermaye %85,33 azaltımı + eş zamanlı %581,82 bedelli, 1 TL | KAP 1463632. Yeni satır türü `reduction_rights`: azaltım çarpanı `factor` sütununda |
| TUKAS | 03.02.2025 | %205,64 bedelsiz | haber |

**Mum istisnaları** (yeni dosya `data/candle_exceptions.csv`; ikinci kaynak: `datacheck/2026-10-28_18-55.txt`):
- **ASUZU 27.06.2022 `drop`:** Yahoo mumu bozuk (dört fiyat da 35,13; İş Yatırım'da kapanış 39,27). Mum atılır; iki seanslık +%19 hareket gerçektir.
- **GOLTS 15.04.2024 `real_move`:** Yahoo'da 09.04.2024 yarım günü yok. İş Yatırım'da 417,12 → 458,69 → 504,51, yani iki tavan. +%21 veri sıçraması değildir; kalite raporu ve "veri sorunu" elemesi onu saymaz.

**Kodlar:**
- **KERVT → BESLR:** kod 02.06.2025'te değişti (Kerevitaş → Besler Gıda; Borsa İstanbul duyurusu). Üyelik eşlemesine eklendi; fiyatlar BESLR koduyla indirilir. KERVT'in 2023'teki BIST 100 üyeliği artık verisiz değil.
- **KPOWR rapor evreninden çıkarıldı:** Yahoo, İş Yatırım ve resmî BIST 100 listelerinde yok; web aramasında böyle bir BIST kodu bulunamadı. Satırın kendi notu "teyit bekliyor" diyordu. Git geçmişinde duruyor, geri alınabilir (K-50).

**Doğrulama:** satırlar eklendikten sonra Actions `datacheck` bu hisseleri 2022'den bugüne İş Yatırım'ın düzeltilmiş fiyatlarıyla karşılaştırır. Sonuç bu bölüme eklenir.

