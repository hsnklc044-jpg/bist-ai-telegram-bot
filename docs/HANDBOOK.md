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
- **Kendi koşullarımla tarama.** Bkz. §8 (`/tara`).
- **Bir kural "işe yarıyor" mu?** RESEARCH_LOG'daki ön kayıtlı ölçüt geçmeden hayır. Canlı ölçüm kararı Kasım 2026 sonu.

## 8. Gösterge taraması (/tara)

**Bir filtredir, öneri değildir** (CHARTER §9, DECISIONS K-32, K-33). Liste yalnız "bugün hangi hisseler bu koşulları sağlıyor" sorusunu cevaplar. "Al/sat/öneri/fırsat/hedef fiyat" dili kullanılmaz. Sıralama alfabetiktir ya da ölçülmüş bir alana göre yapılır; "en iyi" sıralaması yoktur. Her listenin son satırı: "Filtre sonucudur, yatırım önerisi değildir."

**Yazım.**
- Karşılaştırma: `rsi<30`, `ema20>ema50` (`<= >=` de olur).
- Aralık: `rsi 30..50`.
- Kesişim: `kesti_yukari(ema20,ema50)`, `kesti_asagi(macd,macd_sinyal)`.
- Pencere: `son(5, kesti_yukari(...))` (koşul son 5 seansın birinde sağlandıysa).
- Mantık: `ve` / `veya` / `değil` ve parantez. Yan yana yazılan koşullar "ve" sayılır.
- Ondalıklar virgülle yazılabilir: `1,5`.
- Sınırlar: en çok 300 karakter, en çok 10 koşul.
- Hatalı yazımda mesaj hatanın yerini `^` ile gösterir ve en yakın alanı önerir. Ayrıştırıcı kendi yazdığımız kod; yazılan hiçbir şey çalıştırılmaz (eval/exec yok).

**Seçenekler.**
- `evren=bist100` (varsayılan, güncel liste) ya da `evren=izleme` (izleme listen). `evren=bist30` için kaynaklı bir `data/bist30.csv` gerekir; şimdilik yok.
- `likidite=10`: 20 günlük ortalama işlem hacmi, milyon TL. Varsayılan 10; `likidite=0` tabanı kapatır.
- `sirala=alfabetik|goreli_guc|hacim|rsi`.

**Elenenler adıyla yazılır, sessizce düşürülmez:** son kapanışı son seans olmayan, ikinci kaynakta farkı olan (düzeltme bekleyen) ve likidite tabanının altındaki hisseler.

**Zaman kuralı.** Göstergeler yalnız kapanmış mumlardan hesaplanır. Seans sürerken çalıştırılırsa cevap "dünkü kapanışa göre" olduğunu yazar.

**Hesap yolu.** `ema20, ema50, rsi, macd, hacim_oran, atr_yuzde` canlı analizin kendi hesabından (`score_frame`) alınır; bot ile tarama aynı değeri gösterir (`test_screen_engine.FieldTest`). Diğer alanlar aynı kütüphaneyle hesaplanır. ATR ve ADX'in hızlı sürümleri kütüphaneyle bit bit aynı sonucu verir (`FastAtrTest`, `FastAdxTest`). BIST 100 tam tarama, 5 yıllık veriyle 5 saniyenin altında kalır (testte sınır var).

**Alanlar** (`/tara_alanlar` aynı listeyi gösterir):

