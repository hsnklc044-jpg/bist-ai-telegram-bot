# QuantBIST yol haritası ve açık sorunlar

Son doğrulanmış nokta, ardından önceliklendirilmiş işler. Her sürümden sonra
güncellenir; tamamlanan iş, kanıtıyla birlikte "Doğrulanmış durum" bölümüne taşınır.

## Kaldığım yer (27.10.2026, kod v0.48.0)

- **Son sürüm:** v0.48.0 (Aşama 3 H2 ve H3, TCMB politika faizli nakitle — plan değişikliği 1).
- **PC doğrulaması (27.10 09:09, v0.46.0):** 448 test geçti (Windows'ta 2 test atlandı), ruff temiz, paketler kilit dosyasıyla aynı. `/durum`'daki 12 kontrolün hepsi SAĞLIKLI; geri yükleme testi başarılı.
- **Bulunan sorunlar:**
  - `verify.ps1` sonda emoji yazdırırken çöküyordu (v0.46.1'de düzeltildi).
  - Bot açılırken `telegram.error.Conflict` hatası çıktı: aynı token'la iki bot aynı anda çalışıyordu (kullanıcının log'u, 27.10 09:21). v0.46.2'den itibaren bu durum log'a tek bir açık satırla yazılıyor.
- **PC doğrulaması (27.10 09:22, v0.46.1):** 450 test geçti (2 atlandı); `verify.ps1` hatasız tamamlandı.
- **Bot tek örnek (27.10 09:30):** arka plandaki eski bot (08:40) kapatıldı ve v0.46.1 ile yeniden başlatıldı. Başlangıçtan sonra `Conflict` satırı yok; yaşam sinyali 09:30:56'da yazıldı. Botu otomatik başlatan bir şey yoktu: bilgisayar yeniden başlarsa bot açılmayacaktı. Kullanıcı 27.10'da "QuantBIST Bot" görevini kurdu (oturum açılışında, tek kopya, çökerse yeniden başlatır); aynı ayarlar `scripts/register_bot_task.ps1` dosyasında.
- **Bot görev üzerinden (27.10 10:15):** görev yeniden başlatılınca elle açılmış eski bot da çalışır durumdaydı (iki bot); eski kopya kapatıldı. Şimdi tek bot, "QuantBIST Bot" görevinin başlattığı. Bot artık yalnız görevle başlatılır/yeniden başlatılır.
- **Aşama 3 kapandı:** H1, H2, H3'ün üçü de ön kayıtlı birincil ölçütü (Bonferroni %98,3 fazla getiri aralığı > 0) geçemedi, hepsi **red** (RESEARCH_LOG, 27.10). H2/H3 nakdi kullanıcı onaylı plan değişikliği 1 ile TCMB politika faizi. Haftalık araştırma üçünü kayıt için yeniden hesaplıyor; yeni hipotez yalnız yeni plan ve onayla.
- **Denetim:** D1–D14'ün hepsi kapandı (v0.45.1–v0.45.15).
- **Kullanıcı kararları (27.10) uygulandı:**
  - KCAER katsayısı 0,8646 (v0.45.13).
  - `/performans` "geçmiş" sütunu (v0.45.14).
  - Temettü kaydı (v0.45.15).
  - Tek gün kapanış düzeltmeleri kapalı kalıyor.
  - Dışarıdan izleme: Healthchecks.io kodu hazır (v0.46.0); adresler girilene kadar kapalı.
  - Sunucu: şimdilik PC'de kalınıyor; hazırlık docs/SERVER.md'de bekliyor.
- **Kullanıcıdan beklenen:**
  - PC'de elle yapılan değişiklikler (27.10, fiyat düzeltmesi koruması, OHLC incelemesi) yalnız PC'de; repoya alınmadan incelenmesi için fark dosyası (`quantbist_degisiklik.diff`).
  - Healthchecks.io hesabı ve iki adres (OPERATIONS.md §7).
- **Gözlem tarihleri:**
  - 28.10: yarım gün.
  - 29.10: tatil.
  - 30.10: cuma canlı ölçüm satırı.
  - 31.10: zamanlanmış cumartesi araştırması.
  - Kasım sonu: canlı ölçüm kararı. 5 seanslık ufukta 10 bağımsız dönem yaklaşık 50 seans sürer.

## Bağımsız denetim (27.10.2026, v0.45.0 üzerinde)

Kod baştan okundu. Aranan sorun türleri:
- hesap hatası,
- sessizce yutulan hata,
- tarih ve saat dilimi sorunu,
- aynı işi iki kez yapan kod,
- ölü kod.

Kritik bulgu yok. Satır satır kaynak ve risk tablosu: docs/RAKAMLAR.md. Yüksek önemli bulgular sırayla düzeltilir; her biri önce başarısız bir testle gösterilir.

| # | Önem | Bulgu | Etki | Durum |
|---|---|---|---|---|
| D1 | YÜKSEK | Gerçek hesabın "Günlük değişim" satırı ve "zirveden düşüş" uyarısı, hisse alımını kazanç, satışı kayıp sayıyor. Değer yalnız hisselerin piyasa değeri; arada para giriş-çıkışı ayrılmıyor | Yeni alım gününde "+%20" gibi sahte bir değişim görünüyor. Yarı satışta yanlış "hesap zirvesinden %50 aşağıda" uyarısı (yüksek önem) çıkıyor | ✅ v0.45.1 (`test_report_numbers.RealAccountFlowsTest`) |
| D2 | YÜKSEK | Rapor yalnız BIST 100 listesindeki hisselerin fiyatını güncelliyor. Listede olmayan bir hisseyi tutunca değer ve kâr/zarar eski fiyattan hesaplanıyor. Bekleyen bir sanal emir hiç dolmuyor ve bunu söylemiyor | Değer ve uyarılar eski fiyata dayanıyor. Uyarı ancak 5 gün sonra çıkıyor | ✅ v0.45.2 (`test_report_numbers.HeldOutsideUniverseTest`) |
| D3 | YÜKSEK | `/performans`'taki güven aralığı 20 ve 60 seanslık getirilerin üst üste bindiğini hesaba katmıyor. Ardışık günlerin 20 günlük getirileri neredeyse aynı ama bağımsız sayılıyor | Aralık olması gerekenden çok dar; "XU100'ü anlamlı şekilde geçiyor" kararı yanlışlıkla çıkabilir | ✅ v0.45.3 (`test_forward.SummaryTest.test_overlapping_horizons_do_not_make_noise_significant`) |
| D4 | ORTA | `data/corporate_actions.csv` içindeki bozuk bir satır yalnız log'a yazılıp atlanıyor | O hissenin geçmiş fiyatları düzeltilmeden kullanılıyor ve kimse fark etmiyor | ✅ v0.45.4 (`test_corrections.BadCorporateActionRowTest`) |
| D5 | ORTA | Canlı ölçüm kaydı yazılamazsa hata yalnız log'a gidiyor, raporda görünmüyor | O gün ölçümden düşüyor; `/durum` bunu ancak sonraki günlerde "kaydı olmayan seans" olarak gösteriyor | ✅ v0.45.5 (`test_daily.ScoreRecordingFailureTest`) |
| D6 | ORTA | İki ayrı mesaj bölücü var (`bot/common.split_message`, `daily.split_text`). Günlük raporun bölücüsü 4.000 karakteri aşan tek bir satırı bölmüyor | Çok uzun bir satır Telegram'da hata verir ve rapor gitmez | ✅ v0.45.6 (`test_daily.SplitLongLineTest`) |
| D7 | ORTA | Hesap değerleme mantığı üç yerde ayrı ayrı yazılmış: `daily.build_daily`, `service.portfolio_text`, `service._paper_value`. `/portfolio` fiyatın tarihini göstermiyor | Bir düzeltme bir yerde kalıp diğerlerinde eksik kalabilir; eski fiyat "son kapanış" gibi görünebilir | ✅ v0.45.7 (`test_report_numbers.PortfolioCommandTest`) |
| D8 | DÜŞÜK | `/analyze` skoru 2 yıllık, günlük kayıt 5 yıllık geçmişle hesaplıyor (EMA/RSI başlangıç farkı) | Seyrek de olsa bir puanlık fark ve farklı görünüm çıkabilir | ✅ sorun değil: 300 seride 2 ve 5 yıllık geçmiş aynı skoru, görünümü ve göstergeleri veriyor (`test_strategy_score.HistoryLengthTest`) |
| D9 | DÜŞÜK | Ölü kod: `market.data.load_last_price`, `load_snapshot`, `load_market`, `get_data_quality`; `indicators.is_bullish`, `is_bearish`, `is_neutral`, `strong_buy_signal`, `strong_sell_signal`, `indicator_score`; `watchlist.service.get_watchlist_details` | Bakım yükü; bu fonksiyonların hiçbiri çağrılmıyor | ✅ v0.45.8 (11 fonksiyon, 319 satır kaldırıldı; tüm testler geçiyor) |
| D10 | DÜŞÜK | Saat dilimi belirtilmemiş zamanlar: fiyat deposunun eşitleme zamanı, veri önbelleği, log dosyası adı | PC ve sunucu İstanbul saatinde olduğu için bugün doğru. Başka bir saat diliminde 15 dakikalık yenileme ve log adı kayar | ✅ v0.45.9 (`test_data_layer.StoreTest.test_times_with_and_without_time_zone_mix_safely`; testler UTC ve İstanbul saatinde geçiyor) |
| D11 | DÜŞÜK | Telegram mesaj sınırı UTF-16 birimiyle sayılıyor, kod Python karakteri sayıyor | 96'dan fazla emoji içeren bir parça sınırı aşabilir; bugünkü raporlarda olmuyor | ✅ v0.45.10 (`test_daily.SplitUtf16Test`) |
| D12 | DÜŞÜK | `/report` elle çalıştırılınca yeni uyarıları kayda geçiriyor. Aynı gün 18:30 raporu onları "🆕" olarak yeniden göstermiyor | Kullanıcı uyarıyı `/report` çıktısında zaten görmüş oluyor | ✅ v0.45.11 (`test_report_numbers.ManualReportAlertsTest`) |
| D13 | ORTA | Temettü kaydı yok. Defterde temettü satırı (`dividend`) bulunmuyor; temettü günü ham fiyat düşüyor ama nakde bir şey eklenmiyor | Sanal ve gerçek hesap getirisi temettü kadar eksik görünüyor; temettü günü "Günlük değişim" kayıp gösteriyor. Backtest (temettüye göre düzeltilmiş fiyat) ile sanal hesap tutarsız | ✅ v0.45.15, kullanıcı onayıyla (`test_ledger.DividendTest`, `test_report_numbers.DividendReportTest`). Sanal hesaba otomatik temettü yazılmıyor: temettü verisi yok |
| D14 | DÜŞÜK | "Günlük değişim" son hesap kaydına göre hesaplanıyor. PC bir veya birkaç gün kapalı kaldıysa satır birkaç günün toplamını gösteriyor ama "günlük" yazıyor | Yanıltıcı etiket; hesabın kendisi doğru | ✅ v0.45.12 (`test_report_numbers.ChangeLabelTest`) |

## Aşama 2: tamamlandı (PC'de doğrulandı, 27.10.2026)

Yazılım tarafı bitti. Testler `tests/` içinde, CI numarası her maddenin yayınlandığı
sürümün ana dalındaki çalışması. Son CI: **#66 (run 40413981373, 55e3384), 380 test**.
"PC" sütunu, kullanıcının bilgisayarında görülmüş kanıtı gösterir.

| Madde | Kanıt (test) | CI | PC |
|---|---|---|---|
| Envanter, arıza etkisi, kurtarma adımları | docs/OPERATIONS.md | #57 | — |
| Günlük doğrulamalı yedek (SHA-256 manifest) | `test_backup.BackupTest.test_backup_contains_existing_files_and_verifies`, `test_corruption_is_detected`, `test_rotation_keeps_newest_daily_backups` | #54 | ✅ 5 dosya, OneDrive (26.10) |
| Fiyat veritabanı anlık yedeği (SQLite backup API, bot yazarken) | `test_backup_restore.RestoreTest.test_snapshot_while_another_connection_writes`, `test_snapshot_rotation_and_daily_list_are_separate` | #54 | kod testli; PC'de çakışma gözlenmedi |
| İzole geri yükleme testi (haftalık, raporda) | `RestoreTest.test_restore_reads_every_file_and_leaves_live_files_alone`, `test_corrupt_backup_is_detected`, `test_unreadable_content_fails_the_test`, `WeeklyCheckInReportTest` | #54 | ✅ PC, `verify_report` 27.10: 6 dosya geçici klasörde okundu |
| Gerçek geri yükleme önce mevcut hâli yedekler | `test_backup.BackupTest.test_restore_round_trip_with_safety_copy` | #54 | ✅ kullanıcı provası, 5 dosya SHA-256 aynı (27.10) |
| Yedek ayrı fiziksel hedefte | `test_health_ops.BackupLocationTest` (3 test) | #66 | ✅ PC, `verify_report` 27.10: OneDrive klasörü, "Yedek" SAĞLIKLI |
| `.env` yedeklenmez, rapor çıktısında token/chat id gizli | `test_verify.RedactTest` | #64 | — |
| Yazma kilidi (rapor ile `/paper`, `/trade` çakışmaz) | `test_write_safety.LockedWritesTest` (3 test) | #54 | kod testli; PC'de çakışma gözlenmedi |
| Tek çalıştırma, çift rapor yok, eski kilit 1 saatte düşer | `test_runs.LockTest`, `OncePerDataDayTest` | önceki sürümler | ✅ 26.10 tek mesaj |
| Telegram yeniden deneme (ağ/5xx/429), yanlış token tekrar denenmez | `test_write_safety.SendRetryTest` (4 test) | #54 | — |
| Sağlık seviyeleri; doğrulanamayan asla SAĞLIKLI değil | `test_health.ReportTextTest.test_verdict_never_ok_with_unknowns`, `ReportCheckTest.test_no_records_is_unknown_not_ok` | #56 | ✅ PC, `verify_report` 27.10 |
| Veritabanı bütünlüğü, kilitli veritabanı uyarı sayılır | `test_health_ops.DatabaseTest` (2 test) | #57 | ✅ PC, `verify_report` 27.10 |
| Disk, veri şeması (yanlış sürüm), yaşam sinyali | `DiskTest`, `SchemaTest`, `HeartbeatTest`, `ReportWarningsTest.test_bot_down_shows_in_the_daily_report` | #56 | ✅ PC, `verify_report` 27.10 |
| GitHub araştırma başarısızlığı uyarısı | `test_health_ops.ResearchTest.test_states` | #56 | — |
| Eski veri uyarısı | `test_health.DataChecksTest.test_prices_current_and_behind` | önceki sürümler | — |
| Başarısız rapor bildirimi | `test_backup.DailyIntegrationTest.test_failed_report_is_announced_in_telegram`, `test_runs.OncePerDataDayTest.test_failure_is_recorded` | önceki sürümler | — |
| 20:00 kontrolü, önem seviyesi, tekrar etmeyen uyarı | `test_scheduler.ReportWatchTest`, `AlertDedupTest`, `SeverityTest` | #57 | ✅ PC, `verify_report` 27.10 |
| Tek komutla kurulum kanıtı | `test_verify` (6 test); `scripts/verify.ps1` Windows'ta denenmedi | #64 | ✅ PC, `verify_report` 27.10 (v0.46.1'de konsol düzeltmesi) |
| Testler ağa çıkmaz, gerçek `data/` ve `logs/`'a yazmaz | `test_health_ops.ResearchTest.test_tests_never_reach_the_network`; conftest oturum sonu kontrolü | #56 | — |

