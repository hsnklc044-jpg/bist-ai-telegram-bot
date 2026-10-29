# Model envanteri

Talimat F §F1 (28.10.2026). Sistemde sayı üreten ya da karar etiketi veren her "model" burada kayıtlıdır. Bu ilk envanterdir; F'nin geri kalanı Talimat 2'nin bitti ölçütünden sonra açılır (ROADMAP "F"). O işler şunlardır:
- bağımsız doğrulama raporları (`docs/validation/<model>.md`);
- değişiklik kontrolü;
- `/durum` izleme eşikleri;
- emeklilik.

**Alanlar:**
- **Amaç:** ne için var.
- **Girdi / çıktı:** ne okur, ne üretir.
- **Sahip:** kodu Claude yazar ve değiştirir; kararları kullanıcı verir. Kullanıcı kararı gereken değişiklik ayrıca belirtilir.
- **Varsayımlar ve sınırlar:** modelin dayandığı ve kapsamadığı şeyler.
- **Doğrulama durumu:**
  - `bağımsız doğrulanmadı`: yalnız geliştiricinin testleri var.
  - `ölçüldü`: gerçek veride bir ölçüm sonucu var, kaynağı yazılı.
  - `doğrulandı`: F2'deki ayrı oturum ya da alt ajan raporu var. Henüz hiçbir model bu durumda değil.
- **Son doğrulama:** son ölçüm ya da test kanıtının tarihi.
- **Risk:** yanlış olursa zarar, kullanıcının bu sayıya ne kadar dayandığına göre.
  - **YÜKSEK:** kullanıcının karar verirken baktığı sayılar (talimat F1), ya da kişisel kayıtları ve hesap rakamlarını değiştiren hesaplar.
  - **ORTA:** karar sürecine bilgi verir.
  - **DÜŞÜK:** yalnız açıklama ya da kayıttır.

Hiçbir model al/sat önerisi üretmez; çıktılar "kural çıktısıdır, öneri değildir".

## Özet tablo

