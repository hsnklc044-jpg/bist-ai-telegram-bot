# Olgunluk merdiveni

Kullanıcının "olgunluk merdiveni" döngüsü (27.10.2026). CHARTER ve dönem değerlendirmesi kuralları geçerlidir. Bir seviye yalnız **kanıtla** sayılır: test adı, CI/Actions numarası, SLO değeri ya da PC gözlemi. Seviye atlanmaz.

**Şu anki seviye: S1 ÇALIŞIR (kapandı 27.10.2026).** Sıradaki: S2 GÜVENİLİR.

## S1 ÇALIŞIR — ✅ kapandı 27.10.2026

| Çıkış kanıtı | Kanıt |
|---|---|
| Günlük rapor çalışıyor | PC: 27.10 18:30 raporu otomatik kurulan sürümle gitti, sayılar elle sağlandı (runs.csv 18:30:01→18:30:39). 26.10 18:30 raporu gönderildi (`/durum` "Günlük rapor: son gönderilen 26.10.2026 kapanışı (26.10 18:30)", 27.10 16:19). Testler: `test_daily`, `test_report_numbers` (elle hesaplanan sayılar), `test_write_safety.SendRetryTest` |
| Bot çalışıyor | PC: tek bot, "QuantBIST Bot" görevi (27.10 10:15:20, iki süreç tek kopya); `/durum` "Telegram botu: çalışıyor (son sinyal 16:17)". Testler: `test_bot`, `test_bot_handlers`, `test_scheduler` |
| Yedek alınıyor ve doğrulanıyor | PC: `quantbist_2026-10-27.zip` (27.10 14:24 "5 dosya, doğrulandı"; 16:11). Geri yükleme testi PC'de 28.10 08:20 başarılı (`--test-restore`: 5 kişisel dosya + fiyat veritabanı, canlı dosyalara dokunulmadı). Testler: `test_backup`, `test_backup_restore`, `test_disaster_recovery` |
| /durum çalışıyor | PC: 27.10 14:26 (v0.48.1) ve 16:19 (v0.55.0) tüm kontroller SAĞLIKLI. Testler: `test_health`, `test_health_ops`, `test_slo` |
| Kod kalitesi | CI #130 (v0.55.3) ve #131 yeşil: ruff, 569 test, kapsam %91 kapısı |

## S2 GÜVENİLİR — sırada

