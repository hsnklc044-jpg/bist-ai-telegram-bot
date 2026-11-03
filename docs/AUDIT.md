# EVRE 1 — Güvenilirlik denetimi (04.11.2026, kod v0.99.40)

Kullanıcının 04.11.2026 güvenilirlik talimatının ilk adımı. Yalnız görülen kanıt yazıldı. Kullanıcının PC'si bu ortamdan görülmez. PC'ye ait son kanıt 04.11 00:17 tarihli `/durum` (v0.99.39) ve 03.11 23:29 geri yükleme testi çıktısıdır.

## Tamamlanma ölçütleri: bugünkü durum

| Ölçüt (hedef) | Bugün | Kanıt | Durum |
|---|---|---|---|
| Veri tazeliği (≥ %98) | %100, 1/1 seans | `/durum` SLO; ölçüm 03.11'de başladı | ölçülüyor, örneklem 1 seans: **yetersiz** |
| Veri doğruluğu (≥ %99) | ölçülemiyor | İş Yatırım ikinci kaynağı robots.txt nedeniyle kapalı (K-54). Son ölçüm 28.10'da: 116/117 tutarlı | ❌ **ikinci kaynak yok** |
| Yedekleme (%100) | %66,7 (2/3 seans) | 02.11'de yedek yok. 03.11 geri yükleme testi başarılı | ❌ |
| Kayıt bütünlüğü (%100) | 30.10 kaydı yok | `signal_log.csv` | ❌ geri doldurulamaz; 7 günlük pencereden 07.11'de çıkar |
| Rapor teslimi (≥ %99) | %100, 1/1 seans | `runs.csv`, ölçüm 03.11'de başladı | ölçülüyor, örneklem **yetersiz** |
| Bot çalışma süresi (≥ %98) | ölçülemiyor | ilk yaşam sinyali 03.11 15:14; en az 1 gün gerekir | ❔ birikiyor |
| Yüksek riskli modellerin bağımsız doğrulaması (hepsi) | 7/14 (aşağıya bakın) | `docs/validation/` | ❌ |
| Sanal işlem kayıtlarında açıklanamayan tutarsızlık (0) | defter boş | `signals.db` hiç işlem içermiyor | ölçülemiyor |

**Sonuç:** Sistem "tam güvenilir" olarak işaretlenemez. Gözlem süresi en az 4 hafta gerekiyor (20 seans). Bu süre içinde her SLO ölçülmeli ve hedefte kalmalı.

## Bulgular (önem sırasıyla)

1. **Model doğrulama sayısı yanlış (hesap hatası).**
   - `/durum` "6/11" diyor. `docs/validation/M15.md` var, ama karar satırı ("## 5. Karar: **kısıtlı kullanılabilir**") ayrıştırıcıya uymadığı için sayılmıyor.
   - Ayrıca yüksek riskli listede (`core/reports/validation.py` HIGH_RISK) M30 ML filtresi yok; oysa MODELS.md onu YÜKSEK sayıyor.
   - Sinyal onay katmanı (K-64) ve sanal sinyal defteri (K-60, K-67) MODELS.md'de hiç yok.
   - Doğru sayı: 14 yüksek riskli modelden 7'si doğrulandı (M11, M12, M14, M15, M16, M24, M28). Eksik olanlar M1, M5, M8, M27, M30, ayrıca yeni eklenen M31 (sinyal onay katmanı ve kart kuralı) ve M32 (sanal sinyal defteri).
   - ✅ v0.99.41'de düzeltildi.
2. **Yedek hatası Telegram'a bildirilmiyor.** 21:00'deki telafi işi (K-69) hata olursa yalnız log'a yazıyor. Talimat "başarısız yedeklemeleri otomatik raporla" diyor.
3. **İkinci veri kaynağı yok.** Veri doğruluğu ölçülemiyor.
   - Yeni bir kaynağa otomatik erişim, kullanım koşulları doğrulanmadan açılmaz; kullanıcının onayı gerekir.
   - Seçenek: kullanıcının elle indirdiği bir dosyayı içe aktarıp karşılaştırmak. Bu ağa erişim gerektirmez.