| # | Model | Kod | Risk | Doğrulama durumu | Son kanıt |
|---|---|---|---|---|---|
| M1 | Teknik skor ve görünüm | `core/strategy/score.py`, `core/analytics/analyzer.py` | YÜKSEK | ölçüldü (Aşama 3, 3 hipotez red) | 27.10.2026 RESEARCH_LOG |
| M2 | Canlı ölçüm ve geçmiş referans | `core/reports/forward.py`, `core/backtest/expectations.py` | ORTA | bağımsız doğrulanmadı | testler, v0.94.0 |
| M3 | Sapma nedenleri | `core/reports/drift.py` | DÜŞÜK | bağımsız doğrulanmadı | testler |
| M4 | /tara motoru ve alanları | `core/screen/engine.py`, `fields.py`, `language.py` | ORTA | bağımsız doğrulanmadı | testler, v0.94.0 |
| M5 | /tara karnesi | `core/screen/card.py` | YÜKSEK | ölçüldü (şablon karşılaştırmaları) | 28.10.2026 RESEARCH_LOG |
| M6 | Eleme filtreleri | `core/screen/elimination.py` | ORTA | ölçüldü (D1 etkisi) | 28.10.2026 RESEARCH_LOG |
| M7 | Hazır şablonlar (15) | `core/screen/templates.py` | ORTA | ölçüldü (keşif, bütçe dışı) | 28.10.2026 RESEARCH_LOG |
| M8 | Destek/direnç seviyeleri | `core/analytics/levels.py` | YÜKSEK | ölçüldü: rastgeleden ayırt edilemedi | 28.10.2026 RESEARCH_LOG |
| M9 | Seviye anlamlılık ölçümü | `core/analytics/levels_study.py` | DÜŞÜK | bağımsız doğrulanmadı | testler, Actions 28.10 |
| M10 | Tarama sanal kitabı | `core/screen/virtual.py` | DÜŞÜK | bağımsız doğrulanmadı | testler |
| M11 | Pozisyon uyarıları | `core/alerts/rules.py`, `core/alerts/levels.py` | YÜKSEK | bağımsız doğrulanmadı | testler; PC 27.10 rapor elle sağlandı |
| M12 | Portföy riski (VaR, korelasyon, etkin pozisyon) | `core/alerts/portfolio.py` | YÜKSEK | bağımsız doğrulanmadı | testler; PC 27.10 rapor |
| M13 | Stres testi | `core/reports/stress.py` | ORTA | bağımsız doğrulanmadı | testler |
| M14 | Hesap ve defter (maliyet, K/Z, temettü, nakit) | `core/ledger/` | YÜKSEK | bağımsız doğrulanmadı | testler; PC 27.10 elle sağlandı |
| M15 | Fiyat düzeltmeleri (kurumsal işlem, mum istisnası) | `core/market/corrections.py` | YÜKSEK | ölçüldü (ikinci kaynak, 11.954 hisse-gün) | 28.10.2026 DATA_CORRECTIONS |
| M16 | Veri kalitesi ve ikinci kaynak | `core/market/quality.py`, `crosscheck.py`, `triage.py` | YÜKSEK | ölçüldü (Veri doğruluğu SLO) | 28.10.2026 |
| M17 | Geçmiş BIST 100 üyeliği | `core/market/membership.py` | ORTA | bağımsız doğrulanmadı (kaynaklı satırlar) | 27.10.2026 |
| M18 | Araştırma motoru (backtest, walk-forward, hipotez testi) | `core/backtest/` | ORTA | ölçüldü (ön kayıtlı H1–H3) | 27.10.2026 RESEARCH_LOG |
| M19 | Piyasa rejimi (araştırma) | `core/backtest/reliability.py` `market_regime` | DÜŞÜK | bağımsız doğrulanmadı | testler |
| M20 | Temel veri deposu | `core/fundamentals/store.py` | ORTA | bağımsız doğrulanmadı; veri yok | testler |
| M21 | SLO ölçümü | `core/reports/slo.py` | ORTA | bağımsız doğrulanmadı | PC /durum 28.10 |
| M22 | Sunucu kararı | `core/reports/server_decision.py` | DÜŞÜK | bağımsız doğrulanmadı; karar 13.11 | testler |
| M24 | Dört bazlı sonuç (nominal/reel/USD/nakit) | `core/market/macro.py` | YÜKSEK | bağımsız doğrulanmadı; elle hesaplanmış testler | testler, v0.95.0 |
| M25 | Piyasa rejimi ve sektör göreli gücü (/piyasa) | `core/market/regime.py` | ORTA | bağımsız doğrulanmadı; elle hesaplanmış testler | testler, v0.95.1 |
| M26 | Eleme filtresinin canlı ölçümü | `core/reports/forward.py` (`log_elimination_groups`, `elimination_lines`) | ORTA | bağımsız doğrulanmadı; elle hesaplanmış fark testi | testler, v0.96.0 |
| M27 | Senaryo şablonları (/senaryo) | `core/analytics/scenarios.py` | YÜKSEK | bağımsız doğrulanmadı; elle hesaplanmış testler; karne sırada | testler, v0.97.0 |
| M28 | Risk bütçesi (/risk) | `core/alerts/budget.py` | YÜKSEK | bağımsız doğrulanmadı; elle hesaplanmış iki hisseli testler | testler, v0.98.0 |
| M29 | Temel puanlar (/temel) | `core/fundamentals/scores.py` | ORTA | bağımsız doğrulanmadı; elle hesaplanmış testler; veri yok | testler, v0.99.0 |
| M23 | Rapor zamanı ve seans takvimi | `core/market/calendar.py` | ORTA | bağımsız doğrulanmadı | testler; tatil 29.10 PC kanıtı bekleniyor |

Planlı, henüz kodu olmayan modeller şunlardır. Envantere kod yazıldığı sürümde girerler.
- **C:** hisse sektörü (kaynak kararı bekliyor; reel/dolar getiri M24, rejim M25 olarak girdi).
- **D:** olay takvimi önem sınıfı.
- **E:** risk bütçesi.

## Ayrıntı

### M1 Teknik skor ve görünüm
- **Amaç:** Her hisseye günlük kapanışla bir teknik puan ve görünüm etiketi vermek. Etiketler: BUY/SELL ve güçlü sürümleri, nötr. `/analyze`, `/top` ve günlük rapor bunu kullanır.
- **Girdi:** düzeltilmiş günlük mumlar.
- **Çıktı:** RSI, MACD, EMA, hacim oranı, ATR; puan; eşiklerle etiket (`core/config/thresholds.py`); 2 ATR altı stop bilgisi.
- **Varsayımlar:** Göstergeler yalnız geçmişe bakar. Canlı analiz ve geçmiş skor aynı fonksiyondan gelir (`score_frame`); bu bir testle denetlenir.
- **Sınırlar:** Aşama 3'te üç ön kayıtlı hipotezin üçü de reddedildi. Skorun fazla getiri öngördüğüne dair kanıt yok. Etiket adları (BUY…) tarihseldir; kullanıcıya "görünüm" olarak gösterilir.
- **Doğrulama:** ölçüldü, sonuç red (RESEARCH_LOG 27.10). Holdout 02.11.2026'dan sonraki ileri veridir.
- **Risk:** YÜKSEK. `/analyze` ve rapor kararda bakılan sayılardır; emir doğurmaz.

