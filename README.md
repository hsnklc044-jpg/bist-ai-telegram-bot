# QuantBIST

Borsa İstanbul hisseleri için teknik analiz, sinyal, portföy değerlendirmesi ve raporlama.
Telegram botu ve web paneli aynı çekirdeği (`core/`) kullanır.

> ⚠️ Sinyaller henüz backtest edilmedi. Yatırım tavsiyesi değildir.

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

## Telegram komutları

| Komut | İş |
| --- | --- |
| `/top` | En güçlü 10 sinyal |
| `/analyze THYAO` | Tek hisse analizi |
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
| `core/portfolio/` | Portföy sağlığı, risk, dağılım (`data/portfolio_model.csv`) |
| `core/committee/`, `core/decision/`, `core/ai/` | Portföy düzeyinde karar |
| `core/dashboard/`, `core/charts/`, `core/reports/`, `core/export/` | Panel, grafik, rapor, dışa aktarma |
| `core/config/` | Yollar (`paths.py`), eşikler (`thresholds.py`), ağırlıklar |
| `templates/`, `static/` | Flask paneli |
| `core/web/` | FastAPI paneli |

## Yol haritası

0. Temizlik ve güvenlik ✅
1. Veri katmanı: uzun geçmiş, kalıcı cache, kapanmış mumlar, gerçek piyasa genişliği
2. Strateji ve backtest motoru
3. Risk ve pozisyon boyutu, işlem defteri
4. Zamanlayıcı ile otomatik tarama ve bildirim
5. Sanal işlem (paper trading)
6. Tek web paneli, Docker, operasyon
7. Aracı kurum üzerinden emir (isteğe bağlı)
