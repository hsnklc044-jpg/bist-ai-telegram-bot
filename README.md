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
python -m core.backtest --stop-atr 1.5 --target-atr 3 --max-hold 20 --commission 0.001
```

Kurallar (sadece alış yönlü, `core/backtest/engine.py`):

- Skor ≥ 70 (BUY) olunca **ertesi seansın açılışında** alınır; sinyali üreten kapanıştan işlem yapılmaz.
- Stop = giriş − 2 ATR, hedef = giriş + 4 ATR (`/analyze`'daki stop ve hedef 2 ile aynı).
  Aynı mum ikisine de değerse stop önce sayılır; açılışta boşlukla geçilirse açılıştan dolar.
- Skor ≤ 35 (SELL) veya 40 gün dolunca ertesi açılışta satılır.
- Her alış ve satışta %0,2 komisyon ve %0,1 kayma düşülür.
- Portföy: sermaye başta hisselere eşit bölünür, yeniden dengelenmez. Kıyas: XU100 al-tut.

## Telegram komutları

| Komut | İş |
| --- | --- |
| `/top` | En güçlü 10 sinyal |
| `/analyze THYAO` | Tek hisse analizi |
| `/backtest`, `/backtest THYAO` | Sinyalin 5 yıllık geçmiş testi |
| `/summary` | Portföy, piyasa ve karar özeti |
| `/watchlist`, `/watchadd EREGL`, `/watchremove EREGL`, `/watchscan` | Takip listesi |
| `/help` | Komut listesi |

Bot sadece `CHAT_ID` sohbetinden gelen komutlara cevap verir.

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
| `core/backtest/` | Sinyal geçmişi, işlem simülasyonu, backtest raporu |
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
4. Zamanlayıcı ile otomatik tarama ve bildirim
5. Sanal işlem (paper trading)
6. Tek web paneli, Docker, operasyon
7. Aracı kurum üzerinden emir (isteğe bağlı)