**Açık (yazılım dışı):**
- PC'de `verify.ps1` çıktısı ve `/durum` bekleniyor.
- PC kapalıyken çalışma ancak sunucuyla mümkün (bkz. sunucu hazırlığı).

## Doğrulanmış durum (27.10.2026; kod v0.46.1, kullanıcı PC'si v0.46.0)

İşletim, yedek ve kurtarma: docs/OPERATIONS.md.

| Bileşen | Durum | Kanıt |
|---|---|---|
| Kod ve bağımlılıklar | Doğrulandı | CI yeşil; kullanıcı PC'sinde v0.46.0 ile 448 test, paketler `requirements.lock` ile aynı (27.10 09:09) |
| Telegram botu | Doğrulandı | `/help` tek sürüm yanıtlıyor (26.10 14:11) |
| Zamanlayıcı | Doğrulandı | Windows görevi tek zamanlayıcı; 26.10 18:30 raporu zamanında geldi |
| Günlük rapor teslimi | Doğrulandı | 26.10.2026 kapanış raporu 18:30'da Telegram'a geldi, tek mesaj |
| Sanal emir dolumu (v0.28 alanları) | Doğrulandı | #1 THYAO 10 adet: açılış 260,25 + %0,05 kayma = 260,38; komisyon 2,60 TL; hesap 97.394 + 2.582 = 99.976 TL |
| Yedek ve geri yükleme | Doğrulandı | Günlük yedek 5 dosya (OneDrive). Kullanıcı provası (27.10, kopya üzerinde): ledger.csv bozuldu, paper_orders.csv boşaltıldı; `--restore` sonrası 5 dosya SHA-256 ile birebir aynı |
| `data/signal_log.csv` | Doğrulandı | 26.10 14:42 elle çalıştırma: 117 hisse kaydı |
| `logs/runs.csv` `sent` satırı, `/durum` | Doğrulandı | 26.10 18:30 `sent` satırı; `/durum` 12/12 SAĞLIKLI (verify_report 27.10). 20:00 kontrolü uyarı gerektiren bir durum olmadığı için henüz tetiklenmedi |
| Portföy "Risk:" satırı (v0.29) | Doğrulandı | Kullanıcı PC'si v0.35.0 raporunda görünüyor (27.10); etkin pozisyon sayısı hatası (1.498,7 yerine 1,0) kullanıcı tarafından bulundu, v0.36.1'de düzeltildi |
| Yarım gün / tatil davranışı | **Doğrulanmadı** | 28.10 yarım gün, 29.10 tatil |
| Cuma canlı ölçüm satırı | **Doğrulanmadı** | İlk görülme hedefi 30.10.2026 |
| Cumartesi araştırma iş akışı | Elle doğrulandı (pipefail ile çıktı dosyaları kontrol edildi, run 40377109448); zamanlanmış çalışma doğrulanmadı | İlk zamanlanmış çalışma 31.10 |
| İkinci kaynak kontrolü | Son 30 gün doğrulandı (116 tutarlı, XU100 tutarlı); 2022 sonrası tam tarama sürüyor | run 40377105196 |
| Test kapsamı | %90 satır (core + bot) | `coverage run -m pytest` |

