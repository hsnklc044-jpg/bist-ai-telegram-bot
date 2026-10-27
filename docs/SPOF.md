# Tek arıza noktaları ve B planları

MATURITY S3. Sistemin dayandığı her dış parça: bozulursa ne durur, nasıl fark edilir, B planı ne, kimin işi. Olay bazında kesintiler (uyku, kilitli dosya, disk dolu…) [OPERATIONS §8](OPERATIONS.md)'dedir; burası parça bazında ve "uzun süre yoksa" sorusunu cevaplar. Durum: ✅ B planı var ve testli · ⚠️ kısmen · ❌ yok (açık iş).

| Parça | Bozulursa ne durur | Nasıl fark edilir | B planı | Durum | Kimin işi |
|---|---|---|---|---|---|
| **PC** (bot, rapor, kişisel kayıtlar) | Her şey: rapor, bot, yedek | Dışarıdan izleme (Healthchecks) `/fail` ya da sinyal gelmez → telefona e-posta | Yeni makinede yedekten kurulum: [DISASTER_RECOVERY](DISASTER_RECOVERY.md), temiz Windows'ta her ay tatbikat (`dr-drill.yml`, 27.10 başarılı). Kayıp en çok 1 gün (günlük yedek) | ⚠️ kurtarma ✅; **fark etme** izleme adreslerine bağlı (BENİM ADIMLARIM). Kalıcı çözüm sunucu kararı (S3, SLO verisiyle) | Sistem + Kullanıcı (.env) |
| **İnternet** | Fiyat inmez, rapor/bot mesajı gitmez | Log "No price could be downloaded (network?)", runs.csv `failed`, 20:00 kontrolü | Açılışta ~7 dk, raporda 1+2+4 dk yeniden deneme; bağlantı gelince sonraki çalışma telafi eder; eski veri güncel gibi sunulmaz | ✅ (`test_bot.StartupNetworkTest`, `test_daily.LateInternetTest`) | Sistem |
| **Yahoo** (yfinance, tek fiyat kaynağı) | Günlük rapor yeni veri olmadan gider; günlerce sürerse sinyaller ve canlı ölçüm durur | `/durum` "Fiyat verisi" ve "Veri tazeliği" SLO'su | Kısa kesinti: bekle. **Uzun kesinti / yfinance değişikliği: yok.** İş Yatırım bağlantısı (`crosscheck.fetch_isyatirim`) var ama yalnız doğrulamada kullanılıyor | ❌ açık iş Y-1: kapanışlar için ikinci kaynağa geçiş | Claude |
| **Telegram** | Rapor ve bot komutları ulaşmaz | runs.csv `failed`; 20:00 kontrolü (aynı kanaldan, o da gitmez); Healthchecks rapor sinyali `/fail` | 3 gönderim denemesi (`test_write_safety.SendRetryTest`). Rapor metni göndermeden önce `logs/reports/rapor_<gün>.txt`'ye yazılır; kesintide o günün raporu oradan okunur (`test_forward.ReportTextKeptTest`, v0.57.0) | ✅ | Sistem |
| **Telegram token** | Token iptal/sızma → bot açılmaz | Bot hemen durur (yanlış token yeniden denenmez); Healthchecks bot sinyali gelmez | [DISASTER_RECOVERY](DISASTER_RECOVERY.md) §3 "Token sızdı": BotFather'dan yeni token, .env. Token'ın süresi dolmaz | ✅ belgeli | Kullanıcı |
| **GitHub** | Yeni sürüm inmez (yerel otomasyon zip indiremez); haftalık araştırma, CI, tatbikat çalışmaz | Otomasyon mesajı "indirilemedi"; Actions sayfası | Çalışan sürüm aynen devam eder: bot ve rapor GitHub'a bağlı değil. Kod ve yedekler PC'de de var | ✅ (çalışma anında bağımlılık yok) | Sistem |
| **Yerel otomasyon** (`C:\Projeler\QuantBIST_otomasyon`, depoda değil) | Yeni sürümler kurulmaz; haftalık rapor ve `bekleyen_mesaj.md` gelmez | Telegram'da "🤖 Otomasyon" mesajları kesilir | Bot ve rapor otomasyondan bağımsız çalışır. Otomasyonun kendi yedeği kullanıcıda ([DISASTER_RECOVERY](DISASTER_RECOVERY.md) adım 9) | ⚠️ yedeği tatbikatta denenmedi | Kullanıcı/Otomasyon |
| **Healthchecks** (izleme servisi) | Alarm gelmez; sistem etkilenmez | — (servis kendi durum sayfası) | 20:00 bot kontrolü ve `/durum` aynı işi PC içinden yapar (PC kapalıysa yapamaz) | ⚠️ kabul edilen risk: ücretsiz servis, alarm dışında bağımlılık yok | — |
| **İş Yatırım** (ikinci kaynak) | Haftalık doğruluk kontrolü yapılamaz → "Veri doğruluğu" SLO'su bilinmiyor | Araştırma raporu "ikinci kaynak yanıt vermiyor" | Kontrol erken biter, rapor etkilenmez (`test_crosscheck`) | ✅ | Sistem |

## Açık işler (puan sırasıyla)

1. ~~T-1 Rapor metni diske~~ ✅ v0.57.0: `logs/reports/rapor_<gün>.txt` (kişisel veri içerir, `logs/` repoya girmez).
2. **Y-1 İkinci fiyat kaynağı** (doğruluk ×2; etki yüksek, olasılık düşük-orta, maliyet orta-yüksek): Yahoo uzun süre yoksa kapanışlar İş Yatırım'dan; hangi kaynaktan geldiği rapora yazılır, iki kaynak hiç karıştırılmadan.
3. **PC'nin fark edilmesi**: izleme adresleri (BENİM ADIMLARIM); sunucu kararı ≥ 1 hafta SLO verisiyle (S3).