| Çıkış kanıtı | Durum | Kanıt / eksik |
|---|---|---|
| SLO'lar art arda 4 hafta hedefte | ⏳ zaman | Ölçüm 27.10'da başladı (v0.51.0, K-15). En erken 24.11 haftası. Haftalık tablolar `docs/PERIODS/`'e yazılır |
| Dışarıdan izleme aktif ve yanlış/gerçek alarm testiyle doğrulanmış | ⏳ son gözlem | **Aktif 27.10 22:23** (PC, yerel otomasyon): .env'deki iki adres düzeltildi (önce örnek metin, sonra `.com/` sonrası boşluk → HTTP 400), bot ilk sinyali gönderdi, `/durum` "✅ SAĞLIKLI · Dışarıdan izleme: açık; bot sinyali 22:23". Bayram günü yanlış alarm olmaz: tatil çalışması başarılı sinyal gönderir (`test_ping`, daily.py). Bildirim kanalları 27.10 22:46'da denendi: Healthchecks "Test!" bildirimi hem Telegram'a (Healthchecks botu, 2/2 kontrol) hem e-postaya ulaştı. **Gerçek alarm tatbikatı başarılı (27.10, PC):** `.venv\Scripts\python -m core.infrastructure.ping --drill` → 22:53'te "QuantBIST rapor is DOWN (received a failure signal)" alarmı hem Telegram'a hem e-postaya ulaştı (zamanlama `35 18 * * 1-5`, Europe/Istanbul; bot kontrolü bu sırada UP) (ilk denemede düz `python` ile hiçbir şey gitmedi; doğru komut OPERATIONS §7'deki). 22:56'da `--recover` → "QuantBIST rapor is now UP. The downtime lasted 2 minutes, 26 seconds" (Total Pings 2). Alarm iki yönde de kanıtlandı. **Eksik (yalnız gözlem):** rapor kontrolünün ilk gerçek yeşili 28.10 18:30; 29.10 bayramında yanlış alarm olmaması |
| Açılış / uyku / ağ kesintisi senaryoları testli | ✅ | `test_bot.StartupNetworkTest` (gerçek PTB döngüsü), `test_scheduler.SleepWakeTest`, `test_daily.LateInternetTest`, `test_corrupt_files.LockedFileTest`, `test_corrupt_files.CutLastLineTest`, `test_runs` (saat değişimi) |
| İzole kopyada felaket kurtarma tatbikatı (sıfır makinede yedekten tam kurulum) başarılı | ✅ 27.10 | `dr-drill.yml` 3. çalışma **40551266369 başarılı** (v0.56.2, ~3 dk): temiz Windows'ta belgedeki zip → `setup.ps1` (kilitli paketler, ruff, 572 test) → yedek → `--restore` (3 dosya SHA-256 aynı) → Yahoo fiyat deposu → `--test-restore` → `/durum` "Kişisel dosyalar: 3 dosya sonuna kadar okundu". Rapor: research-results `drills/2026-10-27_20-33.txt`. Önceki iki çalışma iki gerçek hata buldu (v0.56.1, v0.56.2); tatbikatın `/durum`'u bir üçüncüsünü (K-20, v0.56.3). Aylık tekrar: her ayın 3'ü |
| Son öz-denetimde kritik/yüksek bulgu yok | ✅ 28.10 | Öz-denetim 5 (v0.73.0→v0.79.0, ROADMAP): 1 ORTA (karne likidite tabanı; düzeltildi, v0.80.0), 2 DÜŞÜK (biri düzeltildi), 2 BİLGİ; kritik/yüksek yok. Öz-denetim 4 (v0.64.0→v0.71.0, ROADMAP): 1 ORTA (sunucu kararında kapanan PC; düzeltildi, v0.72.0), 1 DÜŞÜK, 2 BİLGİ; kritik/yüksek yok. Öz-denetim 3 (v0.59.2→v0.63.0, ROADMAP): 1 DÜŞÜK (düzeltildi, v0.63.1), 2 BİLGİ; kritik/yüksek yok. Önceki: öz-denetim 2 (erken, v0.55.3→v0.59.0, ROADMAP): 2 ORTA (biri düzeltildi, v0.59.1), 1 DÜŞÜK, 1 BİLGİ; kritik/yüksek yok. Bir sonraki denetim de temiz çıkmazsa bu madde yeniden açılır |

## S3 BAĞIMSIZ — kapalı (S2'den sonra)

| Çıkış kanıtı | Durum |
|---|---|
| 30 gün kullanıcı müdahalesi olmadan çalışma (yerel otomasyon kurulumları + haftalık raporlar) | ⏳ sayaç 28.10'da başladı: güncelleme görevi yoktu, PC v0.59.0'da kalmıştı; 28.10 08:16 elle v0.66.0 kuruldu (639 geçti + 4 atlandı, ruff temiz), "QuantBIST Guncelle" görevi her gün 07:40 (K-27); v0.68.0'dan beri depodaki güncelleyiciyi çalıştırır, yalnız CI'ı yeşil sürümü kurar ve sonucu Telegram'a yazar (K-29; PC denemesi 28.10 09:05 başarılı). İlk kanıt: bir sonraki sürümün kendiliğinden kurulması ve "🤖 Otomasyon: KURULDU" mesajı |
| Süresi dolacak her şey için önceden uyarı (tatil takvimi, endeks listesi, paket sürümleri, token) | ✅ 27.10: tatil ✅, endeks ✅, Python ✅ (`test_health_ops.MaintenanceCalendarTest`, `QuarterlyReviewDateTest`); paket sürümleri (haftalık pip-audit) ✅; token ✅: Telegram token'ının süresi yok; iptal/sızma durumu [SPOF.md](SPOF.md) "Telegram token" ve DISASTER_RECOVERY §3'te (bot hemen durur, izleme alarmı) |
| Tek arıza noktası analizi (PC, internet, Yahoo, Telegram, GitHub) ve B planları | ✅ 28.10 | Analiz [SPOF.md](SPOF.md) (27.10, `test_disaster_recovery.SpofDocTest`); T-1 rapor metni diske ✅ v0.57.0; Y-1 ikinci kaynakla bilgi mesajı ✅ v0.58.0 (K-21). Son eksik (PC çökünce dışarıdan fark edilmesi) kapandı: Healthchecks 27.10 22:23'ten beri açık, tatbikatta DOWN (22:53) ve UP (22:56) Telegram'a ve e-postaya ulaştı. Yerel otomasyon satırı ✅ v0.68.0 (güncelleyici depoda, K-29). Kabul edilen tek risk: Healthchecks'in kendisi (ücretsiz servis; PC içinden 20:00 kontrolü ve `/durum` aynı işi görür) |
| Sunucu kararı SLO verisiyle, DECISIONS'ta | ⏳ ölçüt önceden yazıldı (K-23, 27.10): pencere 02.11–13.11, karar 14.11. Hesap kodda (v0.70.0, K-31): 13.11 raporu kararı kendisi yazar (`core.reports.server_decision`, `test_server_decision`); ara durum `python -m core.reports.server_decision`. Not: bot hedefi 7/24. Kullanıcı 27.10: PC gece kapanmıyor/uyumuyor; doğrulaması heartbeats.csv'deki "uyku/askı" saatleri (haftalık SLO tablosu) |