### M2 Canlı ölçüm ve geçmiş referans
- **Amaç:** Botun söylediklerini sonuç bilinmeden kaydetmek. Kayıtlar ertesi açılış girişiyle 5/20/60 seans tutulmuş ve XU100'e karşı ölçülür. Geçmiş referansla karşılaştırma yapar.
- **Girdi:** `signal_log` (kişisel) ve fiyat deposu.
- **Çıktı:** `/performans`, cuma özeti, Kasım sonu canlı ölçüm kararı (H).
- **Varsayımlar:** Giriş ertesi açılıştır. Ufuklar çakıştığı için bağımsız dönem sayısı azdır.
- **Sınırlar:** 5 seanslık ufukta 10 bağımsız dönem yaklaşık 50 seans sürer. Kasım sonundan önce hüküm yoktur.
- **Doğrulama:** bağımsız doğrulanmadı; birim testleri var.
- **Risk:** ORTA.

### M3 Sapma nedenleri
- **Amaç:** Canlı sonuç referans aralığının dışına düşünce olağan nedenleri sınamak: birkaç hisse, tek gün, piyasa, veri.
- **Çıktı:** bulgu satırları (tahmin değil). K-30.
- **Risk:** DÜŞÜK.

### M4 /tara motoru ve alanları
- **Amaç:** Kullanıcının yazdığı kriteri her hissede aynı hesapla değerlendirmek.
- **Girdi:** fiyat deposu, XU100, eleme bilgileri.
- **Çıktı:** liste, sıralama alanları ve seviye alanları.
- **Varsayımlar:** Canlı analizle aynı hesap kullanılır (K-33). Ayrıştırıcıda eval/exec yoktur. Sıra alanları evren içinde hesaplanır.
- **Sınırlar:** Son 64 gün canlı hesaplanır. Geçmiş üyelik yalnız BIST 100 için vardır.
- **Doğrulama:** bağımsız doğrulanmadı. Liste ve karne eşdeğerliği testlerle denetlenir.
- **Risk:** ORTA.

### M5 /tara karnesi
- **Amaç:** Bir kriterin geçmişte ne yaptığının özeti. Ölçüm: gün ortalaması, 20 seanslık blok bootstrap, "tüm hisseler"le karşılaştırma, iki tür maliyet (K-35, K-39).
- **Varsayımlar:** Holdout karnede iki yerde kesilir. Giriş ertesi açılıştır. Eleme gün gün uygulanır.
- **Sınırlar:** Kanıt değildir (K-32). Aynı dönem çok kez denenir; çoklu deneme düzeltmesi yoktur, bunu başlık yazar.
- **Doğrulama:** ölçüldü (şablon karşılaştırmaları, RESEARCH_LOG 28.10).
- **Risk:** YÜKSEK. Kullanıcı bir kriteri buna bakarak sürdürebilir.

### M6 Eleme filtreleri
- **Amaç:** Hisse çıkarmak, asla seçmemek. Ölçütler: likidite, kurumsal işlem, aşırı hareket, veri sorunu (K-45).
- **Varsayımlar:**
  - Önceki 20 tam seansın TL hacmi kullanılır.
  - Kurumsal işlem yalnız kayıtlı satırlardan bilinir.
  - ATR kesimi en az 20 hisseyle yapılır.
- **Sınırlar:** Kaydı olmayan kurumsal işlem "bilinmiyor" sayılır, eleme yapılmaz. Dosya süreç başına bir kez okunur (Ö22).
- **Doğrulama:** ölçüldü (D1 etkisi, RESEARCH_LOG).
- **Risk:** ORTA.

### M7 Hazır şablonlar
- **Amaç:** Görevde verilen ve kaynakları yazılı 15 kriter. Her biri kendi reddedilmiş türünü gösterir (K-44, K-47).
- **Varsayımlar:** Eşikler sonuçlara bakılarak ayarlanmaz (YAPMA kuralı).
- **Doğrulama:** ölçüldü, keşif; araştırma bütçesi harcanmadı.
- **Risk:** ORTA.