4. **Sinyal kaydı eksik alanlar içeriyor.** `signals.db` tarih, fiyat, olasılık, lot, stop ve hedefi tutuyor. Şunlar eksik:
   - gerekçe: tetik ve gösterge değerleri;
   - risk: stop gelirse kayıp, TL ve %;
   - geçerlilik süresi: kartın günü ve en çok 10 seans;
   - BIST 100 karşılaştırması: sinyal dönemindeki XU100 getirisi;
   - kazanan ve kaybedenlerin ayrı ölçümü.
5. **30.10 eksikleri: neden bulundu (04.11, kullanıcının PC çıktısı).**
   - Kanıt: eski klasörün `C:\Projeler\QuantBIST\logs\runs.csv` dosyası. 29.10 18:30 bayram, doğru. 30.10 18:30'da hiç çalışma yok: PC kapalıydı. 31.10 01:36'da (Cumartesi) gecikmeli çalışma `data_day=2026-10-28, holiday, hafta sonu` yazdı.
   - **Kod hatası:** Gecikmeli çalışmada 30.10 kapanışı depoda yoktu. Fiyat indirmesi o gün 30.10'u getirmedi; nedeni `daily_2026-10-31.log`'da. Rapor "bugün seans yok" kontrolünü eksik veri kontrolünden önce yaptığı için durumu "hafta sonu" diye kaydetti. Bu, dışarıdan izlemenin alarmını da susturdu.
   - ✅ v0.99.45: Önce eksik kapanış kontrol ediliyor ("stale"); hafta sonu ya da tatil ancak beklenen kapanış varsa yazılıyor.
   - 30.10 kaydı geri doldurulmayacak.
   - **02.11:** PC 18:30'da kapalıydı (çalışma yok). Telafi 03.11 12:40'ta raporu gönderdi. Yedek o gün alındığı için `quantbist_2026-11-03` adını taşıyor; Yedek SLO'su 02.11'i yedeksiz sayıyor, çünkü o gün gerçekten yedek alınmadı. Doğru sayım; düzeltilmeyecek.
   - **Tekrarı önleyen kontroller:** v0.99.33'ten beri bot 21:00'de günün yedeğini alıyor; v0.99.43'ten beri bunu Telegram'a bildiriyor. v0.99.45'ten beri eksik kapanış "hafta sonu" diye gizlenmiyor.
6. **02.11 yedeği:** O gün rapor çalışmadığı için yedek alınmadı. 21:00 telafisi (v0.99.33) artık bunu önlüyor.
7. **Windows zamanlanmış görevleri: doğrulandı (04.11 01:15, kullanıcının PC çıktısı).**
   - QuantBIST Guncelle: 01:11 sonuç 0; sonraki 07:40.
   - QuantBIST Gunluk Rapor: 03.11 18:30 sonuç 0; sonraki 04.11 18:30.
   - QuantBIST Bot: çalışıyor (267009 = görev çalışıyor).
   - Yalnız bu üç görev var; eski klasöre bağlı görev kalmamış.
   - Bot ortamında aider yok; `pip check` temiz.
   - `runs.csv` yeni klasörde 03.11'de başlıyor; öncesi eski klasörde.
8. **Temel veri:** İçe aktarma (`core.fundamentals.store --import`) ve formüller (K-57) var; veri yok. KAP otomatik çekme kullanım koşulları teyit edilene kadar kapalı (K-48). Bu kapalı kalacak.

## PC'de gereken kanıt (kullanıcıdan)

Bu komutlar yalnız okuma yapar:

```
cd C:\Projeler\QuantBIST-yeni
Get-Content logs\runs.csv | Select-Object -Last 15
Get-ChildItem logs\daily_2026-10-3*.log, logs\daily_2026-11-0*.log | Select-Object Name, Length, LastWriteTime
Get-ScheduledTask -TaskName "QuantBIST*" | Get-ScheduledTaskInfo | Select-Object TaskName, LastRunTime, LastTaskResult, NextRunTime
```

## İş sırası (döngü)

Kullanıcı 04.11'de bu sırayı resmi talimat yaptı (DECISIONS K-70). Aşağıdaki numaralar denetim sırasıdır; K-70'teki madde numaraları farklıdır.


