# QuantBIST

Borsa İstanbul hisseleri için teknik analiz, sinyal, portföy değerlendirmesi ve raporlama.
Telegram botu ve web paneli aynı çekirdeği (`core/`) kullanır.

> ⚠️ Backtest sonuçları geçmiş performanstır, geleceği garanti etmez. Yatırım tavsiyesi değildir.

## Kurulum

Python 3.11 veya üstü gerekir.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements-dev.txt
copy .env.example .env          # Windows  (macOS/Linux: cp .env.example .env)
```

`.env` dosyasını doldurun:

| Değişken | Açıklama |
| --- | --- |
| `BOT_TOKEN` | BotFather'dan alınan token |
| `CHAT_ID` | Botun cevap vereceği tek Telegram sohbetinin id'si |
| `QUANTBIST_DEBUG` | `1` ise Flask debug modu açılır (sadece yerelde) |
| `LOG_LEVEL` | `INFO` (varsayılan), `DEBUG`, `WARNING` |

## Çalıştırma

```bash
python main.py                    # Telegram botu
python app.py                     # Web paneli (Flask)  → http://127.0.0.1:5000
python -m core.web.app            # Web paneli (FastAPI) → http://127.0.0.1:8000/dashboard
```

## Sunucusuz kullanım (GitHub Actions)

Bilgisayar ya da sunucu gerekmez; bildirimleri GitHub'ın sunucuları gönderir.

1. Telegram'da `@BotFather` → botun token'ı. `@userinfobot`'a yazın → size `Id` (CHAT_ID) verir.
   Kendi botunuza bir kez `/start` yazın (bot size ancak böyle mesaj atabilir).
2. GitHub'da depo → **Settings → Secrets and variables → Actions → New repository secret**:
   `BOT_TOKEN` ve `CHAT_ID` ekleyin. Token'ı hiçbir dosyaya veya sohbete yazmayın.
3. **Actions → Telegram notices → Run workflow**: rotasyon raporu hemen Telegram'a gelir.

Sonrası otomatik (`.github/workflows/notify.yml`): hafta içi 18:50'de ayın ilk seansıysa dengeleme
bildirimi, cuma günleri haftalık rotasyon raporu. Bu yolda bot komutlara (`/rotasyon` vb.) cevap
vermez; onun için botun sürekli çalıştığı bir sunucu gerekir.

## Sunucuda 7/24 (Docker)

Herhangi bir Linux sunucuda (ör. aylık ~5 $'lık VPS):

```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/hsnklc044-jpg/bist-ai-telegram-bot.git && cd bist-ai-telegram-bot
cp .env.example .env && nano .env      # BOT_TOKEN ve CHAT_ID
docker compose run --rm bot python -m core.market.update   # ilk veri indirme
docker compose up -d --build
docker compose logs -f                  # çıkmak için Ctrl+C (bot çalışmaya devam eder)
```

Güncelleme: `git pull && docker compose up -d --build`. `data/` klasörü (fiyatlar, takip listesi)
güncellemelerde korunur. Sunucuda bot çalışıyorsa GitHub Actions bildirimlerini kapatın
(**Actions → Telegram notices → Disable workflow**), yoksa bildirimler iki kez gelir.

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
- Seans bitmeden (18:15'ten önce) o günün mumu kullanılmaz; sinyaller sadece kapanmış mumlardan üretilir.
- Kalite raporu eksik günleri, bayat veriyi, sıfır hacimli günleri ve ±%10 tavan/taban limitini
  aşan sıçramaları (genelde bölünme/bedelsiz veya veri hatası) gösterir.

## Backtest

Canlı sinyalin (`/analyze`'ın gösterdiği skor) geçmişte nasıl çalıştığını ölçer.
Her gün için skor, sadece o güne kadar kapanmış mumlarla yeniden hesaplanır.

```bash
python -m core.backtest                  # tüm evren, eşit ağırlıklı portföy
python -m core.backtest THYAO EREGL      # seçili hisseler + işlem listesi
python -m core.backtest --compare        # zamanlama + rotasyon + al-tut, aynı dönemde yan yana
python -m core.backtest --no-target --trailing-atr 3 --hold-in-uptrend
python -m core.backtest --stop-atr 1.5 --target-atr 3 --max-hold 20 --commission 0.001
```

**Rotasyon** (`core/backtest/rotation.py`): hep yatırımda kalır. Her ayın ilk seansının kapanışında
hisseler sıralanır, en iyi N tanesi ertesi açılışta eşit ağırlıkla alınır. Sıralama: `/analyze` skoru,
126 seanslık momentum veya ikisinin sıra ortalaması (karma). İsteğe bağlı trend filtresi
XU100 200 günlük ortalamanın altındayken nakde geçer. Sadece el değiştiren tutar için
komisyon ve kayma ödenir.

Bilgisayar yoksa: GitHub'da **Actions → Backtest → Run workflow**. Fiyatlar orada indirilir,
sonuç çalıştırmanın özet sayfasında görünür.

Kurallar (sadece alış yönlü, `core/backtest/engine.py`):

- Skor ≥ 70 (BUY) olunca **ertesi seansın açılışında** alınır; sinyali üreten kapanıştan işlem yapılmaz.
- Stop = giriş − 2 ATR, hedef = giriş + 4 ATR (`/analyze`'daki stop ve hedef 2 ile aynı).
  Aynı mum ikisine de değerse stop önce sayılır; açılışta boşlukla geçilirse açılıştan dolar.
- Skor ≤ 35 (SELL) veya 40 gün dolunca ertesi açılışta satılır.
- Her alış ve satışta %0,2 komisyon ve %0,1 kayma düşülür.
- Portföy: sermaye başta hisselere eşit bölünür, yeniden dengelenmez.
  Kıyas: aynı hisselerin eşit ağırlıklı al-tutu ve XU100. Getiri ayrıca USD bazında
  (USD/TRY, `TRY=X`) gösterilir; TL getirisi enflasyon yüzünden tek başına yanıltıcıdır.
- Dönem ikiye bölünür (1. yarı / 2. yarı): iki yarıda da tutarlı olmayan kural şansa bağlıdır.
- İsteğe bağlı: `--no-target` (sabit hedef yok), `--trailing-atr 3` (en yüksek kapanışı izleyen
  stop), `--hold-in-uptrend` (XU100 200 günlük ortalamanın üstündeyken sat sinyali ve süre
  çıkışı yok sayılır), `--cash-rate 0.40` (boştaki nakde yıllık faiz).
- Günlük fiyat limitinin (±%10, kapalı geçen seanslarla bileşik) açıklayamadığı sıçrama içeren
  hisseler (genelde fiyata yansıtılmamış bedelsiz) dışarıda bırakılır; `--keep-jumps` ile dahil edilir.

## Telegram komutları

| Komut | İş |
| --- | --- |
| `/rotasyon` | Momentum rotasyonu: bu ayın 5 hissesi, sıradakiler, backtest özeti |
| `/top` | Teknik skoru en yüksek 10 hisse |
| `/analyze THYAO` | Tek hisse teknik özeti |
| `/backtest`, `/backtest THYAO` | Sinyalin 5 yıllık geçmiş testi |
| `/summary` | Portföy, piyasa ve karar özeti |
| `/watchlist`, `/watchadd EREGL`, `/watchremove EREGL`, `/watchscan` | Takip listesi |
| `/help` | Komut listesi |

Bot sadece `CHAT_ID` sohbetinden gelen komutlara cevap verir.

Hafta içi her gün 18:45'te (İstanbul) bot rotasyonu kontrol eder. Son kapanış ayın ilk
seansıysa `CHAT_ID` sohbetine giren / çıkan / kalan hisseleri bir kez bildirir. Önceki liste
`data/rotation_state.json` dosyasında tutulur.

`/top` ve `/analyze` teknik skoru "Güçlü pozitif … Güçlü negatif" diye gösterir. Bu skor tek
başına backtestte al-tutu geçemediği için al-sat sinyali olarak sunulmaz.

## Strateji

`/rotasyon` backtestte ayakta kalan kuralı uygular (`core/rotation/service.py`): her ayın ilk
seansının kapanışında hisseler 126 seanslık (≈6 ay) getiriye göre sıralanır, en iyi 5 tanesi
ertesi açılışta eşit ağırlıkla tutulur. Backtest sonuçları al-tuttan yüksek ama düşüşler daha
derin; hisse listesi bugünün büyük şirketleri olduğu için sonuçlar iyimserdir.

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
| `bot/` | Telegram komutları |
| `core/market/` | Fiyat verisi (yfinance), indikatörler, piyasa rejimi |
| `core/analytics/` | Hisse bazında skor ve sinyaller |
| `core/rotation/` | Canlı momentum rotasyonu ve aylık bildirim |
| `core/backtest/` | Sinyal geçmişi, zamanlama ve rotasyon simülasyonu, backtest raporu |
| `core/portfolio/` | Portföy sağlığı, risk, dağılım (`data/portfolio_model.csv`) |
| `core/committee/`, `core/decision/`, `core/ai/` | Portföy düzeyinde karar |
| `core/dashboard/`, `core/charts/`, `core/reports/`, `core/export/` | Panel, grafik, rapor, dışa aktarma |
| `core/config/` | Yollar (`paths.py`), eşikler (`thresholds.py`), ağırlıklar |
| `templates/`, `static/` | Flask paneli |
| `core/web/` | FastAPI paneli |

## Yol haritası

0. Temizlik ve güvenlik ✅
1. Veri katmanı: uzun geçmiş, kalıcı cache, kapanmış mumlar, gerçek piyasa genişliği ✅
2. Strateji ve backtest motoru ✅
3. Risk ve pozisyon boyutu, işlem defteri
4. Zamanlayıcı ile otomatik tarama ve bildirim ✅ (aylık rotasyon bildirimi)
5. Sanal işlem (paper trading)
6. Tek web paneli, Docker ✅, operasyon (GitHub Actions bildirimleri ✅)
7. Aracı kurum üzerinden emir (isteğe bağlı)