## Bulgular

**İşletim**
- PC'de iki zamanlayıcı aynı anda çalışabilir: `scripts/register_daily_task.ps1` (Windows
  görevi, 18:30) ve `DAILY_REPORT_AT` (bot içi, 18:30). İkisi açıksa rapor iki kez gider ve iki
  süreç aynı anda `paper_orders.csv` / `ledger.csv` dosyalarını okuyup yazar: bekleyen bir sanal
  emir iki kez dolabilir. Kullanıcı PC'sinde Windows görevi kurulu çıktı (26.10); `DAILY_REPORT_AT`
  kaldırıldı. v0.22.0'dan itibaren kilit ve `logs/runs.csv` ikinci çalıştırmayı engeller.
- Bot içi zamanlayıcıda kaçırılan çalıştırma telafisi (misfire) ayarlanmamış: PC 18:30'da uykudaysa
  o günün raporu gitmez. Windows görevinde `StartWhenAvailable` var.
- Resmi tatillerde rapor yine çalışır ve önceki seansın verisini yeniden gönderir (kayıtlar tekrar
  yazılmaz, çünkü veri tarihine göre tekilleştirilir).
- Sistem sağlığı tek yerden görülemiyor: son rapor, son veri tarihi, son yedek, signal_log satır
  sayısı için bir komut yok.