1. ✅ v0.99.41: Model doğrulama sayımı düzeltildi; M30, M31 ve M32 envantere eklendi (bulgu 1).
2. ✅ v0.99.43: Yedek ve telafi hatalarında Telegram uyarısı (bulgu 2). Kabul ölçütü (20 seans %100 yedek, her hafta başarılı geri yükleme) gözlemle ölçülecek.
3. ✅ v0.99.46: Sinyal kaydı genişletildi: gerekçe, risk, geçerlilik, XU100 karşılaştırması, kazanan ve kaybeden ölçümü (bulgu 4). Kabul ölçütü (her işlem elle yeniden hesaplanabilir, açıklanamayan fark 0) defterde işlem birikince denetlenecek.
4. ✅ v0.99.42 (altyapı): Elle indirilen fiyat dosyası Yahoo'yla karşılaştırılıyor; özet "Veri doğruluğu" SLO'suna giriyor. Kabul ölçütü (20 seansta ≥ %99) için kullanıcının dosyası gerekiyor. Otomatik erişim açılmadı.
5. Eksik bağımsız doğrulamalar (M31, M32, M30, M1, M5, M8, M27), örneklem dışı ve sızıntı kontrolüyle; başarısız olan kısıtlı kalır.
6. `/durum` metninin sadeleştirilmesi; ölçülemeyen satırlar "ölçülemiyor" kalır.

---

# EVRE 0 — Doğrulanmış durum raporu (28.10.2026, kod v0.86.1 → v0.87.0)

Profesyonel geliştirme talimatının (28.10.2026) ilk adımı ve öz-denetim 6. Bu rapor yalnız **gerçekten görülen** kanıta dayanır. Kanıtı olmayan her şey "doğrulanamadı" olarak yazıldı; varsayım yok.

**Kanıtın nereden geldiği:**
- Depo ve bu bulut ortamı: kod, testler, belgeler, git geçmişi.
- GitHub Actions'ta gerçek veriyle çalışan iş akışları: fiyat indirme ve kalite tablosu, ikinci kaynak kontrolü, tatil takvimi, KAP taraması, paket güvenliği, felaket kurtarma tatbikatı.
- **Kullanıcının PC'si bu ortamdan görülmez.** Kişisel kayıtlar, sanal portföy, PC'deki fiyat veritabanı, yedekler ve loglar için son kanıt, kullanıcının 28.10 sabahı gönderdiği `/durum` ve kurulum çıktısıdır.

## Durum tablosu