## S4 KANITLI ÖLÇÜM — kapalı

| Çıkış kanıtı | Durum |
|---|---|
| Canlı ölçüm ilk kararını vermiş (önceden belirlenmiş ölçüt) | ⏳ Kasım sonu |
| Backtest–canlı sapması nedenleriyle raporlanmış | kısmi: `/performans` ölçüm olgunlaşınca her görünüm için "geçmişle uyumlu" ya da "⚠️ geçmişten anlamlı sapma" yazar (geçmiş değer canlı %95 aralığın dışındaysa; v0.60.0, `test_forward.LiveVersusBacktestTest`). Nedenler artık sınanıyor (v0.69.0, K-30): sapan her görünümün altında "neden?" satırları. Sınananlar: en etkili 3 hisse olmadan, en uç gün olmadan, aynı süredeki XU100 getirisi (canlı/geçmiş), ölçülen hisselerin kurumsal işlemleri (`test_drift_reasons`). Eksik: ilk olgun sonuç (Kasım sonu) ve RESEARCH_LOG kaydı |
| Araştırma programı: deneme bütçesi + holdout + ön kayıtla bir tam döngü | kısmi: program yazıldı ([RESEARCH_PROGRAM](RESEARCH_PROGRAM.md), K-22: holdout 02.11.2026'dan ileri veri, döngüde 3 hipotez, 6 ayda bir). Aşama 3 (a3) ön kayıtlı ama holdout kuralından önce → kısmi. İlk tam döngü a4: **ön kayıt 28.10.2026** (H4 eşit ağırlık, H5 düşük işlem hacmi; RESEARCH_LOG "a4 ön kaydı", K-28), tarama en erken 27.04.2027. Holdout kodla korunuyor (v0.59.0, `test_holdout`) |
| Reddedilen fikir türleri özetlenmiş | ✅ 27.10: RESEARCH_LOG "Reddedilen fikir türleri — özet" (6 tür, 13 kural, ortak sınır) |
| Veri iki kaynakla doğrulanmış ve fark SLO'su tutuyor | kısmi: **ilk ölçüm 28.10 hedefte** (Research 28.10 09:50: 116/117 tutarlı, %0,85 ≤ %1; `crosscheck/latest.json`). Ölçüm hatası (Yahoo'nun henüz yayımlamadığı seans) v0.72.1'de, gerçek fark SKBNK v0.73.1'de düzeltildi; şüpheler artık kanıtlarıyla (v0.74.0, `triage.txt`). Eksik: "tutuyor" için ardışık haftalar (cumartesi çalışmaları) |

## S5 KARAR DESTEĞİ (gerçek para yok) — açılamaz

Yalnız S4'te bir kural istatistiksel ve maliyet sonrası anlamlı çıkarsa açılır. **Bugün böyle bir kural yok**: test edilen 9 kuralın (6 eski + Aşama 3'ün 3'ü) hiçbiri XU100'ü anlamlı geçmedi (RESEARCH_LOG). Gerçek para için kanıt yok.
