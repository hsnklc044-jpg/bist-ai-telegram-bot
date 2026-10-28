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
- Sınırlar: en çok 400 karakter, en çok 15 koşul (K-34, K-37). `ema(n)` ve `sma(n)` için n: 5, 10, 20, 40, 50, 100, 200.
- Hatalı yazımda mesaj hatanın yerini `^` ile gösterir ve en yakın alanı önerir. Ayrıştırıcı kendi yazdığımız kod; yazılan hiçbir şey çalıştırılmaz (eval/exec yok).

**Seçenekler.**
- `evren=bist100` (varsayılan): bugünkü resmi BIST 100 üyeliği, 100 hisse; karne de aynı kaynağı kullanır (K-36).
- `evren=quantbist`: raporun 118 hisselik listesi.
- `evren=izleme`: izleme listen.
- `evren=bist30` için kaynaklı bir `data/bist30.csv` gerekir; şimdilik yok.
- `likidite=10`: 20 günlük ortalama işlem hacmi, milyon TL. Varsayılan 10; `likidite=0` tabanı kapatır.
- `sirala=alfabetik|goreli_guc|hacim|rsi`.

**ATR uyarıları.** Son 14 seansta ±%10 limitini aşan bir kapanış hareketi ya da %30'dan büyük bir fiyat değişimi varsa satırda ⚠️ yazar: ATR o hareketle şişmiş olabilir.

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
| Momentum | `mom(n)` (varsayılan 10) | momentum: kapanış − n seans önceki kapanış | TL |
| Momentum | `cci(n)` (varsayılan 20) | CCI(n), emtia kanal endeksi | puan |
| Momentum | `getiri(n)` (varsayılan 20) | son n seans getiri (1 ay ≈ 21, 3 ay ≈ 63) | % |
| Momentum | `momentum10` | kapanış − 10 seans önceki kapanış (TradingView 'Mom, 10') | TL |
| Momentum | `degisim_1h` | son 5 seans değişim (TradingView 'Değ, 1H') | % |
| Momentum | `degisim_1a` | son 21 seans değişim (TradingView 'Değ/Perf, 1A') | % |
| Momentum | `degisim_3a` | son 63 seans değişim (TradingView 'Perf, 3A') | % |
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
| Hacim | `hacim_oran(n)` (varsayılan 20) | bugünkü hacim / önceki n gün ortalaması (20: canlı analizle aynı) | × |
| Hacim | `hacim_degisim` | bugünkü hacmin dünküne göre değişimi | % |
| Hacim | `ort_hacim(n)` (varsayılan 30) | n günlük ortalama hacim (adet) | milyon adet |
| Hacim | `vwma(n)` (varsayılan 20) | hacim ağırlıklı ortalama fiyat, n gün | TL |
| Hacim | `vwma20` | hacim ağırlıklı ortalama fiyat, 20 gün (TradingView 'VWMA, 20') | TL |
| Hacim | `goreli_hacim` | bugünkü hacim / önceki 10 seans ortalaması (TradingView 'Göreceli hacim'; hacim_oran 20 günlüktür) | × |
| Hacim | `ortalama_hacim_30g` | 30 günlük ortalama hacim, adet (TradingView 'Ort. hacim, 30G') | adet |
| Hacim | `likidite` | 20 günlük ortalama işlem hacmi, TL (likidite= seçeneği milyon TL'dir) | TL |
| Hacim | `obv_egim` | OBV'nin 20 günlük değişimi / 20 günlük toplam hacim | % |
| Hacim | `islem_tl` | 20 günlük ortalama işlem hacmi | milyon TL |
| Göreli güç | `gg_20` | son 20 seans getirisi − XU100'ünki | puan |
| Göreli güç | `gg_60` | son 60 seans getirisi − XU100'ünki | puan |
| Göreli güç | `gg_sira` | gg_60'ın taranan evrendeki yüzdelik sırası | 0–100 |
| Göreli güç | `beta` | son 252 seansta XU100'e göre beta | × |
| Fiyat konumu | `zirve_uzaklik` | kapanışın 52 hafta (252 seans) zirvesine uzaklığı | % |
| Fiyat konumu | `dip_uzaklik` | kapanışın 52 hafta dibine uzaklığı | % |
| Fiyat konumu | `yuksek_20g` | önceki 20 seansın en yükseği (bugün hariç) | TL |
| Fiyat konumu | `dusuk_20g` | önceki 20 seansın en düşüğü (bugün hariç) | TL |
| Fiyat konumu | `zirve_1a` | son 21 seansın en yükseği, bugün dahil (TradingView 'Yüksek, 1A') | TL |
| Fiyat konumu | `bosluk` | açılışın önceki kapanışa göre boşluğu | % |
| Fiyat konumu | `kapanis` | son kapanış | TL |
| Fiyat konumu | `acilis` | son açılış | TL |

**Komutlar.** `/tara` (kılavuz ve 5 örnek) · `/tara KRİTER` · `/tara_alanlar` · `/tara_aciklama KOD KRİTER` (o hissede her koşulun değeri, ✓/✗) · `/tara_devam` (sonraki 15 satır). Cevabın altında düğmeler var: Devam, Karne, Kaydet. Kaydet düğmesi kopyalanacak hazır komutu verir. Uzun cevaplar satırlar bölünmeden parçalanır.

**Sonuç boşsa** cevap bir koşul hunisi gösterir: her koşulu tek başına kaç hissenin sağladığı, öncekilerle birlikte kaç hissenin kaldığı ve en çok eleyen koşul.

**TradingView karşılıkları** (kullanıcının 28.10.2026'da gönderdiği 8 tarama; `tests/test_screen_user_screens.py` bunları kabul ölçütü olarak çalıştırır):

| Tarama | /tara | Sistemde olmayan / not |
|---|---|---|
| GÜÇLÜ TREND FİLTRESİ (GÜVENLİ PORTFÖY) | `kapanis>ema50 ema50>ema200 rsi 63..68 adx 25..40 ort_hacim(30)>20 getiri(21) 7..22 getiri(63) 15..55 ema20>ema50 beta 0,9..1,3` | Pys değ > 20 milyar TL (piyasa değeri verisi yok) |
| 11. Trend Sahibi Şişmemiş Hisseler | `kapanis>ema50 kapanis>ema200 rsi<65 hacim_degisim>10 hacim_oran(10)>2` | HO derecelendirmesi 'Güçlü al' (al/sat etiketi, eklenmez) |
| 10. Düşeni Kıran Hisse ve Harekete Hazır EMA | `kapanis<yuksek_20g rsi 50..70 hacim_oran(10)>1,5 ema(5)>ema(10) ema(10)>ema20 ema20>ema(40) ema50>ema(100) ema(100)>ema200 vwma(20)<kapanis getiri_5g<15 getiri(21)<20 cci(20)>-100 kapanis>acilis hacim_oran(10)>1` | Borsa piyasası (pazar bilgisi yok) |
| 8. Bebek hisse taraması | `hacim_oran(10)>1 mom(10)>0` | Pys değ 1–2 milyar TL (piyasa değeri verisi yok); FSO < 1 (temel veri yok) |
| Trend başlayan + formasyon tamamlamak üzere hisseler | `kapanis>ema50 ema50>ema200 rsi 55..70 hacim_oran(10)>1,8 adx>20 getiri(21) 5..25 kapanis>ema20 getiri_5g<10 kapanis>ema200` | — |
| GOLDENCROSS | `kesti_yukari(ema50,ema200) kapanis>ema200 rsi>50 hacim_oran(10)>1,5 macd>0 adx>20` | kesişim yalnız o günkü mumda aranır; son 5 seans için son(5, kesti_yukari(ema50,ema200)) |
| BIST TEK TUŞ TREND | `kapanis>ema50 ema50>ema200 rsi 60..70 adx>20 ort_hacim(30)>10 getiri(21)<30 beta 0,8..1,5 kapanis>ema20 getiri(63)<60` | Pys değ > 10 milyar TL (piyasa değeri verisi yok) |
| ERKEN TREND | `kapanis>ema20 kapanis<ema50 rsi 45..55 adx 15..22 hacim_oran(10)>1 ort_hacim(10)>10` | — |

Eşlemeler (TradingView adlarıyla alanlar da var, K-37): Perf/Değ 1A = `degisim_1a` (21 seans), 3A = `degisim_3a` (63), Değ 1H = `degisim_1h` (5); Göreceli hacim = `goreli_hacim` (önceki 10 seans; `hacim_oran` 20 günlüktür, ikisi ayrı); Ort. hacim 30G = `ortalama_hacim_30g` (adet) ya da `ort_hacim(30)` (milyon adet); Yüksek 1A = `zirve_1a` (bugün dahil 21 seans; `yuksek_20g` bugünü dışarıda bırakır); Mom 10 = `momentum10`; VWMA 20 = `vwma20`; likidite = `likidite` (TL; `likidite=` seçeneği milyon TL). Piyasa değeri, FSO ve borsa pazarı için veri yok. "HO derecelendirmesi: Güçlü al" bir al/sat etiketidir, eklenmez (CHARTER §9).

**Karne nasıl okunur** (K-35).
- **Dönem ve veri:** 2023-08 – 30.10.2026. Holdout (02.11.2026 sonrası) hiç okunmaz: veri `load_frames` ile gelir ve karne bir kez daha keser.
- **Olay:** her gün, o günkü BIST 100 üyesi olup koşulu sağlayan hisse bir olaydır (geçmiş üyelik; survivorship yok).
- **Giriş ve çıkış:** giriş ertesi seansın açılışıdır (geleceğe bakma yok); çıkış 5 ya da 20 seans sonraki kapanıştır.
- **Maliyet:** her yönde komisyon %0,10 + kayma %0,05, gidiş-dönüş %0,30 düşülür.
- **Likidite tabanı:** listedeki taban karnede de uygulanır; o günün 20 günlük ortalama işlem hacmi tabanın altındaysa olay sayılmaz.
- **Ölçü:** XU100'ün aynı seanslardaki getirisine göre fazla getiri.
- **Satırda** (K-39):
  - **gün ortalaması** ve %95 aralığı: önce her giriş gününün olay ortalaması alınır (her gün bir kez sayılır), sonra 20 seanslık dairesel blok bootstrap yapılır; etiket bu aralığa bakar
  - olay ortalaması (maliyet dahil, yanında maliyet hariç), medyan, isabet (XU100'ü geçen olay oranı)
  - örnek sayısı ve **bağımsız** olay sayısı (bir hissenin aynı tutma süresine düşen sinyalleri bir sayılır)
  - en kârlı 5 hisse çıkarılınca ortalama
  - **tüm hisseler**: aynı dönem, aynı evren ve aynı likidite tabanında koşulsuz gün ortalaması, ve koşulun ondan farkı
- **Etiketler:**
  - örnek 30'dan azsa "yetersiz örnek"
  - aralık sıfırı içeriyorsa "geçmişte XU100'den ayırt edilemiyor"
  - aralık tamamen sıfırın üstündeyse bile "geçmişte olumlu; çoklu deneme nedeniyle şans olabilir, kanıt değildir"
  - tamamen altındaysa "geçmişte XU100'ün gerisinde"
- **Veri gözetlemesi uyarısı:** karne bu oturumda kaçıncı deneme olduğunu ve bugüne kadar kaç farklı kriter denendiğini yazar (`logs/screen_trials.csv`). Ne kadar çok koşul denenirse iyi görünen bir karnenin şans olma ihtimali o kadar artar.
- **Önbellek:** karne aynı kriter ve aynı veri sürümü için bir kez hesaplanır (`logs/screen_cards.json`). Veri sürümü düzeltme ve üyelik dosyalarıyla değişir.
- **Uzun süren karne:** hesap 60 saniyeyi geçerse liste hemen gider, karne hazır olunca ayrı mesajla gelir.
- **Kanıt değildir:** koşullar serbestçe denenebildiği için karne bir kuralın işe yaradığına kanıt sayılmaz. Bir koşul araştırılacaksa ön kayıtla araştırma programına girer (RESEARCH_PROGRAM).

**Canlı ölçüm.** Bulunan her hisse `signal_log`'a "tara" kaynağıyla, kriter metni ve özetiyle yazılır. `/performans` her kriterin 5 ve 20 seans sonucunu ayrı gösterir.

**Kayıt.** `/tara_kaydet AD koşullar`, sonra `/tara AD`. `/tara_liste` kayıtları gösterir, `/tara_sil AD` siler. Kayıtlar `data/screens.csv`'de tutulur: yalnız ekleme, yedeğe dahil, `/durum` kontrol eder. Silme, o ada boş koşullu yeni bir satır yazar; önceki satırlar değişmez (K-41).

**Abonelik.** `/tara_abone AD` (kayıtlı tarama ya da şablon, en fazla 5). Her işlem günü 18:30 raporundan sonra çalışır ve yalnız listeye giren ve çıkan hisseleri gönderir; değişiklik yoksa mesaj gelmez. Rapor gitmeyen gün (tatil) çalışmaz. İlk mesaj listenin tamamıdır. `/tara_abonelikler` listeler, `/tara_abone_iptal AD` bitirir. Kayıtlar `data/screen_subscriptions.csv`'de tutulur: yalnız ekleme, yedekte (K-42).

**Hazır şablonlar** (`/tara_sablonlar` listeler, `/tara AD` çalıştırır; K-38). Kullanıcının TradingView taramalarının teknik kısmıdır. Filtre şablonudur, öneri değildir. Kodda sabittir ve sonuçlara bakılarak ayarlanmaz. Araştırma programına aday kural değildir. Kayıtlı taramalardan ayrıdır; bir kayıt şablon adını alamaz. Temel veri gerektiren koşullar (piyasa değeri, FSO, beta, gelir artışı, ÖGO, borç/öz kaynak) atlanır ve listede yazılır. Karneleri bot açılışında arka planda hesaplanıp önbelleğe alınır, veri sürümü değişince yenilenir; `/tara_sablonlar` yalnız önbelleği okur, hazır değilse "karne hazırlanıyor" der. Haftalık araştırma bütün şablon karnelerini `templates.txt`'ye yazar.

| Şablon | Koşullar | Kaynak | Atlanan (veri yok) |
|---|---|---|---|
| `basit_teknik` | `goreli_hacim>1 kesti_yukari(rsi,50) kesti_yukari(ema5,ema20)` | kullanıcının TradingView taraması 06, teknik kısım; kesişimler o günkü mumda | piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak |
| `basit_teknik_3g` | `goreli_hacim>1 son(3,kesti_yukari(rsi,50)) son(3,kesti_yukari(ema5,ema20))` | kullanıcının TradingView taraması 06, kesişimler son 3 seansta | piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak |
| `bebek_teknik` | `goreli_hacim>1 momentum10>0` | kullanıcının TradingView taraması 08 | piyasa değeri 1–2 milyar TL, FSO < 1 |
| `duseni_kiran` | `kapanis<zirve_1a rsi 50..70 goreli_hacim>1.5 ema5>ema10 ema10>ema20 ema20>ema40 ema50>ema100 ema100>ema200 vwma20<kapanis degisim_1h<15 degisim_1a<20 cci>-100 kapanis>acilis` | kullanıcının TradingView taraması 10 (ve 3, aynı EMA dizilimi) | — |
| `tek_tus_trend` | `kapanis>ema50 ema50>ema200 rsi 60..70 adx>20 ortalama_hacim_30g>10000000 degisim_1a<30 ema20<kapanis degisim_3a<60` | kullanıcının TradingView taraması BIST TEK TUŞ TREND | piyasa değeri > 10 milyar TL; beta 0,8–1,5 (fiyattan hesaplanır, `beta` alanı var; şablon görevdeki tanımla bırakıldı) |
| `teknik_temel_ema` | `kapanis>ema50 ema50>ema200` | kullanıcının TradingView taraması 05 | piyasa değeri > 2 milyar TL, gelir artışı (çeyreklik/yıllık), ÖGO, borç/öz kaynak |