### M8 Destek/direnç seviyeleri
- **Amaç:** Kapanmış mumlardan tekrarlanabilir teknik seviyeler. Yöntemler: fraktal kümeler, klasik pivot, 52 hafta, psikolojik, sma50/200 (K-49).
- **Çıktı:** `/seviye`, `/analyze` bloğu, rapor satırı, `/tara` alanları, `logs/levels_log.csv`, web.
- **Varsayımlar:**
  - Tepe ya da dip ancak 5 seans sonra kesinleşir.
  - Tavan/taban günleri sayılmaz.
  - Güç formülü sabittir.
- **Sınırlar:** Gerçek veride rastgele seviyelerden ayırt edilemedi: dönüş %31,3'e %31,0, fark +0,3 puan [−0,5; +1,1]. Her çıktı bu notu taşır.
- **Doğrulama:** ölçüldü (M9).
- **Risk:** YÜKSEK. Kararda bakılan bir sayıdır ve "destek" kelimesi güven telkin edebilir; not bu yüzden zorunlu.

### M9 Seviye anlamlılık ölçümü
- **Amaç:** M8'in rastgele seviyeden farkını tanımlayıcı olarak ölçmek. Hipotez değildir, bütçeden harcamaz.
- **Varsayımlar:** yaklaşma < 0,25 ATR; 5 seanslık ufuk; dönüş 1 ATR, kırılma 0,5 ATR; sabit tohum.
- **Risk:** DÜŞÜK.

### M10 Tarama sanal kitabı
- **Amaç:** Abone olunan bir taramanın listesini ölçüm amaçlı sanal pozisyonlarla izlemek. Varsayılan kapalı (K-43).
- **Risk:** DÜŞÜK. Gerçek ya da sanal hesaptan ayrıdır.

### M11 Pozisyon uyarıları
- **Amaç:** Açık pozisyonlarda kural uyarıları üretmek: stop yakınlığı, iz süren ATR stop, kapanış alarmı ve diğerleri.
- **Girdi:** defter, fiyat deposu, `core/config/alerts.py` eşikleri.
- **Çıktı:** rapor satırları, `alerts_log` (kişisel).
- **Varsayımlar:** Her kural yalnız `as_of`'a kadar olan kesin seansları görür. Alarm gün sonu fiyatıyla çalışır (K-26).
- **Sınırlar:** Gün içi fiyat yoktur. Gap ve taban nedeniyle stop garanti değildir.
- **Doğrulama:** bağımsız doğrulanmadı. PC'de ilk alarm (THYAO < 260) 28.10 akşamı gerçek veriyle denenecekti; kanıt bekleniyor.
- **Risk:** YÜKSEK.

### M12 Portföy riski
- **Amaç:** Pozisyon kurallarının göremediği riskleri göstermek: 1 günlük tarihsel VaR %95 (son yıl), yüksek korelasyonlu çiftler, etkin pozisyon sayısı.
- **Varsayımlar:** Geçen yılın hareketleri kullanılır. Fiyatı olmayan pozisyon sıfır risk sayılmaz, raporlanır.
- **Sınırlar:** Sektör yoğunlaşması yoktur, çünkü sektör verisi yok (C ile gelecek).
- **Risk:** YÜKSEK.

### M13 Stres testi
- **Amaç:** Açık pozisyonların depodaki en kötü 1/5/20 seanslık XU100 düşüşlerinde ne kaybettireceğini göstermek.
- **Varsayımlar:** Pencereler veriden bulunur. Fiyatı olmayan pozisyon XU100'ü alır ve "varsayım" olarak işaretlenir.
- **Risk:** ORTA.

### M14 Hesap ve defter
- **Amaç:** Gerçek ve sanal hesabın maliyeti, K/Z'si, temettüsü ve nakdi; sanal emir doldurma.
- **Girdi ve çıktı:** `ledger`, `paper_orders`, `equity_log` (kişisel).
- **Varsayımlar:**
  - Kayıtlar yalnız eklenir; yarım satır korunur (K-4).
  - Sanal emir dolumu idempotenttir (K-5).
  - Nakit getirisi TCMB politika faizinden alınır (`data/cash/`).
- **Doğrulama:** bağımsız doğrulanmadı. PC 27.10 raporunun rakamları elle sağlandı; SHA-256 kurulum öncesi ve sonrası aynı.
- **Risk:** YÜKSEK.

