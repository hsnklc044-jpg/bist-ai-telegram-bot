# QuantBIST el kitabı

Aylar sonra, hiçbir şey hatırlamadan açan biri için tek başlangıç noktası. Ayrıntılar bağlantılı belgelerde.

## 1. Bu sistem ne yapar, ne yapmaz

- BIST hisseleri için **ölçüm ve rapor** botu: her iş günü 18:30'da Telegram'a kapanış raporu, komutlarla portföy/sanal hesap/sağlık bilgisi, haftalık araştırma.
- **Al/sat önerisi vermez, gerçek emir göndermez, aracı kuruma bağlanmaz.** Sanal hesap yalnız ölçüm içindir.
- Test edilen hiçbir kural XU100'ü istatistiksel olarak geçmedi (docs/RESEARCH_LOG.md). Gerçek para için kanıt **yok**.

## 2. Mimari

```
                 Yahoo (fiyat)            İş Yatırım (ikinci kaynak, haftalık)
                      │                              │
   ┌──────────────────▼───────────────┐   ┌──────────▼───────────────────────┐
   │ PC (Windows)                     │   │ GitHub                            │
   │                                  │   │                                   │
   │ "QuantBIST Gunluk Rapor" görevi  │   │ CI: ruff + testler + kapsam ≥%91  │
   │  18:30 → core.reports.daily      │   │ Research (cumartesi): araştırma,  │
   │    fiyat güncelle → rapor →      │   │   Aşama 3, ikinci kaynak özeti,   │
   │    yedek → Telegram → ping       │   │   kurumsal işlem taraması         │
   │                                  │   │ Security (pazartesi): pip-audit   │
   │ "QuantBIST Bot" görevi           │   │ research-results dalı: sonuçlar   │
   │  main.py → bot/ (komutlar,       │   └───────────────────────────────────┘
   │  20:00 kontrol, 5 dk yaşam       │
   │  sinyali)                        │   Healthchecks.io (isteğe bağlı):
   │                                  │   sinyal gelmezse uyarır
   │ data/  kişisel kayıtlar + fiyat  │
   │ logs/  runs.csv, heartbeats.csv, │   Yerel otomasyon
   │        freshness.csv, log'lar    │   (C:\Projeler\QuantBIST_otomasyon):
   │ OneDrive\QuantBIST-yedek: yedek  │   yeni sürümü dener, kurar, geri alır
   └──────────────────────────────────┘
```

Kod düzeni: `core/market` (fiyat, takvim, düzeltmeler, ikinci kaynak), `core/reports` (rapor, sağlık, SLO), `core/ledger` (defter, sanal hesap), `core/backtest` (araştırma), `core/strategy` (kurallar), `bot/` (Telegram).

## 3. Kurulum ve geri yükleme

- Sıfırdan kurulum ve yedekten dönüş: **docs/DISASTER_RECOVERY.md**.
- Tek arıza noktaları (PC, internet, Yahoo, Telegram, GitHub) ve B planları: **docs/SPOF.md**.
- Araştırma kuralları (deneme bütçesi, ileri holdout, ön kayıt): **docs/RESEARCH_PROGRAM.md**.
- Yeni sürümü yerel otomasyon kurar (deneme kopyasında ruff + pytest, olmazsa geri alır). Elle kurulum gerekirse: OPERATIONS §5.

## 4. Günlük işleyiş

| Saat | Ne olur | Nerede görülür |
|---|---|---|
| Her 5 dk | Bot yaşam sinyali (`logs/heartbeats.csv`, Healthchecks) | `/durum` "Telegram botu" ve SLO "Bot ayakta kalma" |
| 18:30 (iş günü) | Fiyat güncelleme, rapor, yedek, canlı ölçüm kaydı | Telegram raporu; `logs/runs.csv`; `RUN daily …` satırı |
| 20:00 (iş günü) | Sağlık kontrolü; sorun varsa tek mesaj | Telegram |
| Cuma raporu | Canlı ölçüm özeti, haftalık sistem özeti, SLO tablosu | Telegram |
| Cumartesi | GitHub araştırması | GitHub Actions > Research; `research-results` dalı |
| Pazartesi | Paket güvenlik taraması | GitHub Actions > Security |

## 5. Sağlık nasıl okunur

- `/durum`: bileşenlerin şu anki durumu + "📐 SLO (son 7 gün)" (CHARTER §2 hedefleri). "Bilinmiyor" = ölçülemedi, asla "sağlıklı" sayılmaz.
- Bir şey bozulursa: **OPERATIONS §8** (kesinti tablosu: ne olur / nasıl fark edilir / nasıl toparlanır / kimin işi).
- Log'da arama: OPERATIONS §7b.

## 6. Kurallar ve kararlar

- **docs/CHARTER.md**: yönetim belgesi (öncelikler, SLO'lar, roller, aşamalar, kalite kapıları).
- **docs/DECISIONS.md**: verilen teknik kararlar ve gerekçeleri.
- **docs/ROADMAP.md**: şu anki durum, bekleyen işler.
- **docs/RESEARCH_LOG.md**: her araştırma, sonuçtan önce yazılmış planıyla.
- **docs/DATA_CORRECTIONS.md**: veriye yapılan (ve yapılmayan) her düzeltme, kaynağıyla.
- **docs/MAINTENANCE.md**: haftalık/aylık/yıllık bakım.
- **CHANGELOG.md**: sürüm geçmişi, sade dille.

## 7. Sık sorulanlar

- **Rapor gelmedi.** `/durum` → "Günlük rapor". PC açık mıydı? `logs/runs.csv`'nin son satırı ne diyor? Elle: `Start-ScheduledTask "QuantBIST Gunluk Rapor"`.
- **Bot cevap vermiyor.** `Start-ScheduledTask "QuantBIST Bot"`. Elle `python main.py` açmayın; iki bot çakışır.
- **"… kilitli" yazıyor.** Dosya Excel'de açık; kapatın, sonraki çalışma yazar.
- **Bir hissede garip fiyat.** `python -m core.market.crosscheck --inspect KOD:YYYY-AA-GG` (ya da GitHub "Data check" iş akışı, `inspect` girdisi). Düzeltme yalnız `data/price_fix_approvals.csv` onayıyla.
- **Kendi koşullarımla tarama.** Telegram'da `/tara` örnekleri ve alanları gösterir (ör. `/tara rsi<30 ema20>ema50`). Liste filtre sonucudur. Altındaki karne 2023-08 – 30.10.2026 verisinin özetidir; holdout (02.11.2026 sonrası) kullanılmaz. Koşullar serbestçe denenebildiği için karne bir kuralın kanıtı değildir. Bulunan hisseler canlı ölçüme "tara" kaynağıyla yazılır; `/performans` her kriterin 5 ve 20 seans sonucunu gösterir. Taramalar `/tara_kaydet AD koşullar` ile `data/screens.csv`'ye kaydedilir (yedeğe dahil, yalnız ekleme).
- **Bir kural "işe yarıyor" mu?** RESEARCH_LOG'daki ön kayıtlı ölçüt geçmeden hayır. Canlı ölçüm kararı Kasım 2026 sonu.