| Grup | Alan | Ne | Birim |
|---|---|---|---|
| Trend | `ema(n)` (varsayılan 20) | üssel ortalama, ema(n) ya da ema20/ema100 gibi | TL |
| Trend | `sma(n)` (varsayılan 20) | basit ortalama, sma(n) ya da sma200 gibi | TL |
| Trend | `ema20` | 20 günlük üssel ortalama (canlı analizle aynı) | TL |
| Trend | `ema50` | 50 günlük üssel ortalama (canlı analizle aynı) | TL |
| Trend | `ema200` | 200 günlük üssel ortalama | TL |
| Trend | `uzaklik_ema(n)` (varsayılan 20) | kapanışın ema(n)'ye uzaklığı | % |
| Trend | `uzaklik_sma(n)` (varsayılan 20) | kapanışın sma(n)'ye uzaklığı | % |
| Trend | `adx(n)` (varsayılan 14) | ADX(n), trendin gücü (yönsüz) | 0–100 |
| Trend | `supertrend` | Supertrend (10, 3) yönü: 1 yukarı, -1 aşağı | ±1 |
| Momentum | `rsi(n)` (varsayılan 14) | RSI(n) (14: canlı analizle aynı) | 0–100 |
| Momentum | `macd` | MACD (12, 26) (canlı analizle aynı) | TL |
| Momentum | `macd_sinyal` | MACD sinyal çizgisi (9) | TL |
| Momentum | `macd_hist` | MACD − sinyal | TL |
| Momentum | `stok_k` | stokastik %K (14) | 0–100 |
| Momentum | `stok_d` | stokastik %D (3) | 0–100 |
| Momentum | `roc(n)` (varsayılan 10) | n günlük değişim oranı | % |
| Momentum | `getiri_5g` | son 5 seans getiri | % |
| Momentum | `getiri_20g` | son 20 seans getiri | % |
| Momentum | `getiri_60g` | son 60 seans getiri | % |
| Oynaklık | `atr(n)` (varsayılan 14) | ATR(n), ortalama gerçek aralık | TL |
| Oynaklık | `atr_yuzde` | ATR(14) / kapanış (canlı analizle aynı) | % |
| Oynaklık | `bb_ust` | Bollinger üst bandı (20, 2) | TL |
| Oynaklık | `bb_alt` | Bollinger alt bandı (20, 2) | TL |
| Oynaklık | `bb_genislik` | Bollinger genişliği / orta bant | % |
| Oynaklık | `bb_yuzde` | Bollinger %b ×100 (0 alt bant, 100 üst bant) | % |
| Oynaklık | `bb_genislik_yuzdelik` | bugünkü genişliğin son 126 seanstaki yüzdelik sırası | 0–100 |
| Oynaklık | `oynaklik_20g` | 20 günlük tarihsel oynaklık (yıllık) | % |
| Hacim | `hacim_oran` | bugünkü hacim / önceki 20 gün ortalaması (canlı analizle aynı) | × |
| Hacim | `obv_egim` | OBV'nin 20 günlük değişimi / 20 günlük toplam hacim | % |
| Hacim | `islem_tl` | 20 günlük ortalama işlem hacmi | milyon TL |
| Göreli güç | `gg_20` | son 20 seans getirisi − XU100'ünki | puan |
| Göreli güç | `gg_60` | son 60 seans getirisi − XU100'ünki | puan |
| Göreli güç | `gg_sira` | gg_60'ın taranan evrendeki yüzdelik sırası | 0–100 |
| Fiyat konumu | `zirve_uzaklik` | kapanışın 52 hafta (252 seans) zirvesine uzaklığı | % |
| Fiyat konumu | `dip_uzaklik` | kapanışın 52 hafta dibine uzaklığı | % |
| Fiyat konumu | `yuksek_20g` | önceki 20 seansın en yükseği (bugün hariç) | TL |
| Fiyat konumu | `dusuk_20g` | önceki 20 seansın en düşüğü (bugün hariç) | TL |
| Fiyat konumu | `bosluk` | açılışın önceki kapanışa göre boşluğu | % |
| Fiyat konumu | `kapanis` | son kapanış | TL |
| Fiyat konumu | `acilis` | son açılış | TL |

**Karne nasıl okunur.**
- Aynı koşulların 2023-08 – 30.10.2026 verisindeki geçmişidir. Holdout (02.11.2026 sonrası) hiç okunmaz.
- Her gün o günkü BIST 100 üyeleri alınır. Giriş ertesi seansın açılışıdır; çıkış 5 ya da 20 seans sonraki kapanıştır; sonuç XU100'e göre fazla getiri olarak verilir.
- 30'dan az örnekte "yetersiz örnek" yazar.
- Koşullar serbestçe denenebildiği için karne bir kuralın işe yaradığına **kanıt değildir**. Bir koşul araştırılacaksa ön kayıtla araştırma programına girer (RESEARCH_PROGRAM).

**Canlı ölçüm.** Bulunan her hisse `signal_log`'a "tara" kaynağıyla, kriter metni ve özetiyle yazılır. `/performans` her kriterin 5 ve 20 seans sonucunu ayrı gösterir.

**Kayıt.** `/tara_kaydet AD koşullar`, sonra `/tara AD`. Kayıtlar `data/screens.csv`'de tutulur: yalnız ekleme, yedeğe dahil, `/durum` kontrol eder.