### M15 Fiyat düzeltmeleri
- **Amaç:** Kurumsal işlemleri fiyat geçmişine uygulamak ve bozuk mumları atmak ya da gerçek hareket olarak işaretlemek. İşlem türleri: bedelli, bedelsiz, bölünme, azaltım+bedelli.
- **Girdi:** `data/corporate_actions.csv` (29 satır), `data/candle_exceptions.csv`, `data/price_fix_approvals.csv`.
- **Varsayımlar:** Kaynaksız satır okunmaz. Oran fiyattan tahmin edilmez (K-50).
- **Sınırlar:** BJKAS 07.04.2025'te tek günlük yaklaşık 10 puanlık artık fark kalır (Ö23).
- **Doğrulama:** ölçüldü. İkinci kaynakla karşılaştırılan 11.954 hisse-günde açıklanamayan fark 2 gün.
- **Risk:** YÜKSEK. Her şey bunun üstüne kurulur.

### M16 Veri kalitesi ve ikinci kaynak
- **Amaç:** ±%20 sıçrama, sıfır hacim ve eksik seansları bulmak. Fiyatları İş Yatırım'la karşılaştırmak (Veri doğruluğu SLO'su, K-12).
- **Sınırlar:** İş Yatırım'ın robots.txt bulgusu var (D13, kullanıcı kararı bekliyor). İkinci kaynağın fiyatı depoya yazılmaz (K-21).
- **Doğrulama:** ölçüldü, 116/117 tutarlı (28.10).
- **Risk:** YÜKSEK.

### M17 Geçmiş BIST 100 üyeliği
- **Amaç:** Survivorship hatasını önlemek: bir hisse yalnız üye olduğu günlerde sayılır.
- **Sınırlar:** 2022 öncesi kaynaklı liste yok (K-16). Kod değişiklikleri takma ad tablosuyla izlenir (ör. KERVT→BESLR).
- **Risk:** ORTA.

### M18 Araştırma motoru
- **Amaç:** Ön kayıtlı hipotezleri sınamak. Yöntemler: backtest, walk-forward, Bonferroni düzeltmeli aralıklar, a4 kuralları (K-22, K-28).
- **Varsayımlar:** Holdout 02.11.2026'dan sonraki ileri veridir. Bütçe her döngüde 3 hipotezdir.
- **Doğrulama:** ölçüldü (H1–H3 red).
- **Risk:** ORTA.

### M19 Piyasa rejimi (araştırma)
- **Amaç:** Araştırma raporunda getiriyi XU100'ün 63 seanslık getirisine göre (±%5) yükselen, düşen ya da yatay diye ayırmak.
- **Not:** C'nin rejim tanımı ayrıdır (DECISIONS K-51). Bu tanım araştırma raporunda olduğu gibi kalır; ikisi karıştırılmaz.
- **Risk:** DÜŞÜK.

### M20 Temel veri deposu
- **Amaç:** Yayın tarihli temel veri. Bir değer yayınının ertesi gününden itibaren kullanılır. Ağ kodu yoktur.
- **Sınırlar:** Veri yok. KAP'tan otomatik çekme kullanım koşulu teyidine kadar kapalı (K-48).
- **Risk:** ORTA.

### M21 SLO ölçümü
- **Amaç:** Hedefleri yerel kayıtlardan ölçmek: rapor teslimi, ayakta kalma, tazelik, yedek, kayıt bütünlüğü, veri doğruluğu, kalite (K-11, K-15).
- **Risk:** ORTA. Yanlış "hedefte" bir sorunu gizler.

### M22 Sunucu kararı
- **Amaç:** K-23 ölçütünü 02.11–13.11 kayıtlarına uygulamak (K-31).
- **Risk:** DÜŞÜK. Karar kullanıcınındır.

### M23 Rapor zamanı ve seans takvimi
- **Amaç:** Hangi günün seans olduğunu ve raporun ne zaman gitmesi gerektiğini belirlemek (`report_due_day`, K-46). Yarım günleri ve tatilleri kapsar.
- **Sınırlar:** Tatil dosyası yalnız 2026'yı kapsar; 2027 tatilleri açık iş.
- **Risk:** ORTA. Yanlış takvim yanlış alarm ya da kaçan rapor demektir.