**Araştırma**
- Düzeltildi (v0.24.0): `core.backtest.research` artık geçmiş BIST 100 üyeliğini kullanıyor; GitHub iş
  akışı eski üyelerin verisini indirmiyordu, bu yüzden önceki `--pit` sonuçları da eksik evrenle
  hesaplanmıştı (90/202 hisse dışarıda). Ayrıntı: docs/RESEARCH_LOG.md.
- Momentum walk-forward'un +%20 yıllık sonucu tek bir test penceresinden (+%140) geliyor; son
  pencere −%66,5. Pencere dağılımı ve güven aralığı raporlanmıyor.
- Aday kurallardan hiçbiri üç kapıyı geçmiyor (26.10 çalışması). Teknik skor (bot sinyali) yıllık
  +%7,5, XU100 +%14,6.
- Araştırma sonuçları yalnızca Actions özetinde (90 gün sonra silinir); hipotez ve sonuç kaydı yok.
- Veri geçmişi ~5 yıl (Yahoo); test dönemi ~3 yıl. Tek veri kaynağı.

**Veri**
- KPOWR verisiz; SASA'da 151 gün hacim eksik. CANTE (2026-01-26) ve KCAER (2024-11-28) bilinçli
  olarak düzeltilmedi.

**Test kapsamı boşlukları**
- `bot/watchlist.py` %28, `bot/portfolio.py` %34, `core/market/update.py` %32,
  `core/backtest/candidates.py` %22. PowerShell betikleri test edilmiyor.

