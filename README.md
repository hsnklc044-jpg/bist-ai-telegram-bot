# QuantBIST

Borsa İstanbul hisseleri için teknik analiz, sinyal, portföy değerlendirmesi ve raporlama.
Telegram botu ve web paneli aynı çekirdeği (`core/`) kullanır.

> ⚠️ Sinyaller henüz backtest edilmedi. Yatırım tavsiyesi değildir.

## Kurulum

Python 3.11 gerekir. Paket sürümleri `requirements.lock` ile sabitlenmiştir;
böylece her kurulum aynı sonuçları üretir.

Windows'ta tek komut (sanal ortamı kurar, sabit sürümleri yükler, ruff ve
testleri çalıştırır, sonucu `logs\setup_report.txt` dosyasına yazar):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
copy .env.example .env
```

Yalnızca kontrol (kurulum yapmadan): `scripts\setup.ps1 -CheckOnly`.

Elle kurulum:

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.lock
copy .env.example .env          # Windows  (macOS/Linux: cp .env.example .env)
```

Paket yükseltmesi bilinçli yapılır: yükselt, testleri çalıştır, geçerse
`pip freeze | Out-File -Encoding ascii requirements.lock` ile kilidi yenile
(PowerShell'de `>` dosyayı UTF-16 yazar, bu yüzden kullanılmaz).

`.env` dosyasını doldurun:

| Değişken | Açıklama |
| --- | --- |
| `BOT_TOKEN` | BotFather'dan alınan token |
| `CHAT_ID` | Botun cevap vereceği tek Telegram sohbetinin id'si |
| `QUANTBIST_DEBUG` | `1` ise web paneli kod değişince kendini yeniden başlatır (sadece yerelde) |
| `LOG_LEVEL` | `INFO` (varsayılan), `DEBUG`, `WARNING` |

## Çalıştırma

```bash
python main.py                    # Telegram botu
python -m core.web.app            # Web paneli (/summary ile aynı özet) → http://127.0.0.1:8000/dashboard
```

## Fiyat verisi

Fiyatlar `data/market.db` (SQLite) dosyasında 5 yıllık günlük mum olarak tutulur.
İlk çalıştırmada tamamı indirilir, sonra sadece eksik günler gelir. Yahoo'ya
ulaşılamazsa sistem son kayıtlı veriyle çalışmaya devam eder.

```bash
python -m core.market.update          # veriyi güncelle + kalite raporu
python -m core.market.update --full   # 5 yılı baştan indir
python -m core.market.quality         # sadece kalite raporu
```

- Taranan hisseler `data/universe.csv` dosyasında; satır ekleyerek listeyi genişletebilirsiniz.
  Mevcut liste yaklaşık BIST100'dür: BtcTurk'ün Temmuz 2026 BIST100 listesi + Ekim 2026
  revizyonunda eklenen hisseler (endeksten çıkanlar da araştırma için bırakıldı). Resmî güncel
  bileşen listesi değildir.
- Seans bitmeden (18:15'ten önce) o günün mumu kullanılmaz; sinyaller sadece kapanmış mumlardan üretilir.
- 8 Şubat 2023 (deprem sonrası iptal edilen seans) verilerden çıkarılır.
- Yahoo'nun düzeltmediği bedelsiz/bedelli/bölünme etkileri `data/corporate_actions.csv` ile düzeltilir;
  kalite raporu şüpheli sıçramalar için önerilen satırı yazdırır (KAP'tan doğrulayıp ekleyin).
- Kalite raporu eksik günleri, bayat veriyi, sıfır hacimli günleri ve ±%20'yi aşan sıçramaları
  (düzeltme önerisiyle; bu hisseler backtest'ten dışlanır) gösterir. Ayrıca bilgi olarak ±%10
  günlük limitle açıklanamayan %20 altı hareketleri listeler; bunlar hisseyi dışlamaz. Düşüşler
  temettü düzeltmesiyle açıklanamadığı için önce listelenir (fiyata yansımamış bedelli olabilir).
- **İkinci kaynak kontrolü** (`python -m core.market.crosscheck`, haftalık araştırmada otomatik):
  son 30 günün kapanışları İş Yatırım'ın fiyat geçmişiyle günlük getiri bazında karşılaştırılır
  (Yahoo fiyatları temettüye göre düzeltilmiş olduğu için seviye değil getiri). 1 puandan büyük
  farklar, tek kaynakta olan günler ve kontrol edilemeyen hisseler raporlanır. İş Yatırım verisi
  ücretsiz ama resmî olmayan bir web servisi; yalnızca kontrol için, hisse başına bir istekle kullanılır.

## Backtest

```bash
python -m core.backtest.run                  # 5 pozisyon, %0.10 komisyon + %0.05 kayma
python -m core.backtest.run --positions 3 --start 2023-01-01
```

Botun canlı sinyalini (`core/strategy/score.py`, canlı skorla birebir aynı) gerçek
veride test eder; trend kuralı, eşit ağırlık al-tut ve XU100 ile karşılaştırır.
İşlemler sinyal gününün kapanışında değil, ertesi günün açılışında yapılır.

### Strateji araştırması

```bash
python -m core.market.update --bist100-history   # önce: 2022'den beri BIST 100'e girmiş her hissenin verisi
python -m core.backtest.research                 # bot sinyali, trend, momentum, walk-forward, XU100
python -m core.backtest.research --universe today  # karşılaştırma: bugünkü liste (survivorship bias'lı)
```

- **Evren:** varsayılan olarak geçmiş BIST 100 üyeliği; her gün yalnızca o günkü üyeler alınabilir.
  Bugünkü listeyle test, sonradan yükselen hisseleri baştan seçtiği için sonuçları şişirir.
  Eski üyelerin %10'undan fazlası verisizse rapor sonucu "güvenilir değil" diye işaretler.
- **İstatistik:** her stratejinin XU100'e göre günlük fazla getirisi için blok bootstrap güven
  aralığı (21 seanslık bloklar), test edilen strateji sayısına göre Bonferroni ile genişletilir.
  Aralığın tamamı sıfırın üstünde değilse strateji "XU100'ü geçti" sayılmaz.
- **Geçmiş:** GitHub'daki haftalık çalışma her raporu `research-results` dalına kaydeder
  (`runs/<tarih>/`, `history.csv`) ve öncekiyle karşılaştırır (`python -m core.backtest.history`):
  yıllık getiri değişimi, karar değişimi ve her stratejinin kaç çalışmada anlamlı çıktığı.
- **Walk-forward:** parametreler önceki 24 ayda seçilir, sonraki 6 ayda (görülmemiş veride)
  işlem yapılır; her pencere XU100 ile yan yana, ayrıca medyan ve "en iyi pencere hariç" sonuç.

## Telegram komutları

| Komut | İş |
| --- | --- |
| `/top` | En güçlü 10 sinyal |
| `/analyze THYAO` | Tek hisse analizi |
| `/summary` | Piyasa, gerçek ve sanal hesap, açık risk uyarıları (salt okunur; AL/SAT kararı içermez) |
| `/watchlist`, `/watchadd EREGL`, `/watchremove EREGL`, `/watchscan` | Takip listesi |
| `/portfolio` | Pozisyonlar ve kâr/zarar (gerçek ve sanal hesap) |
| `/trade al THYAO 100 285,50 [komisyon] [GG.AA.YYYY]` | Gerçekleşmiş işlemi deftere yaz (`sat`, `bedelsiz`, `bedelli` de olur) |
| `/paper al THYAO 100 [gerekçe]`, `/paper sat THYAO 50`, `/paper iptal 3`, `/paper` | Sanal emir; bir sonraki açılıştan dolar (09:40'tan önce verilirse aynı günün açılışından). Gerekçe isteğe bağlı, kayda geçer |
| `/alerts` | Açık risk uyarıları |
| `/report` | Günlük raporu şimdi üret |
| `/performans` | Kayıtlı teknik görünümlerin ve sanal hesabın canlı sonucu, XU100'e karşı |
| `/durum` | Sistem sağlığı, dört seviye (SAĞLIKLI / UYARI / KRİTİK / BİLİNMİYOR): Telegram botu (5 dakikalık yaşam sinyali), son rapor, fiyat verisi, fiyat veritabanı bütünlüğü, canlı kayıt, sanal hesap, veri şeması, yedek, disk, tatil takvimi, son GitHub araştırması. Doğrulanamayan bileşen asla SAĞLIKLI görünmez. Bot açıksa hafta içi 20:00'de sorunları bildirir; aynı sorun 3 günde bir kez. Bot kapalıysa uyarıyı günlük rapor verir |
| `/rapor_tekrar [27.10]` | Kayıtlı günlük raporu yeniden gönderir (yeniden hesaplamaz); tarih yoksa en sonuncusu. Raporlar v0.57.0'dan beri `logs/reports/`'ta |
| `/help` | Komut listesi |

`/start` yazınca alttaki klavyenin yerine sık kullanılan komutların düğmeleri gelir (/durum, /summary, /portfolio, /alerts, /performans, /rapor_tekrar). Telegram'ın "Menu" düğmesi de bütün komutları açıklamalarıyla listeler (bot açılırken ayarlanır).

Bot sadece `CHAT_ID` sohbetinden gelen komutlara cevap verir ve hiçbir zaman gerçek emir göndermez.

## Portföy, sanal işlem ve günlük rapor

- **Defter** `data/ledger.csv`: tek kayıt kaynağı. Satırlar silinmez; hata ters işlemle düzeltilir.
  Pozisyon, ortalama maliyet ve gerçekleşen kâr/zarar FIFO ile defterden hesaplanır.
  Elde tutulan hissede bedelsiz/bedelli olursa `/trade bedelsiz` ya da `/trade bedelli` ile girin;
  girilmezse rapor uyarır.
- **Sanal hesap** 100.000 TL nakitle başlar. Emirler `data/paper_orders.csv` dosyasında bekler.
  Her emirle birlikte kaydedilir: gerekçe, kullanılan veri (son kapanış tarihi ve fiyatı), teknik skor
  (tahmin gücü kanıtlanmadı), tutar ve sanal hesaptaki payı, oynaklık (ATR/fiyat); dolumda açılış
  fiyatı, kayma ve komisyon, dolamadığı tavan/taban günleri. Defterde kayıtlı bir dolum ikinci kez
  yazılmaz. v0.28.0 öncesi dosya ilk yeniden yazımdan önce `paper_orders_before_v0.28.csv` olarak saklanır.
- **Risk uyarıları** (eşikler `core/config/alerts.py`): iz süren ATR stop, kilitli taban, parabolik
  yükseliş, likidite, yoğunlaşma, hesap düşüşü, veri sorunları. Portföy düzeyinde
  (`core/alerts/portfolio.py`): 1 günlük kayıp tahmini (%95 tarihsel, son 250 seans; hesabın %5'ini
  aşarsa uyarı), birlikte hareket eden ağır hisse çiftleri (60 seans korelasyonu ≥ 0,80 ve ikisi
  hesabın ≥ %35'i), etkin pozisyon sayısı ve fiyatı olmayan pozisyon. Günlük rapor ve `/portfolio`
  "Risk:" satırını gösterir; hesaplanamazsa nedenini yazar. Durum değişiklikleri
  `data/alerts_log.csv` dosyasına yazılır; aynı uyarı her gün tekrar gönderilmez.
- **Sinyal kaydı** `data/signal_log.csv`: `/analyze`, `/top` ve `/watchscan` çıktıları veri tarihiyle kaydedilir.
  Günlük kayıtlar denetlenir (`/durum`, `/performans` "Kayıt sağlığı"): tekrar kayıt, okunamayan satır,
  kaydı olmayan seans (tatiller hariç) ve yeni kapanış varken eski veriyle yazılmış gün.
- **Günlük rapor**: `python -m core.reports.daily [--send] [--no-update]`. Hafta içi 18:30'da otomatik
  göndermek için bir kez: `powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1`
  (kaldırmak için `-Remove`). Çıktılar `logs\daily_<tarih>.log`.
  Botu oturum açılışında kendiliğinden başlatmak için bir kez: `powershell -ExecutionPolicy Bypass -File scripts\register_bot_task.ps1`
  (tek kopya çalışır; ayrıca elle `python main.py` başlatmayın, Telegram iki botu reddeder).
  Aynı anda tek rapor çalışır; aynı veri günü Telegram'a bir kez gider (tatilde tekrar gönderilmez,
  yeniden göndermek için `--force`). Her çalıştırma `logs\runs.csv` dosyasına yazılır:
  `sent` gönderildi, `skipped` zaten gönderilmişti, `holiday` bugün seans yok (tatil), `stale` beklenen
  kapanışın verisi gelmedi, `busy` başka bir çalıştırma sürüyordu, `failed` hata.
- **Tatil takvimi** `data/bist_holidays.csv`: Borsa İstanbul'un tam gün tatilleri ve yarım günleri (arifeler;
  pay piyasası ~12:40'ta kapanır). Yeni yılın tarihleri Borsa İstanbul'un Aralık duyurusundan eklenir;
  `/durum` eksik yılı ve yaklaşan tatilleri gösterir, haftalık araştırma dosyayı XU100 mumlarıyla karşılaştırır
  (`python -m core.market.calendar`).

Bu dosyalar kişiseldir; `.gitignore` içindedir ve sürüm zip'leri bunların üzerine yazmaz.

**Canlı performans** (`python -m core.reports.forward`, Telegram'da `/performans`): günlük rapor her
akşam tüm hisselerin teknik görünümünü `data/signal_log.csv` dosyasına kaydeder. Her kayıt, ertesi
açılışta alınıp 5, 20 ve 60 seans tutulmuş gibi XU100'e karşı puanlanır. Aynı günün kayıtları birlikte
hareket ettiği için %95 aralık günler üzerinden hesaplanır; 20 işlem gününden önce sonuç "henüz karar
yok" olarak gösterilir. Sanal hesabın değeri de aynı günlerde XU100 ile karşılaştırılır. Geçmişe
uydurulamayan tek ölçüm budur: sadece sonuç bilinmeden önce yazılmış kayıtları puanlar.

**Yedekleme:** günlük rapor her çalıştığında bu kişisel dosyaları tarihli bir zip'e yedekler
(`data\backups\quantbist_<tarih>.zip`, son 30 gün; her yedek SHA-256 ile doğrulanır) ve raporun
sonuna "💾 Yedek" satırını ekler. Disk arızasına karşı `.env` içinde `BACKUP_DIR` ile senkronize
bir klasör (ör. OneDrive) gösterin. Rapor hazırlanamazsa Telegram'a ayrıca uyarı gelir.

```bash
python -m core.backup                     # şimdi yedekle
python -m core.backup --list              # yedekleri listele ve doğrula
python -m core.backup --restore data\backups\quantbist_2026-10-26.zip   # geri yükle
```
Geri yükleme önce yedeği doğrular, sonra mevcut dosyaların ayrı bir yedeğini alır; böylece
yanlış yedek seçilse bile önceki hâle dönülebilir.

## Sunucuda 7/24 (Docker)

Bilgisayar kapalıyken de botun komutlara cevap vermesi ve günlük raporun gelmesi için
herhangi bir Linux sunucuda (ör. aylık ~5 $'lık VPS):

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/hsnklc044-jpg/bist-ai-telegram-bot.git && cd bist-ai-telegram-bot
cp .env.example .env && nano .env        # BOT_TOKEN, CHAT_ID, DAILY_REPORT_AT=18:30
docker compose run --rm bot python -m core.market.update   # ilk veri indirme
docker compose up -d --build
docker compose logs -f                   # çıkmak için Ctrl+C (bot çalışmaya devam eder)
```

- Sunucuda günlük raporu bot kendisi gönderir (`DAILY_REPORT_AT`, hafta içi, İstanbul saati);
  böylece `data/` klasörüne tek bir program yazar.
- Cuma raporunun sonunda canlı ölçüm özeti (XU100'e göre ileri getiri ve sanal hesap) yer alır;
  ayrıntı `/performans` komutundadır.
- **Kişisel kayıtları taşıyın:** bilgisayardaki `data\ledger.csv`, `paper_orders.csv`,
  `watchlist.json`, `alerts_log.csv`, `signal_log.csv`, `equity_log.csv` dosyalarını sunucudaki
  `data/` klasörüne kopyalayın (ör. Windows'tan `scp`). `data/` içindeki diğer dosyalar depodan gelir.
- **Aynı anda tek bot:** sunucu çalışırken bilgisayardaki `python main.py`'yi kapatın ve
  zamanlanmış görevi kaldırın (`scripts\register_daily_task.ps1 -Remove`). İki bot aynı token'la
  çalışırsa Telegram "Conflict" hatası verir; iki zamanlayıcı raporu iki kez gönderir.
- Güncelleme: `git pull && docker compose up -d --build`. `data/` ve `logs/` korunur.

## Geliştirme

```bash
ruff check .
pytest -q
```

Testler internete çıkmaz; fiyat verisi `tests/helpers.py` içinde üretilir.
GitHub'a push edildiğinde `.github/workflows/ci.yml` aynı kontrolleri çalıştırır.

## Proje yapısı

| Klasör | İçerik |
| --- | --- |
| `bot/` | Telegram komutları, sunucu modunda günlük rapor zamanlayıcısı |
| `core/market/` | Fiyat verisi (yfinance), düzeltmeler, kalite raporu, BIST100 üyelikleri, indikatörler |
| `core/analytics/`, `core/strategy/` | Teknik skor (canlı ve zaman serisi), aday kurallar |
| `core/backtest/` | Backtest motoru, araştırma, güvenilirlik, walk-forward, düşüş teşhisi |
| `core/ledger/`, `core/alerts/` | İşlem defteri, sanal emirler, risk uyarıları |
| `core/reports/` | Günlük rapor (`daily`), özet (`overview`), canlı performans (`forward`) |
| `core/backup.py`, `core/signals_log.py` | Kişisel kayıtların yedeği, görünüm kaydı |
| `core/config/` | Yollar (`paths.py`), eşikler (`thresholds.py`), işlem ve uyarı ayarları |
| `core/web/` | Web paneli (FastAPI; `/summary` ile aynı özet) |

## Yol haritası

Ayrıntılı durum, açık sorunlar ve öncelikler: [docs/ROADMAP.md](docs/ROADMAP.md).

Kurulum doğrulaması tek komutla: `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1` (çıktı `logs\verify_report.txt`, token ve chat id gizli). İşletim ve kurtarma: [docs/OPERATIONS.md](docs/OPERATIONS.md). Veri düzeltmeleri: [docs/DATA_CORRECTIONS.md](docs/DATA_CORRECTIONS.md). Geliştirme oturumu için hazır mesajlar: [docs/MESAJLAR.md](docs/MESAJLAR.md). Sunucuya taşıma: [docs/SERVER.md](docs/SERVER.md).


0. Temizlik ve güvenlik ✅
1. Veri katmanı: uzun geçmiş, kalıcı cache, kapanmış mumlar, gerçek piyasa genişliği ✅
2. Backtest motoru (walk-forward, BIST100 üyelik geçmişi, maliyet) ✅ — kanıtlanmış strateji henüz yok
3. Risk ve pozisyon boyutu, işlem defteri ✅
4. Zamanlayıcı ile günlük rapor ve bildirim ✅
5. Sanal işlem (paper trading) ✅
6. Tek web paneli, Docker, yedekleme, operasyon ✅
7. Canlı ölçüm: görünümlerin XU100'e göre ileri getirisi (`/performans`, Cuma özeti) — veri birikiyor
8. Aracı kurum üzerinden emir (isteğe bağlı; yalnızca canlı ölçüm bir kuralı kanıtlarsa ve açık onayla)