### M24 Dört bazlı sonuç
- **Amaç:** nominal TL sonucunu enflasyona, dolara ve nakde göre de göstermek (Talimat C, K-51, K-52).
- **Girdi:**
  - `data/macro/cpi.csv` ve PC'nin eklediği aylar (TÜİK verisi, TCMB tablosundan);
  - TCMB kur bülteni önbelleği;
  - politika faizi.
- **Çıktı:** günlük rapordaki hesap satırları; `/performans`'ta sanal hesap ve XU100.
- **Varsayımlar:**
  - TÜFE yayımın ertesi gününden itibaren kullanılır; ay içinde tahmin yoktur.
  - Kur, bülten günündeki döviz alış kurudur.
  - Nakit, araştırmanın kullandığı seriyle aynıdır.
- **Sınırlar:**
  - Geçmiş ayların yayım tarihi kuraldandır (iki kaynaklı istisna dışında).
  - Bir aydan kısa pencerede reel getiri nominale eşit çıkar.
  - Yahoo ile ikinci kaynak kur karşılaştırması yalnız uyarı verir (%1); değer değiştirmez.
  - 10 günden eski kur kullanılmaz ("kur yok"; Ö34).
  - Politika faizi serisi 23.06.2023'te başlar. Daha önce başlayan dönemde "nakde göre" boş kalır.
- **Doğrulama:** bağımsız doğrulanmadı. Elle hesaplanmış testler var (bir ay, bir yıl, kur, nakit). Yayımdan önce görünmeme testi var. Zincirlenen 12 ay, TÜİK'in yıllık değişimiyle tutarlı.
- **Risk:** YÜKSEK. Kararda bakılan bir sayıdır.

### M25 Piyasa rejimi ve sektör göreli gücü
- **Amaç:** piyasanın genel durumunu sabit bir etiketle ve dört ana sektörün XU100'e göre gücüyle göstermek (K-51).
- **Girdi:** XU100, o günün BIST 100 üyeleri (geçmiş üyelik), sektör endeks fiyatları.
- **Çıktı:** `/piyasa`. Kapı açılınca `/tara`'da `rejim` filtresi.
- **Varsayımlar:** eşikler sabittir (200 seans, 20/252 seans, yüzdelik 80, genişlik %50, en az 20 üye). Her gün yalnız kendi kapanışına kadarki veriyi kullanır.
- **Sınırlar:**
  - Etiket sinyal değildir.
  - Yüksek oynaklık diğerlerinden önce gelir.
  - Sektör endeks verisinin Yahoo'daki varlığı ilk PC çalışmasında doğrulanacak; yoksa "veri yok" yazar.
- **Doğrulama:** bağımsız doğrulanmadı. Elle hesaplanmış testler var (trend, yüzdelik, genişlik, göreli güç) ve geleceği görmeme testi var.
- **Risk:** ORTA.

### M26 Eleme filtresinin canlı ölçümü
- **Amaç:** M6 eleme filtresinin ileri veride ayırt edici olup olmadığını ölçmek (K-53).
- **Girdi:** bugünkü BIST 100, varsayılan eleme ayarları, fiyat deposu.
- **Çıktı:** `signal_log`'da "eleme" kaynağı; `/performans` "Eleme filtresi (canlı)".
- **Varsayımlar:** canlı ölçümle aynı giriş, ufuk ve XU100 karşılaştırması. Fark, gün gün iki grubun ortalamasından hesaplanır.
- **Sınırlar:**
  - Bağımsız dönem sayısı azdır; 20 seanslık sonuç aylar sürer.
  - Elenen grup küçüktür (birkaç hisse), bu yüzden en az 30 kayıttan önce sayı yok.
- **Doğrulama:** bağımsız doğrulanmadı. Kayıt tek seferlik, elle hesaplanmış fark ve rapor testleri var.
- **Risk:** ORTA.

## Yüksek riskli modeller (F3 sırası)

Bağımsız doğrulama F'nin kapısı açılınca bu sırayla yapılır. Sıra, kişisel kaydı ya da her gün okunan rakamı etkileyen modelden başlar:
1. M15 fiyat düzeltmeleri.
2. M16 veri kalitesi.
3. M14 hesap ve defter.
4. M11 pozisyon uyarıları.
5. M12 portföy riski.
6. M1 teknik skor.
7. M5 karne.
8. M8 seviyeler.
9. M24 dört bazlı sonuç.

F7 gereği, doğrulama raporu gelene kadar bu modellerin çıktısına "doğrulanmadı" etiketi eklenmesi F'nin uygulama işidir. Kapı açılmadan kod değişmez.