| Alan | Durum | Kanıt |
|---|---|---|
| Kod ve testler | ✅ doğrulandı | 105 Python modülü, yaklaşık 18 bin satır, 91 test dosyası. Yerelde ve CI'da 818 test geçti, kapsam %91,95, ruff temiz (CI, commit 08bde54). Testler gerçek `data/` ve `logs/`'a dokunmuyor (yazma koruması). |
| Python ortamı ve bağımlılıklar | ✅ doğrulandı | Python 3.11 sabit (`pyproject.toml`). Tüm paketler `requirements.lock`'ta tam sürümle. |
| Paket güvenliği | ✅ doğrulandı (ilk kez bugün) | pip-audit: bilinen açık yok (Security çalışması 40676080251). Haftalık tarama daha önce hiç çalışmamıştı (bkz. D7). |
| Depoda gizli bilgi | ✅ doğrulandı | Tüm git geçmişinde bot token deseni 0. Geçmişteki 2 Healthchecks adresi test örneği (`test_ping`, `test_repo_secrets`), gerçek değil. |
| Tarihsel fiyat (OHLCV) kapsamı | ⚠️ kısmen | 209 sembol, 5 yıl (2021-10-25 – 2026-10-27, Actions 28.10). 207'si tam, 2'si boş: KPOWR, KERVT. XU100'de 3 eksik gün (biliniyor: 09.04.2024 yarım gün vb.). 4 hissede 1'er hatalı OHLC mumu (BASGZ, BIOEN, BOBET, PSGYO). SASA'da 151 gün sıfır hacim, PAHOL'da 6. |
| İkinci kaynak | ✅ doğrulandı | İş Yatırım'la son 30 gün: 118 hissenin 117'si tutarlı, 2574 hisse-gün; XU100 tutarlı. KPOWR kontrol edilemedi (iki kaynakta da yok). |
| Kurumsal işlem düzeltmeleri | ❌ eksik (D4) | `corporate_actions.csv`'de 16 satır var. 10 hissede **15 çözülmemiş ±%20 sıçrama** kayıtta yok: ADEL, ASUZU, BJKAS, CVKMD, EUREN, FENER, GOLTS, GSRAY, TSPOR, TUKAS. Haftalık inceleme yalnız son 14 güne baktığı için "yeni şüphe yok" diyor. |
| Sembol değişiklikleri | ✅ doğrulandı | Kod değişiklikleri eşleme tablosunda (`membership.py`, ör. KOZAA→TRMET 24.11.2025). KERVT (BIST 100 üyesi 2023-01 – 2023-07) Yahoo'da yok: geçmiş evrende 1 hisselik veri boşluğu. |
| Tarihsel endeks üyeliği | ✅ doğrulandı | `bist100_stable.csv` + `bist100_changes.csv` (344 değişiklik, kaynaklı). 23.10.2026 listesiyle 100/100. |
| Tatil takvimi | ⚠️ kısmen (D9) | 2026'nın 13 günü XU100 mumlarıyla tutarlı. Dosya yalnız 2026'yı kapsıyor; 2027 yıl bitmeden eklenmeli. Önceki yıllar mumlardan çıkarılıyor. |
| Finansal (temel) veri | ❌ yok | Sistemde temel veri hiç yok. Kaynak seçenekleri tasarımda (K-40); yeni görevin Aşama 3'ü bunu kuracak. |
| Veri lisansları | ⚠️ belgesiz (D5) | Yahoo (yfinance, resmi olmayan API) ve İş Yatırım (resmi olmayan uç nokta) için kullanım koşulları hiçbir belgede yazılı değil. |
| Felaket kurtarma | ✅ doğrulandı (CI'da) | `dr-drill` 27.10'da başarılı. PC'deki gerçek yedekler buradan görülmez. |
| Holdout ve geleceği görme | ✅ doğrulandı | Karne holdout'u iki yerde keser; kesim kaldırılırsa test kırmızı olur. Giriş ertesi açılışta. Sanal köprüde geleceği görme testi var. |
| Kişisel kayıtlar (defter, sanal emirler, izleme, alarmlar, canlı ölçüm, hesap değeri) | ✅ doğrulandı (PC, 28.10) | `/durum`: şema 5/5 uyumlu, kişisel dosyalar 5/5 sonuna kadar okundu. Yedekte equity_log 3, defter 1, sanal emir 1, fiyat alarmı 1, signal_log 351 satır, izleme listesi 1 kullanıcı. |
| Sanal portföy raporu | ✅ doğrulandı (PC, 28.10) | `/performans` çalışıyor: sanal hesap 27.10'da 99.924 TL; 23–27.10 −%0,1 (XU100 +%0,3); Taramalar "veri birikiyor", sanal köprü kapalı. |
| PC'deki fiyat veritabanı, loglar, yedek bütünlüğü (SHA) | ✅ doğrulandı (PC, 28.10) | `core.backup --test-restore` BAŞARILI, canlı dosyalara dokunmadı (quantbist_2026-10-28.zip; marketdb 27.10 bütünlük ok). Yedek 28.10 14:27, dışarıdan izleme açık. PC'deki fiyat kalite tablosu Actions'takiyle birebir aynı (28.10 14:32). |
| PC'de çalışan sürüm | ✅ doğrulandı (PC, 28.10) | v0.88.0 kurulu (14:30). Kurulumdan önce geçici kopyada 830 test geçti, ruff temiz; bot tek kopya. v0.88.1 PC'de kurulmadı: geçici kopyada 1 test kırıldı (D12). |

## Bulgular (öz-denetim 6)

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| D1 | **YÜKSEK** | /tara geçmiş karnesi, araştırmanın dışarıda bıraktığı hisseleri de kullanıyordu: çözülmemiş ±%20 sıçrama ya da kısa geçmiş (`tradable_symbols`). Örneğin FENER'in düzeltilmemiş −%78'lik veri sıçraması karnede −%78'lik bir işlem gibi sayılabiliyordu. Bu, 28.10'daki şablon karnelerini ve kullanıcı sayılarıyla karşılaştırmayı da etkiledi. | ✅ v0.87.0: karne aynı hisseleri dışarıda bırakıyor ve hangilerini bıraktığını yazıyor; eski önbellek geçersiz (`CARD_FORMAT=3`, `test_screen_card_jumps`). Şablon karneleri yeniden hesaplanacak. |
| D2 | ORTA | Canlı /tara listesi, abonelik ve sanal köprü yakın tarihte çözülmemiş sıçraması olan hisseyi eleyemiyor: CVKMD 03.08.2026'da −%61,9. 60 seanslık göstergeler bozuk çıkar. | ✅ v0.88.0: "veri sorunu" elemesi (252 seans) |
| D3 | ORTA | Göreli hacim, eksik (sıfır) hacmi 1,0 ile dolduruyor; işlem tutarı sıfır hacmi 0 TL sayıyor (SASA 151 gün). Talimattaki "sahte doldurma yok" kuralına aykırı. | ✅ v0.88.0 eleme: son 20 seansta 3+ gün sıfır hacim "veri sorunu" sayılır. Göreli hacim tanımı puan ve araştırma beklentilerine bağlı olduğu için değişmedi (ayrı karar). |
| D4 | ORTA | 10 hissede 15 çözülmemiş sıçrama kayıtta yok (yukarıda). Bu hisseler araştırmadan ve artık karneden tümüyle çıkıyor: geçmiş evrenin yaklaşık %5'i kayıp. | ✅ v0.88.1 + v0.91.0: 15 sıçramanın hepsi kaynaklı satır ya da kaynaklı mum istisnasıyla kapatıldı; KERVT→BESLR, KPOWR evrenden çıktı (K-50). İkinci kaynak doğrulaması DATA_CORRECTIONS'ta. |
| D5 | DÜŞÜK | Veri kaynaklarının lisansı ve kullanım koşulları belgesiz. | açık → Aşama 3 kaynak kararıyla birlikte DECISIONS'a yazılacak. |
| D6 | DÜŞÜK | Herkese açık git geçmişinde (eski commit 7ece232) Telegram sohbet kimliği ve 2 hisselik eski izleme listesi var. Kimlik bir parola değil; bot yalnız token sahibiyle konuşur ve izinli sohbet dışını reddeder. | kabul. Geçmişi yeniden yazmak kopyaları bozar ve varsayılan dal üzerinde kullanıcı kararıdır; kayıt altında. |
| D7 | DÜŞÜK | Haftalık paket güvenlik taraması eklendiğinden beri hiç çalışmamıştı (zamanı pazartesi, iş akışı salı geldi). | ✅ 28.10'da elle çalıştırıldı, temiz. Bir sonraki otomatik çalışma 02.11. |
| D8 | BİLGİ | Rapor evreninde (`universe.csv`) verisi olmayan KPOWR var; K-36 evren farkı (32 fazla, 14 eksik) sürüyor. | açık; karar Kasım sonu (K-36). |
| D9 | BİLGİ | Tatil dosyası yalnız 2026'yı kapsıyor. | açık: 2027 listesi Borsa İstanbul duyurusundan (genelde aralık) eklenecek. |
| D10 | BİLGİ | `likidite`/`islem_tl` bugünkü seansı da içeren 20 günlük ortalama. Talimat "önceki 20 tam seans" diyor. Kırılımda (`yuksek_20g`) ve göreli hacimde bugün zaten hariç. | ✅ v0.88.0: eleme tabanı önceki 20 seans, bugün hariç (K-45). Görüntülenen `islem_tl` alanı aynı kaldı. |

## Hesap tanımları talimata göre

| Tanım | Durum |
|---|---|
| RSI14 | Wilder (ta `RSIIndicator`). |
| ATR14 / ADX14 | Wilder. Hızlı sürüm kütüphaneyle bit bit aynı (test). |
| EMA kesişimi | Yalnız önceki kapanışta ilişki tersken. |
| Kırılım | `kapanis > max(yüksek[t-20..t-1])`; bugün hariç. |
| Göreli hacim | Önceki 20 (veya 10) seansın ortalamasına oran; bugün hariç. Sıfır hacim: D3. |
| Likidite | D10. |
| Sinyal → işlem | Kapanış sinyali ertesi açılışta işlenir. Karne, araştırma ve sanal köprü aynı. |

## Kullanıcıdan gereken kanıt (BENİM ADIMLARIM)

PC tarafını doğrulamak için 29.10 otomatik kurulumundan sonra şunları gönder:
1. `/durum` ekran görüntüsü (kişisel dosyalar, yedek, şema, sürüm).
2. `/performans` ekran görüntüsü (sanal portföy ve canlı ölçüm).
3. PowerShell'de `C:\Projeler\QuantBIST` içinde:

   ```
   .venv\Scripts\python.exe -m core.backup --test-restore
   ```

   Çıktıyı yapıştır. Bu komut son yedekleri geçici bir klasöre açar ve SHA kontrolüyle okur. Kişisel dosyalara dokunmaz; yalnız sonucunu yedek testi kaydına (`logs/`) bir satır olarak ekler.

**28.10 öğleden sonra geldi** (PC'deki yerel oturum çalıştırdı): yukarıdaki dört satır doğrulandı. SLO o an 6/7; eksik olan "kayıt bütünlüğü" yarım gün yanlış alarmıydı (D11).

## Sonradan bulunanlar (28.10.2026)

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| D11 | ORTA | Yarım günde (28.10) /durum, 14:30'dan itibaren "KRİTİK · rapor gitmedi", "fiyat 1 seans geride", "kaydı olmayan seans" ve SLO "kayıt bütünlüğü" uyarısı verdi. Kontroller mumun kesinleştiği saati (13:15 + 1:15) esas alıyordu; rapor ise 18:30'da çalışıyor. | ✅ v0.88.2: tek ortak fonksiyon `report_due_day` (18:30 + 1:15, yarım gün dahil, tatil hariç). Rapor, fiyat tazeliği, canlı ölçüm ve SLO penceresi onu kullanıyor (`test_report_due`). |
| D13 | ORTA | İş Yatırım `robots.txt` bütün botlara `/_layouts/` yolunu yasaklıyor; ikinci fiyat kaynağımız bu yolun altında (`crosscheck.URL`). Kullanım koşulları sayfası bulunamadı. | ✅ kapatıldı (K-54, v0.96.1): otomatik istek gönderilmiyor; Veri doğruluğu SLO'su "bilinmiyor". |
| D14 | ORTA | Borsa İstanbul telif bildirimi (arşiv `sources/2026-10-28_20-28-55/001.html`) bilgilerin yazılı izinsiz kopyalanmasını, uygulamaya konulmasını ve "ileride kullanılmak üzere" saklanmasını yasaklıyor. Ancak `data/bist100_changes.csv` BIST 100 değişikliklerini Borsa İstanbul duyurularına atıfla tutuyor ve `sources.yml` Borsa İstanbul sayfalarını herkese açık `research-results` dalına arşivledi. robots.txt `Allow: /` diyor. | açık: kullanıcı kararı. Seçenekler: yazılı izin istemek; değişiklik satırlarını aynı olguyu duyuran KAP bildirimlerine dayandırmak (KAP koşulu da teyit bekliyor); olduğu gibi bırakmak. Bu arada yeni Borsa İstanbul arşivi ve satırı yok; sektör dosyası kullanılmıyor (K-51). Git geçmişi yeniden yazılmaz. |
| D15 | YÜKSEK | Yahoo'nun şartları (arşiv `sources/2026-10-29_09-28-44/007.html`) hizmetten otomatik yollarla veri toplamayı açık izin olmadan yasaklıyor. Fiyat deposu yfinance ile Yahoo'dan geliyor. Ücretsiz ve otomatik çekmeye izin veren bir BIST gün sonu kaynağı bulunamadı. | kabul edilmiş risk (K-54): kişisel, ticari olmayan, günde bir toplu indirme; genişletilmez. Uyumlu çözüm lisanslı veri: kullanıcı kararı (ödeme). |
| D12 | ORTA | /tara'da karne, liste oturumu yazılmadan biterse kullanıcıya önce karne yerine "Önce /tara ile bir tarama yap." gidiyordu, liste sonra geliyordu. Yalnız yavaş PC'de görüldü; CI yeşildi. | ✅ v0.88.2: karne hemen hesaplanıyor, mesajı listeden sonra gidiyor (`asyncio.Event`). Test olaylarla sıralı, uykusuz; 50 tekrarda geçiyor. CI'a "yavaş makine" işi eklendi: tek meşgul çekirdek, iki rastgele test sırası. |