## Öncelikli işler

Ölçüt sırası: güvenlik ve veri bütünlüğü → hesap doğruluğu → strateji doğrulama değeri →
kullanıcı faydası → sürdürülebilirlik → maliyet/risk.

| # | İş | Önem | Fayda | Uygulama riski | Modüller | Gerekli testler | Kabul kriteri |
|---|---|---|---|---|---|---|---|
| 1 | ✅ v0.22.0 (PC'de doğrulama bekliyor) — Tek çalıştırma güvencesi: rapor için dosya kilidi ve "bu veri günü için gönderildi" kaydı | Kritik | Çift rapor ve çift sanal dolum imkânsız olur | Düşük | `core/reports/daily.py`, `bot/scheduler.py` | Eşzamanlı iki çalıştırma; aynı gün ikinci çalıştırma; `/report` elle çalıştırma | İki süreç aynı anda başlasa da tek mesaj, tek dolum; `/report` yine çalışır |
| 2 | ✅ v0.23.0 (PC'de doğrulama bekliyor) — Sistem sağlığı: çalıştırma kaydı (`logs/runs.csv`), `/durum` komutu, kaçırılan rapor telafisi | Yüksek | Rapor gitmediğinde fark edilir; uyku/kapanma sonrası telafi | Düşük | `daily.py`, `scheduler.py`, `bot/` | Kaçırılan gün senaryosu; sağlık metni; veri yokken "bilinmiyor" (asla "sağlıklı" değil) | `/durum` son rapor, son veri tarihi, son yedek, signal_log satırı gösterir; uyanınca aynı gün rapor gider |
| 3 | ✅ v0.24.0 (sonuçlar: docs/RESEARCH_LOG.md) — Araştırmada istatistiksel doğrulama: research için PIT evren, pencere bazlı sonuç, blok bootstrap güven aralığı, çoklu deneme düzeltmesi | Yüksek | Rastlantısal sonuçların başarı gibi görünmesi engellenir | Orta | `core/backtest/research.py`, `reliability.py`, yeni test | Bilinen sıfır-beklentili seride CI sıfırı kapsar; PIT ile eski sonuçların karşılaştırması | Haftalık tablo her strateji için CI ve "anlamlı değil" etiketi gösterir |
| 4 | ✅ v0.25.0 (`research-results` dalı, `history.csv`, `docs/RESEARCH_LOG.md`) — Araştırma kaydı: `docs/RESEARCH_LOG.md` (hipotez, ön tanımlı ölçüt, sonuç, olumsuz sonuçlar dahil) ve haftalık sonuçların kalıcı saklanması | Yüksek | Süreklilik; veri gözetleme (snooping) izlenebilir | Düşük | `docs/`, `research.yml` | İş akışı çıktısı dosya olarak kalır | Her araştırma hipotezle başlar, sonuç tarihli kayıtlıdır |
| 5 | ✅ v0.26.0 (2026 takvimi; 2027 Aralık'ta eklenecek) — BIST takvimi: tatil/seanssız gün tespiti (yeni mum yoksa rapor "seans yok" der, yeniden göndermez) | Orta | Yanıltıcı tekrar raporu kalkar | Düşük | `daily.py`, `core/market/calendar.py` | Tatil günü simülasyonu; yarım gün (arife) mumu | Seanssız günde tek kısa bildirim veya hiç mesaj |
| 6 | ✅ v0.27.0 — Canlı ölçüm bütünlüğü: signal_log denetimi (tekrar, eksik gün, veri tarihi gecikmesi) ve `/performans`ta kayıt sağlığı | Orta | Canlı sonuçlara güven | Düşük | `core/reports/forward.py`, `core/signals_log.py` | Bozuk/tekrarlı log örnekleri | Eksik gün ve gecikmeler raporda görünür |
| 7 | ✅ v0.28.0 (kullanıcı onaylı, 26.10) — Sanal işlem kaydını zenginleştirme: emir gerekçesi/kaynağı, giriş anındaki risk, gerçekleşme koşulu (tavan/taban kilidi notu) | Orta | Her sanal işlem izlenebilir | Orta (dosya şeması değişir → onay gerekir) | `core/ledger/paper.py`, `book.py` | Eski dosyanın yeni şemayla okunması | Eski kayıtlar değişmeden okunur; yeni alanlar dolar |
| 8 | ✅ v0.29.0 (sektör verisi yok; sektör yoğunlaşması açık) — Portföy riski: yoğunlaşma, korelasyon ve likidite uyarıları (sektör verisi gerekirse ayrıca) | Orta | Risk tek hisse stop'undan genişler | Orta | `core/alerts/rules.py` | Sentetik portföylerle eşik testleri | Uyarı kuralları belgelenmiş ve testli; veri yoksa "hesaplanamadı" |
| 9 | ✅ v0.31.0 (İş Yatırım, getiri bazlı haftalık kontrol) — Veri kalitesi: ikinci kaynakla örneklem karşılaştırma, hacim eksikleri için uyarı | Orta | Tek kaynak riski azalır | Orta (ücretsiz kaynak sınırlı) | `core/market/` | Kaynak farkı tespiti | Fark eşiği aşan hisse raporlanır |
| 10 | ✅ v0.30.0 (hedef modüller %89–93; toplam %90) — Test boşlukları: bot komutları (watchlist, portfolio), `market/update`, `candidates` | Düşük-orta | Gerilemeler erken yakalanır | Düşük | `tests/` | — | Bu modüllerde kapsam ≥ %70 |

## Karar notları

- 2026-10: Teknik skor yatırım sinyali olarak sunulmaz; backtest'te XU100'ü geçmedi.
- 2026-10: KCAER/CANTE fiyat düzeltmesi yapılmadı (çift düzeltme riski). Sonra v0.34.0'da ikinci kaynakla eklendi.
- 2026-10-27 (kullanıcı kararları):
  - KCAER katsayısı teorik değere, 0,8646'ya çekildi (v0.45.13).
  - Tek gün kapanış düzeltmeleri kapalı kalıyor.
  - `/performans`'a "geçmiş" sütunu eklenecek.
  - Temettü kaydı (D13) eklenecek.
- 2026-10: Eski karar katmanı (AL/SAT etiketleri, AI modülleri) kaldırıldı (v0.20.0, kullanıcı onaylı).
- Gerçek emir entegrasyonu: yalnızca canlı ölçüm bir kuralı istatistiksel olarak kanıtlarsa ve açık onayla.
