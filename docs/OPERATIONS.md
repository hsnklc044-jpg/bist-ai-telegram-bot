# QuantBIST işletim ve kurtarma

Bileşenler, arıza etkileri, korumalar ve kurtarma adımları. Durum: v0.38.0 (27.10.2026).

## 1. Envanter

| Bileşen | Yer | Bağımlılık | Arızada ne olur | Veri kaybı riski | Koruma |
|---|---|---|---|---|---|
| Uygulama (Python 3.11, `requirements.lock`) | `C:\Projeler\QuantBIST` | `.venv` | Bot ve rapor çalışmaz | Yok (GitHub'da) | `setup.ps1 -CheckOnly`: sürüm, paket kilidi, ruff, testler |
| Telegram botu | Windows görevi "QuantBIST Bot": oturum açılışında `pythonw main.py`, tek kopya (`scripts/register_bot_task.ps1`, 27.10.2026'da kuruldu) | `.env` (BOT_TOKEN, CHAT_ID) | Komutlar ve 20:00 kontrolü çalışmaz | Yok | 5 dk yaşam sinyali (`logs/heartbeat.txt`); kapalıysa günlük rapor ve `/durum` KRİTİK der. Çökerse görev 5 dk sonra yeniden başlatır (en çok 3 kez). İkinci kopya Telegram'da `Conflict` verir |
| Günlük rapor | Windows görevi "QuantBIST Gunluk Rapor", 18:30 | fiyat deposu, kişisel dosyalar, internet | Rapor ve canlı kayıt eksik kalır | Düşük (ertesi gün kendini tamamlar) | Kilit (tek çalıştırma), `logs/runs.csv`, hata bildirimi, Telegram yeniden deneme, 20:00 kontrolü |
| Fiyat deposu | `data/market.db` (SQLite) | Yahoo | Fiyatlar okunamaz | Orta: Yahoo yalnız son 5 yılı verir | Haftalık SQLite anlık yedeği (online backup API), `/durum` bütünlük kontrolü |
| İşlem defteri | `data/ledger.csv` | — | Portföy hesaplanamaz | **Yüksek** (yalnız bu PC'de) | Günlük doğrulamalı yedek, yazmalarda kilit |
| Sanal emirler | `data/paper_orders.csv` | defter | Bekleyen emir kaybolur | **Yüksek** | Günlük yedek, kilit, çift dolum koruması, v0.28 öncesi kopya |
| Canlı ölçüm kaydı | `data/signal_log.csv` | rapor | Ölçüm örneklemi bozulur | **Yüksek** (geri üretilemez) | Günlük yedek, bütünlük denetimi |
| Hesap değeri kaydı | `data/equity_log.csv` | rapor | Hesap geçmişi kaybolur | Orta | Günlük yedek |
| Risk uyarı kaydı | `data/alerts_log.csv` | rapor | Uyarı geçmişi kaybolur | Düşük | Günlük yedek |
| Takip listesi | `data/watchlist.json` | bot | Liste kaybolur | Düşük | Günlük yedek |
| Yapılandırma | `.env` | — | Bot başlamaz | Token Telegram'dan yeniden alınır | **Yedeklenmez** (gizli bilgi; uzak klasöre açık metin gönderilmez) |
| Şirket işlemi düzeltmeleri | `data/corporate_actions.csv` | — | Fiyatlar yanlış düzeltilir | Yok (git geçmişi) | Her satırda kaynak ve gerekçe; geri alma = satırı silmek |
| Tatil takvimi | `data/bist_holidays.csv` | — | Tatil eksik rapor sayılır | Yok (git) | Haftalık XU100 karşılaştırması |
| Araştırma sonuçları | GitHub `research-results` dalı | GitHub | Geçmiş karşılaştırma kaybolur | Düşük (git) | Dal geçmişi |
| GitHub iş akışları | `.github/workflows` | GitHub, Yahoo, İş Yatırım | Haftalık araştırma ve veri kontrolü yapılmaz | Yok | pipefail (çöken adım başarılı görünmez), `/durum` son çalışma kontrolü |
| Log kayıtları | `logs/` | — | Kanıt kaybolur | Düşük | Dönen log dosyası (5 × 5 MB) |

## 2. Yedekleme

- **Kişisel kayıtlar:** her günlük raporda `quantbist_YYYY-MM-DD.zip`. İçinde 6 dosya ve SHA-256 manifesti var; zip yazıldıktan sonra geri okunup doğrulanıyor. Son 30 gün tutuluyor (`BACKUP_KEEP`). Hedef `.env`'deki `BACKUP_DIR`, kullanıcıda OneDrive; böylece ayrı fiziksel hedef sağlanıyor. Rapor kilidi altında alındığı için dosyalar tutarlı bir noktayı yansıtıyor.
- **Fiyat deposu:** haftada bir `quantbist_marketdb_YYYY-MM-DD.zip`. SQLite online backup API ile alınıyor, bot yazarken bile tutarlı. Son 4 hafta tutuluyor.
- **Haftalık geri yükleme testi:** en yeni iki yedek geçici bir klasöre açılıyor ve her dosya kendi kodu ile okunuyor:
  - defterin yeniden hesaplanması,
  - sanal emirler,
  - takip listesi,
  - CSV'ler,
  - SQLite `integrity_check`.
  Canlı dosyalara dokunulmuyor. Sonuç raporda tek satır olarak görünüyor.
- **Elle kullanım:**
  - `python -m core.backup --list`: yedekleri listeler.
  - `python -m core.backup --test-restore`: geri yükleme testini çalıştırır.
  - `python -m core.backup --market-db`: fiyat deposunun anlık yedeğini alır.

## 3. Kurtarma senaryoları

| Senaryo | Beklenen en fazla kayıp | Geri dönüş | Yol |
|---|---|---|---|
| `ledger.csv` / `paper_orders.csv` bozuldu veya silindi | Son yedekten sonraki komutlar (en fazla 1 gün) | Dakikalar | Botu durdur → `python -m core.backup --restore <zip>`. Önce mevcut hâl `before_restore` olarak yedeklenir. Kullanıcı provası 27.10'da başarılı. |
| `market.db` bozuldu | Son anlık yedekten sonraki günler; Yahoo'dan yeniden inebilir | Dakikalar | `/durum` KRİTİK → botu durdur → `quantbist_marketdb_*.zip` içindeki dosyayı `data/` içine kopyala → `python -m core.market.update` |
| Bekleyen emir kayboldu | Aynı | Dakikalar | Yedekten geri yükle; dolum defterde varsa çift dolum koruması tekrar yazmaz |
| Sanal portföy tutarsız | — | — | `--test-restore` defteri yeniden hesaplar; tutarsızlık hata olarak görünür |
| Bilgisayar beklenmedik kapandı | Yarım kalan rapor | Ertesi açılış | Kilit 1 saatte geçersiz sayılır; Windows görevi açılışta kaçırılan raporu çalıştırır (26.10 06:47'de gözlendi) |
| Yarım kalan yedek | Yok | — | Önce `.tmp` dosyasına yazılır, doğrulanınca adı değiştirilir; doğrulanmayan yedek yok sayılır |
| Hatalı sürüm güncellemesi | Yok (kişisel dosyalar zip'te yok) | Dakikalar | Önceki commit'in zip'iyle aynı `robocopy` komutu (rapordaki geri dönüş bağlantısı) |
| Sürüm ve veri şeması uyuşmaz | Yok | — | `/durum` "Veri şeması" KRİTİK; fazla sütun sorun değil, eksik sütun güncellemeyi geri al demektir |
| İnternet ya da Telegram kesik | Günün raporu gecikir | Ertesi çalıştırma | 3 deneme; başarısızsa `runs.csv`'de `failed` ve 20:00 uyarısı. Geçmiş tarihli veri güncel gibi sunulmaz, rapor başlığı veri tarihini yazar |
| Bilgisayar 18:30'da kapalı | — | Açılışta | Windows görevi `StartWhenAvailable` ile çalışır. **Bilgisayar kapalıyken hiçbir yerel görev çalışmaz.** Kesintisiz çalışma için sunucu gerekir (aşağıda) |

**Üretim geri yüklemesi kullanıcı onayı ister.** Kod hiçbir zaman kendiliğinden geri yükleme yapmaz.

## 4. Hata bildirimleri

20:00 kontrolü ve `/durum` aynı kontrolleri kullanır. Durum dört seviyededir: SAĞLIKLI, UYARI, KRİTİK, BİLİNMİYOR. Kontrol yapılamadıysa durum BİLİNMİYOR olur, asla SAĞLIKLI gösterilmez.

Her bildirim şunları içerir:
- önem,
- tespit zamanı,
- etki,
- "Otomatik işlem: yok",
- yapılacak iş.

Aynı sorun 3 gün içinde tekrar gönderilmez. Çözülen bir sorun geri gelirse hemen yeniden bildirilir.

| Önem (KRİTİK durumda) | Kontroller |
|---|---|
| KRİTİK | Fiyat veritabanı bozuk, veri şeması eksik |
| YÜKSEK | Günlük rapor yok/başarısız, yedek 10 günden eski, canlı ölçüm kaydı, bot kapalı, disk |
| ORTA | Fiyat verisi eski, sanal hesap kaydı |
| DÜŞÜK | Tatil takvimi, GitHub araştırması |

UYARI durumundaki bir sorun bir seviye düşük sayılır. Örneğin kilitli veritabanı geçici bir durumdur ve YÜKSEK olarak bildirilir; bozuk veritabanı KRİTİK olarak bildirilir.

## 5. Güvenli güncelleme

1. Güncellemeden önce `python -m core.backup` ile yedek al.
2. Zip'i indir ve aç.
3. `robocopy ... /E /XF watchlist.json .env` ile kopyala. **`/MIR` kullanma**, çünkü kişisel dosyaları siler.
4. `setup.ps1 -CheckOnly` çalıştır. Beklenen: sürüm, `identical to requirements.lock`, `tests: OK`.
5. Bota `/durum` yaz; "Veri şeması" SAĞLIKLI olmalı.

Zip kişisel dosyaları içermez (`.gitignore`), bu yüzden kopyalama onları ezemez. Uygulamanın sürümü (`core/__init__.py`) ile veri şeması birbirinden ayrı izlenir: şema, `/durum`'daki zorunlu sütun kontrolüyle doğrulanır.

**Geri dönüş sınırı:** v0.45.15 ile defterde "temettü" (`dividend`) işlem türü geldi. Defterde temettü satırı varsa daha eski bir sürüm defteri okuyamaz ve satır numarasıyla hata verir. Böyle bir durumda geri dönmeden önce şunlardan birini yap:
- o satırları geçici olarak çıkar,
- ya da temettü satırı olmayan bir yedeği geri yükle (`python -m core.backup --list`).

## 6. Sunucu seçenekleri (karar kullanıcıda)

| Seçenek | Artı | Eksi |
|---|---|---|
| Bugünkü PC + Windows görevi | Ücretsiz, veriler sende | PC kapalıyken çalışmaz |
| Küçük bulut sunucu (Docker hazır, adımlar docs/SERVER.md) | Kesintisiz; yeniden başlarsa kaçan raporu telafi eder | Aylık ücret, kişisel veriler sunucuda (onay gerekir); yedekler haftalık PC'ye alınmalı |
| GitHub Actions'ta rapor | Ücretsiz | Kişisel dosyalar herkese açık depoda tutulamaz; **uygun değil** |

## 7. Dışarıdan izleme (Healthchecks.io)

Bilgisayar kapalıysa ya da internet kesikse 18:30 raporu ve 20:00 kontrolü kimseyi uyaramaz. Bunu dışarıdaki bir servis çözer: bot ve rapor ona düzenli olarak "çalışıyorum" sinyali gönderir. Sinyal zamanında gelmezse servis seni Telegram'dan ya da e-postayla uyarır.

**Kurulum.** Hesap ve adresler sende; kod adresleri yalnız `.env` dosyasından okur.

1. https://healthchecks.io adresinde ücretsiz hesap aç.
2. **"QuantBIST rapor"** kontrolünü ekle:
   - Schedule: `Cron`, `35 18 * * 1-5`
   - Time zone: `Europe/Istanbul`
   - Grace time: `1 hour`

   Rapor başarılıysa, tatildeyse ya da o gün zaten gönderildiyse servis "başarılı" sinyali alır. Hata verirse ya da yeni veri gelmediyse `/fail` sinyali gider.
3. **"QuantBIST bot"** kontrolünü ekle:
   - Period: `5 minutes`
   - Grace time: `20 minutes`

   Bot her 5 dakikada bir sinyal gönderir.
4. Integrations bölümünden Telegram'ı (ya da e-postayı) bağla.
5. İki kontrolün "Ping URL" adresini `.env` dosyasına yaz:
   ```
   HC_REPORT_URL=https://hc-ping.com/...
   HC_BOT_URL=https://hc-ping.com/...
   ```
6. Botu yeniden başlat. 5 dakika içinde "QuantBIST bot" kontrolü yeşile döner; ilk 18:30 raporundan sonra "QuantBIST rapor" da yeşile döner.

**/durum satırı ("Dışarıdan izleme"):**
- ℹ️ BİLGİ "kurulmadı": adresler yok; genel durumu değiştirmez, uyarı göndermez.
- ✅ "açık; bot sinyali SS:DD, rapor sinyali GG.AA SS:DD": iki adres var, son sinyaller ulaştı.
- ⚠️ UYARI: adreslerden biri eksik, son sinyal ulaşmadı ya da bot sinyali 20 dakikadan eski.
- Sinyal sonuçları `logs/monitoring.json`'da tutulur: yalnız zaman, ulaştı mı, `/fail` mı. Adres hiçbir yerde yazılmaz.

**Güvenlik:**
- Adresler gizlidir; bilen herkes sahte sinyal gönderebilir.
- `scripts\verify.ps1` çıktısında adresler gizlenir.
- Log dosyasına adresler yazılmaz.
- Testler gerçek servise asla sinyal göndermez.

**Arıza:** servise ulaşılamazsa rapor ve bot normal çalışmaya devam eder; log'a yalnız "Monitoring ping failed" yazılır.

**Yarım gün ve tatil:**
- Yarım günlerde rapor yine 18:30'da çalışır.
- Tatilde "tatil" kaydı başarılı sinyali sayılır, bu yüzden yanlış alarm çıkmaz.
- Takvime girmemiş bir tatilde rapor "yeni veri yok" diyerek `/fail` gönderir. Bu durumda alarm doğrudur: `data/bist_holidays.csv` dosyasına bakılmalı.

## 7b. Çalıştırma kayıtları (aranabilir)

Her günlük rapor çalıştırması `logs/daily_<tarih>.log` ve `logs/quantbist.log` dosyalarına tek satırlık bir özet yazar:

    RUN daily id=20261027-183001-4321 status=sent day=2026-10-27 duration=58s

- Tüm çalıştırmalar: `Select-String "RUN daily" logs\quantbist.log`
- Yalnız hatalar: `Select-String "status=failed" logs\quantbist.log`
- `status` değerleri: `sent`, `skipped` (o gün zaten gönderildi), `holiday`, `stale` (yeni veri yok), `busy` (başka çalıştırma sürüyordu), `failed`.

## 8. Kesintiler: ne olur, nasıl fark edilir, nasıl toparlanır, kimin işi

Her satırın arkasında bir test var (parantez içinde). "Sistem" = kod kendiliğinden; "Otomasyon" = PC'deki yerel otomasyon; "Kullanıcı" = sen.

| Kesinti | Ne olur (sistem ne yapar) | Nasıl fark edilir | Nasıl toparlanır | Kimin işi |
|---|---|---|---|---|
| Bot açılırken internet/DNS yok | ~7 dk artan aralıklarla yeniden dener (`bootstrap_retries=20`); yanlış token'da hemen durur (`test_bot.StartupNetworkTest`) | Log "Failed run number N of 20"; sonra bot kapanır | Görev 5 dk arayla 3 kez yeniden başlatır | Sistem; hepsi başarısızsa Otomasyon/Kullanıcı: `Start-ScheduledTask "QuantBIST Bot"` |
| PC 18:30'da uykuda/kapalı | Görev uyanınca çalışır (`StartWhenAvailable`) | Rapor geç gelir | Kendiliğinden | Sistem |
| Uyanınca internet geç (rapor) | Hiç fiyat inmezse 1+2+4 dk bekleyip dener (`test_daily.LateInternetTest`) | Log "No price could be downloaded (network?)" | 7 dk'da gelmezse "yeni veri yok", Healthchecks `/fail`, 20:00 uyarısı | Sistem; sonra Kullanıcı: `Start-ScheduledTask "QuantBIST Gunluk Rapor"` |
| PC 20:00'de uykuda | 20:00 kontrolü uyanınca, en fazla 4 saat gecikmeyle bir kez çalışır (`test_scheduler.SleepWakeTest`) | Uyarı mesajı geç gelir | Kendiliğinden | Sistem |
| Telegram 429 / 5xx / ağ hatası (rapor gönderimi) | 3 deneme (5 ve 20 sn ara) (`test_write_safety.SendRetryTest`) | runs.csv `failed`, 20:00 uyarısı | Sonraki çalışma | Sistem |
| Dosya Excel'de açık (rapor sırasında) | Rapor gider; "… kilitli" notu; o dosyaya yazılmaz; doldurulamayan sanal emir bekler (`test_corrupt_files.LockedFileTest`) | Raporun "Veri notları" | Dosyayı kapat; sonraki çalışma yazar | Kullanıcı (dosyayı kapatmak) |
| Dosya Excel'de açık (bot komutu) | İşlem yazılmaz | Bot: "… kilitli … İşlem kaydedilmedi" | Dosyayı kapat, komutu tekrar gönder | Kullanıcı |
| Disk dolu | Rapor yine gider (gönderim diske yazmaz); "… yazılamadı: disk dolu" notu (`test_corrupt_files.LockedFileTest.test_full_disk`) | Rapor notu; `/durum` "Disk" | Yer aç; sonraki çalışma yazar | Kullanıcı |
| Elektrik kesildi, kayıt yarım kaldı | Sonraki ekleme yeni satırdan başlar; yarım satır olduğu gibi kalır (`test_corrupt_files.CutLastLineTest`) | Dosya adı + satır numarasıyla uyarı; "Kayıt sağlığı" | Yarım satırı sil ya da `python -m core.backup --restore` | Kullanıcı |
| Rapor yazılırken PC kapandı | Kilit 1 saat sonra geçersiz; dolum tekrar yazılmaz (`test_runs`) | runs.csv'de o çalışma yok | Açılışta görev çalışır | Sistem |
| Saat geri alındı (saat eşitleme, yanlış saat dilimi) | "Gelecekten" kalan kilit geçersiz sayılır; tüm saatler İstanbul'a göre hesaplanır (`test_runs…clock_change`, `test_data_layer` saat dilimi) | — | Kendiliğinden | Sistem |
| Aynı anda iki rapor çalıştırması | Kilit ikinciyi durdurur; aynı veri günü iki kez gönderilmez (`test_runs`, `test_write_safety`) | runs.csv `skipped` | Kendiliğinden | Sistem |
| İki bot birden | Telegram ikincisini reddeder; log'a tek satır | Log "aynı anda iki bot çalışıyor" | Elle açılan pencereyi kapat | Kullanıcı/Otomasyon |
| Yahoo erişilemez | Eski veri güncel gibi sunulmaz; rapor veri tarihini yazar | `/durum` "Fiyat verisi" | İnternet gelince kendiliğinden | Sistem |
| İş Yatırım (ikinci kaynak) yanıt vermez | 3 hisse üst üste başarısızsa kontrol durur; adımın 20 dk sınırı (`test_crosscheck`) | Araştırma raporu "ikinci kaynak yanıt vermiyor" | Gerekmez | Sistem |
