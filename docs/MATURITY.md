# Olgunluk merdiveni

Kullanıcının "olgunluk merdiveni" döngüsü (27.10.2026). CHARTER ve dönem değerlendirmesi kuralları geçerlidir. Bir seviye yalnız **kanıtla** sayılır: test adı, CI/Actions numarası, SLO değeri ya da PC gözlemi. Seviye atlanmaz.

**Şu anki seviye: S1 ÇALIŞIR (kapandı 27.10.2026).** Sıradaki: S2 GÜVENİLİR.

## S1 ÇALIŞIR — ✅ kapandı 27.10.2026

| Çıkış kanıtı | Kanıt |
|---|---|
| Günlük rapor çalışıyor | PC: 27.10 18:30 raporu otomatik kurulan sürümle gitti, sayılar elle sağlandı (runs.csv 18:30:01→18:30:39). 26.10 18:30 raporu gönderildi (`/durum` "Günlük rapor: son gönderilen 26.10.2026 kapanışı (26.10 18:30)", 27.10 16:19). Testler: `test_daily`, `test_report_numbers` (elle hesaplanan sayılar), `test_write_safety.SendRetryTest` |
| Bot çalışıyor | PC: tek bot, "QuantBIST Bot" görevi (27.10 10:15:20, iki süreç tek kopya); `/durum` "Telegram botu: çalışıyor (son sinyal 16:17)". Testler: `test_bot`, `test_bot_handlers`, `test_scheduler` |
| Yedek alınıyor ve doğrulanıyor | PC: `quantbist_2026-10-27.zip` (27.10 14:24 "5 dosya, doğrulandı"; 16:11). Testler: `test_backup`, `test_backup_restore`, `test_disaster_recovery` |
| /durum çalışıyor | PC: 27.10 14:26 (v0.48.1) ve 16:19 (v0.55.0) tüm kontroller SAĞLIKLI. Testler: `test_health`, `test_health_ops`, `test_slo` |
| Kod kalitesi | CI #130 (v0.55.3) ve #131 yeşil: ruff, 569 test, kapsam %91 kapısı |

## S2 GÜVENİLİR — sırada

| Çıkış kanıtı | Durum | Kanıt / eksik |
|---|---|---|
| SLO'lar art arda 4 hafta hedefte | ⏳ zaman | Ölçüm 27.10'da başladı (v0.51.0, K-15). En erken 24.11 haftası. Haftalık tablolar `docs/PERIODS/`'e yazılır |
| Dışarıdan izleme aktif ve yanlış/gerçek alarm testiyle doğrulanmış | ⏳ kullanıcı + 🔧 | Kod v0.46.0/v0.49.1. Araç hazır (v0.56.0, `python -m core.infrastructure.ping --drill/--recover`, `test_ping.AlarmDrillTest`). Eksik: adresler (.env, BENİM ADIMLARIM), tatbikatın PC'de yapılması ve bir hafta yanlış alarm olmaması |
| Açılış / uyku / ağ kesintisi senaryoları testli | ✅ | `test_bot.StartupNetworkTest` (gerçek PTB döngüsü), `test_scheduler.SleepWakeTest`, `test_daily.LateInternetTest`, `test_corrupt_files.LockedFileTest`, `test_corrupt_files.CutLastLineTest`, `test_runs` (saat değişimi) |
| İzole kopyada felaket kurtarma tatbikatı (sıfır makinede yedekten tam kurulum) başarılı | 🔧 | `dr-drill.yml`: GitHub'ın temiz Windows makinesinde DISASTER_RECOVERY adımları. 1. çalışma (40513818221, 27.10) ❌: zip kurulumunda `setup.ps1` git yüzünden durdu → v0.56.1 düzeltti (`test_environment.SetupScriptTest`). 2. çalışma bekleniyor |
| Son öz-denetimde kritik/yüksek bulgu yok | ❌ | 27.10 öz-denetimi: 2 YÜKSEK (düzeltildi). Sonraki öz-denetim (10 sürüm sonra) temiz çıkmalı |

## S3 BAĞIMSIZ — kapalı (S2'den sonra)

| Çıkış kanıtı | Durum |
|---|---|
| 30 gün kullanıcı müdahalesi olmadan çalışma (yerel otomasyon kurulumları + haftalık raporlar) | ⏳ |
| Süresi dolacak her şey için önceden uyarı (tatil takvimi, endeks listesi, paket sürümleri, token) | kısmi: tatil ✅, endeks ✅, Python ✅ (`test_health_ops.MaintenanceCalendarTest`, `QuarterlyReviewDateTest`); paket sürümleri (haftalık pip-audit) ✅; token: Telegram token'ının süresi yok, ama geçersizleşirse (iptal) bot açılmaz ve izleme alarmı çalar — belgelenecek |
| Tek arıza noktası analizi (PC, internet, Yahoo, Telegram, GitHub) ve B planları | ❌ |
| Sunucu kararı SLO verisiyle, DECISIONS'ta | ⏳ (≥1 hafta veri) |

## S4 KANITLI ÖLÇÜM — kapalı

| Çıkış kanıtı | Durum |
|---|---|
| Canlı ölçüm ilk kararını vermiş (önceden belirlenmiş ölçüt) | ⏳ Kasım sonu |
| Backtest–canlı sapması nedenleriyle raporlanmış | ⏳ |
| Araştırma programı: deneme bütçesi + holdout + ön kayıtla bir tam döngü | kısmi: Aşama 3 ön kayıtlı, Bonferroni; holdout yoktu; veri uzatması engelli (K-16) |
| Reddedilen fikir türleri özetlenmiş | ❌ (RESEARCH_LOG'a özet) |
| Veri iki kaynakla doğrulanmış ve fark SLO'su tutuyor | kısmi: v0.52.0 kodu; ilk özet 31.10 |

## S5 KARAR DESTEĞİ (gerçek para yok) — açılamaz

Yalnız S4'te bir kural istatistiksel ve maliyet sonrası anlamlı çıkarsa açılır. **Bugün böyle bir kural yok**: test edilen 9 kuralın (6 eski + Aşama 3'ün 3'ü) hiçbiri XU100'ü anlamlı geçmedi (RESEARCH_LOG). Gerçek para için kanıt yok.
