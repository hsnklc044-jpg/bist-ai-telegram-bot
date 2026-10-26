# QuantBIST işletim ve kurtarma

Bileşenler, arıza etkileri, korumalar ve kurtarma adımları. Durum: v0.38.0 (27.10.2026).

## 1. Envanter

| Bileşen | Yer | Bağımlılık | Arızada ne olur | Veri kaybı riski | Koruma |
|---|---|---|---|---|---|
| Uygulama (Python 3.11, `requirements.lock`) | `C:\Projeler\QuantBIST` | `.venv` | Bot ve rapor çalışmaz | Yok (GitHub'da) | `setup.ps1 -CheckOnly`: sürüm, paket kilidi, ruff, testler |
| Telegram botu | `python main.py` (açık pencere) | `.env` (BOT_TOKEN, CHAT_ID) | Komutlar ve 20:00 kontrolü çalışmaz | Yok | 5 dk yaşam sinyali (`logs/heartbeat.txt`); kapalıysa günlük rapor ve `/durum` KRİTİK der |
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

## 6. Sunucu seçenekleri (karar kullanıcıda)

| Seçenek | Artı | Eksi |
|---|---|---|
| Bugünkü PC + Windows görevi | Ücretsiz, veriler sende | PC kapalıyken çalışmaz |
| Küçük bulut sunucu (Docker hazır, adımlar docs/SERVER.md) | Kesintisiz; yeniden başlarsa kaçan raporu telafi eder | Aylık ücret, kişisel veriler sunucuda (onay gerekir); yedekler haftalık PC'ye alınmalı |
| GitHub Actions'ta rapor | Ücretsiz | Kişisel dosyalar herkese açık depoda tutulamaz; **uygun değil** |
