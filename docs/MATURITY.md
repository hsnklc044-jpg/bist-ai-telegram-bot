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
| İzole kopyada felaket kurtarma tatbikatı (sıfır makinede yedekten tam kurulum) başarılı | ✅ 27.10 | `dr-drill.yml` 3. çalışma **40551266369 başarılı** (v0.56.2, ~3 dk): temiz Windows'ta belgedeki zip → `setup.ps1` (kilitli paketler, ruff, 572 test) → yedek → `--restore` (3 dosya SHA-256 aynı) → Yahoo fiyat deposu → `--test-restore` → `/durum` "Kişisel dosyalar: 3 dosya sonuna kadar okundu". Rapor: research-results `drills/2026-10-27_20-33.txt`. Önceki iki çalışma iki gerçek hata buldu (v0.56.1, v0.56.2); tatbikatın `/durum`'u bir üçüncüsünü (K-20, v0.56.3). Aylık tekrar: her ayın 3'ü |
| Son öz-denetimde kritik/yüksek bulgu yok | ❌ | 27.10 öz-denetimi: 2 YÜKSEK (düzeltildi). Sonraki öz-denetim (10 sürüm sonra) temiz çıkmalı |

## S3 BAĞIMSIZ — kapalı (S2'den sonra)

| Çıkış kanıtı | Durum |
|---|---|
| 30 gün kullanıcı müdahalesi olmadan çalışma (yerel otomasyon kurulumları + haftalık raporlar) | ⏳ |
| Süresi dolacak her şey için önceden uyarı (tatil takvimi, endeks listesi, paket sürümleri, token) | ✅ 27.10: tatil ✅, endeks ✅, Python ✅ (`test_health_ops.MaintenanceCalendarTest`, `QuarterlyReviewDateTest`); paket sürümleri (haftalık pip-audit) ✅; token ✅: Telegram token'ının süresi yok; iptal/sızma durumu [SPOF.md](SPOF.md) "Telegram token" ve DISASTER_RECOVERY §3'te (bot hemen durur, izleme alarmı) |
| Tek arıza noktası analizi (PC, internet, Yahoo, Telegram, GitHub) ve B planları | ⚠️ analiz [SPOF.md](SPOF.md) (27.10, `test_disaster_recovery.SpofDocTest`); T-1 rapor metni diske ✅ v0.57.0; Y-1 ikinci kaynakla bilgi mesajı ✅ v0.58.0 (K-21). Kalan: PC'nin fark edilmesi izleme adreslerine bağlı |
| Sunucu kararı SLO verisiyle, DECISIONS'ta | ⏳ (≥1 hafta veri) |

## S4 KANITLI ÖLÇÜM — kapalı

| Çıkış kanıtı | Durum |
|---|---|
| Canlı ölçüm ilk kararını vermiş (önceden belirlenmiş ölçüt) | ⏳ Kasım sonu |
| Backtest–canlı sapması nedenleriyle raporlanmış | ⏳ |
| Araştırma programı: deneme bütçesi + holdout + ön kayıtla bir tam döngü | kısmi: program yazıldı ([RESEARCH_PROGRAM](RESEARCH_PROGRAM.md), K-22: holdout 02.11.2026'dan ileri veri, döngüde 3 hipotez, 6 ayda bir). Aşama 3 (a3) ön kayıtlı ama holdout kuralından önce → kısmi. İlk tam döngü a4, en erken Nisan 2027, kullanıcı onayıyla. Holdout kodla korunuyor (v0.59.0, `test_holdout`) |
| Reddedilen fikir türleri özetlenmiş | ✅ 27.10: RESEARCH_LOG "Reddedilen fikir türleri — özet" (6 tür, 13 kural, ortak sınır) |
| Veri iki kaynakla doğrulanmış ve fark SLO'su tutuyor | kısmi: v0.52.0 kodu; ilk özet 31.10 |

## S5 KARAR DESTEĞİ (gerçek para yok) — açılamaz

Yalnız S4'te bir kural istatistiksel ve maliyet sonrası anlamlı çıkarsa açılır. **Bugün böyle bir kural yok**: test edilen 9 kuralın (6 eski + Aşama 3'ün 3'ü) hiçbiri XU100'ü anlamlı geçmedi (RESEARCH_LOG). Gerçek para için kanıt yok.
