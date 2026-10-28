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
- **"Gecikti" ne zaman denir:** bir seans gününün raporu, fiyatı ve canlı ölçüm kaydı o gün 19:45'ten itibaren beklenir (rapor 18:30, tolerans 1:15). Yarım günler de aynıdır; tatil ve hafta sonu hiçbir şey beklemez (K-46). 19:45'ten önce gün içindeki "bugün yok" uyarıları hata değildir ve gösterilmez.
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
- Eleme seçenekleri (aşağıda "Eleme filtreleri"): `ele=hayir` hepsini kapatır. Tek tek kapatmak için: `ele_likidite=0` (eski adı `likidite=`; sayı yazılırsa taban o olur, varsayılan 15 mn TL), `ele_kurumsal=0`, `ele_hareket=0`, `ele_veri=0`.
- `sirala=alfabetik|goreli_guc|hacim|rsi`.

**ATR uyarıları.** Son 14 seansta ±%10 limitini aşan bir kapanış hareketi ya da %30'dan büyük bir fiyat değişimi varsa satırda ⚠️ yazar: ATR o hareketle şişmiş olabilir.

**Eleme filtreleri** (her sonuca varsayılan olarak uygulanır; K-45). Bunlar hisse eler, hisse seçmez. Elenen her hisse sonucun altında tek satırda nedeniyle yazılır, ör. "Elenen (3): X (likidite 8 mn TL), Y (bedelli 14.10)".

| Filtre | Ne zaman eler | Kapatmak |
|---|---|---|
| Likidite | Önceki 20 tam seansın ortalama işlem tutarı < 15 mn TL (bugün sayılmaz) | `ele_likidite=0` |
| Kurumsal işlem | Son 60 seansta bedelli, bedelsiz/bölünme (`data/corporate_actions.csv`) ya da halka arz (ilk mumu fiyat deposunun başlangıcından sonra). **Kaydı olmayan hissede bilinmiyor; elenmez.** KAP duyuruları haftalık taramada görülür, kendiliğinden kayda girmez. | `ele_kurumsal=0` |
| Aşırı hareket | Son 10 seansta 3 ya da daha çok ±%9,5'i aşan gün, ya da ATR14/kapanış taranan listenin en oynak %5'inde (en az 20 hisselik listede) | `ele_hareket=0` |
| Veri sorunu | Son 252 seansta düzeltilmemiş ±%20 tek gün sıçraması, son 20 seansta 3 ya da daha çok gün sıfır hacim, ya da ikinci kaynakta fark (düzeltme bekliyor) | `ele_veri=0` |

Son kapanışı son seans olmayan hisse her zaman "veri eksik" olarak ayrıca yazılır; o hisse taranamaz. Karne aynı elemeleri her gün o günün verisiyle uygular: likidite o güne kadarki 20 seans, kurumsal işlem o günden önceki 60 seans, ATR sırası o günkü üyeler arasında. İkinci kaynak farkı yalnız canlı listede vardır.

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
| Trend | `egim(alan,n)` | egim(alan, n): alanın n seanstaki yüzde değişimi; egim(sma200,21)>0 = 200 günlük ortalama 21 seanstır yükseliyor | % |
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
| Momentum | `getiri_6a_1a_haric` | 6 ay getirisi, son 1 ay hariç: kapanış[t−21] / kapanış[t−126] − 1 (Jegadeesh & Titman 6-1) | % |
| Momentum | `getiri_12a_1a_haric` | 12 ay getirisi, son 1 ay hariç: kapanış[t−21] / kapanış[t−252] − 1 (12-1 momentum) | % |
| Göreli güç | `rs_puan` | ağırlıklı göreli güç puanı: 0,4×getiri(63) + 0,2×(126, 189, 252) (IBD/O'Neil RS yaklaşımı) | % |
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
| Oynaklık | `oynaklik_60g` | 60 günlük tarihsel oynaklık (yıllık) | % |
| Oynaklık | `oynaklik_sira` | oynaklik_60g'nin taranan evrendeki yüzdelik sırası (100 = en oynak) | 0–100 |
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
| Göreli güç | `goreli_guc_yuzdelik` | rs_puan'ın taranan evrendeki yüzdelik sırası (Minervini/IBD 'RS rating' yaklaşımı) | 0–100 |
| Göreli güç | `momentum_sira` | getiri_6a_1a_haric'in taranan evrendeki yüzdelik sırası | 0–100 |
| Göreli güç | `beta` | son 252 seansta XU100'e göre beta | × |
| Seviye | `destek_uzaklik_atr` | en yakın küme desteğine uzaklık, ATR (negatif: altta; K-49, teknik seviye) | ATR |
| Seviye | `direnc_uzaklik_atr` | en yakın küme direncine uzaklık, ATR (pozitif: üstte) | ATR |
| Seviye | `seviye_gucu` | en yakın küme seviyesinin güç puanı (dokunma, yaş, kırılma; sabit formül) | 0–100 |
| Seviye | `kirdi_yukari` | kirdi_yukari(direnc) ile yazılır: kapanış dünkü en yakın direnci 0,5 ATR'den fazla geçti | 1/0 |
| Seviye | `kirdi_asagi` | kirdi_asagi(destek) ile yazılır: kapanış dünkü en yakın desteğin 0,5 ATR'den fazla altına indi | 1/0 |
| Fiyat konumu | `zirve_52h` | 52 hafta (252 seans) en yükseği, bugün dahil | TL |
| Fiyat konumu | `dip_52h` | 52 hafta (252 seans) en düşüğü, bugün dahil | TL |
| Fiyat konumu | `zirve_52h_oran` | kapanış / 52 hafta en yükseği × 100 (95 = zirvenin %95'i) | % |
| Fiyat konumu | `dip_52h_oran` | kapanış / 52 hafta en düşüğü × 100 (130 = dibin %30 üstü) | % |
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
- **Elemeler:** listedeki elemeler karnede de her gün o günün verisiyle uygulanır (likidite, kurumsal işlem, aşırı hareket, veri sorunu; K-45). Elenen gün olay sayılmaz.
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

**Canlı ölçüm.** Bulunan her hisse `signal_log`'a "tara" kaynağıyla, kriter metni ve özetiyle yazılır. `/performans` "Taramalar" bölümünde her kriterin 5 ve 20 seans sonucunu kriter özetiyle ayrı gösterir. 30 olgun örnekten azsa sayı yerine "veri birikiyor" yazar.

**Kayıt.** `/tara_kaydet AD koşullar`, sonra `/tara AD`. `/tara_liste` kayıtları gösterir, `/tara_sil AD` siler. Kayıtlar `data/screens.csv`'de tutulur: yalnız ekleme, yedeğe dahil, `/durum` kontrol eder. Silme, o ada boş koşullu yeni bir satır yazar; önceki satırlar değişmez (K-41).

**Abonelik.** `/tara_abone AD` (kayıtlı tarama ya da şablon, en fazla 5). Her işlem günü 18:30 raporundan sonra çalışır ve yalnız listeye giren ve çıkan hisseleri gönderir; değişiklik yoksa mesaj gelmez. Rapor gitmeyen gün (tatil) çalışmaz. İlk mesaj listenin tamamıdır. `/tara_abonelikler` listeler, `/tara_abone_iptal AD` bitirir. Kayıtlar `data/screen_subscriptions.csv`'de tutulur: yalnız ekleme, yedekte (K-42).

**Sanal köprü.** `/tara_sanal AD` kayıtlı bir taramayı ya da şablonu ölçüm amaçlı bir sanal kitapta işletir. Varsayılan kapalıdır; `/tara_sanal AD kapat` kapatır, `/tara_sanal` durumu gösterir.
- Kurallar önceden yazılıdır: eşit ağırlık, en çok 5 pozisyon, 20 seans, 2 ATR stop, ertesi açılışta giriş, maliyet dahil.
- Kriter açıldığı anda dondurulur.
- Sonuç `/performans`'ta "SANAL, yalnız ölçüm" etiketiyle görünür; 30 kapanmış işleme kadar "veri birikiyor" yazar.
- Kişisel `/paper` emirlerine ve deftere dokunmaz; kitap her seferinde fiyatlardan yeniden hesaplanır (K-43).

**Karnede dışarıda kalanlar.** Araştırmadaki gibi, çözülmemiş ±%20 veri sıçraması (düzeltilmemiş bedelli, bedelsiz ya da bölünme) ya da 300 mumdan kısa geçmişi olan hisseler karneye girmez (öz-denetim 6, D1). Şablon karneleri bunların listesini yazar.

**Hazır şablonlar** (`/tara_sablonlar` listeler, `/tara AD` çalıştırır; K-38). Kullanıcının TradingView taramalarının teknik kısmıdır. Filtre şablonudur, öneri değildir. Kodda sabittir ve sonuçlara bakılarak ayarlanmaz. Araştırma programına aday kural değildir. Kayıtlı taramalardan ayrıdır; bir kayıt şablon adını alamaz. Temel veri gerektiren koşullar (piyasa değeri, FSO, beta, gelir artışı, ÖGO, borç/öz kaynak) atlanır ve listede yazılır. Karneleri bot açılışında arka planda hesaplanıp önbelleğe alınır, veri sürümü değişince yenilenir; `/tara_sablonlar` yalnız önbelleği okur, hazır değilse "karne hazırlanıyor" der. Haftalık araştırma bütün şablon karnelerini `templates.txt`'ye yazar.

| Şablon | Koşullar | Kaynak | Atlanan (veri yok) |
|---|---|---|---|
| `basit_teknik` | `goreli_hacim>1 kesti_yukari(rsi,50) kesti_yukari(ema5,ema20)` | kullanıcının TradingView taraması 06, teknik kısım; kesişimler o günkü mumda | piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak |
| `basit_teknik_3g` | `goreli_hacim>1 son(3,kesti_yukari(rsi,50)) son(3,kesti_yukari(ema5,ema20))` | kullanıcının TradingView taraması 06, kesişimler son 3 seansta | piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak |
| `bebek_teknik` | `goreli_hacim>1 momentum10>0` | kullanıcının TradingView taraması 08 | piyasa değeri 1–2 milyar TL, FSO < 1 |
| `duseni_kiran` | `kapanis<zirve_1a rsi 50..70 goreli_hacim>1.5 ema5>ema10 ema10>ema20 ema20>ema40 ema50>ema100 ema100>ema200 vwma20<kapanis degisim_1h<15 degisim_1a<20 cci>-100 kapanis>acilis` | kullanıcının TradingView taraması 10 (ve 3, aynı EMA dizilimi) | — |
| `tek_tus_trend` | `kapanis>ema50 ema50>ema200 rsi 60..70 adx>20 ortalama_hacim_30g>10000000 degisim_1a<30 ema20<kapanis degisim_3a<60` | kullanıcının TradingView taraması BIST TEK TUŞ TREND | piyasa değeri > 10 milyar TL; beta 0,8–1,5 (fiyattan hesaplanır, `beta` alanı var; şablon görevdeki tanımla bırakıldı) |
| `teknik_temel_ema` | `kapanis>ema50 ema50>ema200` | kullanıcının TradingView taraması 05 | piyasa değeri > 2 milyar TL, gelir artışı (çeyreklik/yıllık), ÖGO, borç/öz kaynak |
| `trend_takibi` | `ema20>ema50 ema50>ema200 adx>20` | /tara görev örneği (Aşama 5) | — |
| `asiri_satim` | `rsi<30 kapanis>ema200` | /tara görev örneği (Aşama 5) | — |
| `kirilim` | `kapanis>yuksek_20g hacim_oran>1.5` | /tara görev örneği (Aşama 5) | — |
| `sikisma` | `bb_genislik_yuzdelik<10` | /tara görev örneği (Aşama 5) | — |
| `goreli_guc` | `gg_sira>80` | /tara görev örneği (Aşama 5) | — |
| `minervini` | `kapanis>sma150 kapanis>sma200 sma150>sma200 egim(sma200,21)>0 sma50>sma150 kapanis>sma50 dip_52h_oran>=130 zirve_52h_oran>=75 goreli_guc_yuzdelik>=70` | profesyonel filtre (Aşama 2): Minervini (2013), Trend Template; pratisyen kuralı, akademik kanıtı sınırlı. goreli_guc_yuzdelik IBD 'RS rating' yaklaşımıdır | — |
| `zirveye_yakin` | `zirve_52h_oran>=95` | profesyonel filtre (Aşama 2): George & Hwang (2004), 52 hafta zirvesi ve momentum | — |
| `goreli_guc_ust` | `momentum_sira>=80` | profesyonel filtre (Aşama 2): Jegadeesh & Titman (1993), 6 ay getirisi, son 1 ay hariç. Bu sistemde kesitsel momentum reddedildi (2025 +%88, 2026 −%73; RESEARCH_LOG) | — |
| `dusuk_oynaklik` | `oynaklik_sira<=20` | profesyonel filtre (Aşama 2): Ang, Hodrick, Xing & Zhang (2006); Blitz & van Vliet (2007). Bu sistemde H1 düşük oynaklık reddedildi (+%0,9 [−16,5; +18,6]; RESEARCH_LOG) | — |

Her şablonun yanında ait olduğu araştırma türü yazar: RESEARCH_LOG'daki "Reddedilen fikir türleri" tablosu (27.10.2026'da test edildi, XU100'ü geçmedi). Teknik sinyal: `basit_teknik`, `basit_teknik_3g`, `bebek_teknik`, `asiri_satim`. Tek hissede trend/kırılım: `duseni_kiran`, `tek_tus_trend`, `teknik_temel_ema`, `trend_takibi`, `kirilim`, `sikisma`. Kesitsel momentum: `goreli_guc`.

**Profesyonel filtreler ve elemeler** (K-45, K-47). Bunlar filtre ve eleme araçlarıdır, öneri değildir. Kaynakları başka piyasalarda yapılmış çalışmalardır; BIST'teki durumu bu sistemin kendi karnesi gösterir ve karne kanıt sayılmaz. Hiçbirine "güvenilir" ya da "kanıtlanmış" denmez.

| Filtre | Kaynak | Ne seçer / ne eler | BIST'te bilinen durum (bu sistem) | Sınırlar |
|---|---|---|---|---|
| Eleme: likidite | Uygulama kuralı (görev) | Önceki 20 seansta ortalama < 15 mn TL'yi eler | Kayma ve uygulanabilirlik içindir, getiri iddiası yok | Eşik enflasyonla eskir; yeniden bakılmalı |
| Eleme: kurumsal işlem | Uygulama kuralı | Son 60 seansta kayıtlı bedelli, bedelsiz/bölünme ya da halka arz olanı eler | Kayıtlar eksik (D4); kaydı olmayan hisse "bilinmiyor" | KAP'tan otomatik kayıt yok |
| Eleme: aşırı hareket | Uygulama kuralı | 10 seansta 3 tavan/taban ya da en oynak %5'i eler | Keşifte elenen grup kalan gruptan zayıf göründü; canlı ölçüm sürüyor | Tek dönem; kanıt değil |
| Eleme: veri sorunu | Veri kalite kuralı | Düzeltilmemiş sıçrama, sıfır hacim, ikinci kaynak farkı | Veri hatasını işleme dönüştürmemek içindir | Yahoo'ya bağlı |
| `minervini` | Minervini (2013), Trend Template | Uzun vadeli yükselen trendde, 52 hafta dibinden en az %30 yukarıda, zirvesinin en az %75'inde, göreli gücü üst %30'da olan hisseler | Tek hissede trend türü 27.10.2026'da reddedildi; karne ayrıca gösterilir | Pratisyen kuralı; akademik kanıtı sınırlı; `goreli_guc_yuzdelik` IBD RS yaklaşımıdır, birebir değildir |
| `zirveye_yakin` | George & Hwang (2004) | Kapanışı 52 hafta zirvesinin en az %95'inde olanlar | Geçmiş getiriye dayalı sıralamalar momentum ailesinden sayılıp araştırma programından dışlandı | ABD verisi; BIST'te ayrıca sınanmadı |
| `goreli_guc_ust` | Jegadeesh & Titman (1993), 6-1 momentum | 6 ay getirisi (son ay hariç) evrenin üst %20'si | Kesitsel momentum reddedildi: 2025 +%88, 2026 −%73 (RESEARCH_LOG) | Rejime çok bağlı |
| `dusuk_oynaklik` | Ang, Hodrick, Xing & Zhang (2006); Blitz & van Vliet (2007) | 60 günlük oynaklığı evrenin en düşük %20'si | H1 düşük oynaklık reddedildi: +%0,9 [−16,5; +18,6] | Düşük oynaklık "düşük risk" garantisi değildir |

Yeni alanlar: `sma150`, `zirve_52h`, `dip_52h`, `zirve_52h_oran`, `dip_52h_oran`, `egim(alan,n)`, `getiri_6a_1a_haric`, `getiri_12a_1a_haric`, `oynaklik_60g`, `rs_puan`, `goreli_guc_yuzdelik`, `momentum_sira`, `oynaklik_sira`.
- **Sıralar evren içidir.** Canlı listede taranan hisseler arasında, karnede o günkü BIST 100 üyeleri arasında hesaplanır.
- **Dil çarpma yazmaz.** "Zirvenin %75'i" `zirve_52h_oran>=75`, "dibin %30 üstü" `dip_52h_oran>=130` olarak yazılır.

**Temel veri deposu** (`data/fundamentals.csv`, K-48). Her kalem **yayın tarihiyle** saklanır. Bir seans, bir kalemi ancak yayın gününden sonraki seanstan itibaren görür; 18:30'da gönderilen bir bilanço o gün kullanılmaz. Bu yüzden karne ve tarama geleceği görmez.
- Düzeltilmiş (restated) tablo yeni bir satırdır. Her gün en yeni dönemin en yeni yayını geçerlidir; hiçbir şey üzerine yazılmaz.
- `inflation_adjusted` sütunu TMS 29 tablolarını işaretler (2023 yıl sonundan itibaren; 1/0/boş). Büyüme oranları iki dönemi karıştırmaz.
- **Veri girişi:** yalnız dosyadan içe aktarma: `python -m core.fundamentals.store --import DOSYA`. Her satır denetlenir: kod, tarih, yayın tarihi > dönem sonu, bilinen kalem, sayı, kaynak. Reddedilenler satır numarası ve nedeniyle yazılır.
- **KAP'tan otomatik çekme kapalıdır:** kullanım koşulları teyit edilmedi. Modülde ağ kodu yoktur (test denetler).
- **Durum ve karşılaştırma:** `/durum` "Temel veri" satırı son yayını ve kaç hissede ana kalemlerin eksiksiz olduğunu gösterir. Depo boşken bu bir bilgi satırıdır, hata değildir. `--compare DOSYA` ikinci bir kaynağın dosyasıyla kalem kalem fark raporu verir.
- **Sütunlar:** symbol, period_end, published_at (ISO, saat dilimiyle), item, value (TL), unit, consolidated (1/0), inflation_adjusted (1/0/boş), source.
- **Kalemler:** `revenue` (hasılat (satışlar)), `cost_of_sales` (satışların maliyeti), `gross_profit` (brüt kâr), `operating_profit` (esas faaliyet kârı (FVÖK yerine)), `ebit` (faiz ve vergi öncesi kâr), `net_income` (net dönem kârı (ana ortaklık)), `operating_cash_flow` (işletme faaliyetlerinden nakit akışı), `depreciation` (amortisman ve itfa), `sga` (genel yönetim + pazarlama giderleri), `total_assets` (toplam varlıklar), `current_assets` (dönen varlıklar), `receivables` (ticari alacaklar), `ppe` (maddi duran varlıklar), `cash` (nakit ve nakit benzerleri), `total_liabilities` (toplam yükümlülükler), `current_liabilities` (kısa vadeli yükümlülükler), `long_term_debt` (uzun vadeli finansal borçlar), `financial_debt` (toplam finansal borçlar), `total_equity` (özkaynaklar (ana ortaklık)), `retained_earnings` (geçmiş yıllar kârları), `paid_in_capital` (ödenmiş sermaye (nominal TL = pay adedi)), `dividends_paid` (ödenen temettü).

**CHARTER §9 uyumu (/tara).**
- `/tara` bir filtredir.
- Emir vermez; aracı kuruma, deftere ve kişisel `/paper` emirlerine dokunmaz. Sanal köprü kendi ölçüm kitabını her seferinde fiyatlardan yeniden hesaplar ve hiçbir yere emir yazmaz (K-43).
- Token ya da şifre istemez, okumaz.
- Hiçbir metinde al/sat/öneri/fırsat/hedef fiyat/en iyi/şampiyon dili yoktur. Liste, karne, abonelik ve sanal köprü mesajları "Filtre sonucudur, yatırım önerisi değildir." satırıyla biter.
- Karneler holdout'u (02.11.2026 sonrası) okumaz. Şablonlar sonuçlara bakılarak ayarlanmaz ve araştırma programına aday kural değildir.
- `test_screen_quality` bunları her sürümde denetler: modüllerde emir, defter ve token yok; metinlerde öneri dili yok; son satır sabit.

**BotFather listesi** (bot her açılışta bu listeyi Telegram'a kendisi yükler, `set_my_commands`. Elle girmek gerekirse BotFather → /setcommands → bota bu blok yapıştırılır. Test, listenin bottaki menüyle aynı olduğunu denetler.)

```
start - komutlar ve düğmeler
durum - sistem sağlığı ve hedefler
summary - portföy ve piyasa özeti
portfolio - pozisyonlar ve kâr/zarar
alerts - açık risk uyarıları
performans - canlı ölçüm ve sanal hesap
rapor_tekrar - kayıtlı günlük raporu yeniden gönder
report - günlük raporu şimdi üret
yil - yıllık döküm: satışlar, temettü, komisyon
stres - pozisyonlar en kötü geçmiş düşüşlerde ne kaybederdi
alarm - kapanış alarmı: /alarm THYAO altında 240
tara - göstergeyle filtre: /tara rsi<30 ema20>ema50
tara_kaydet - taramayı kaydet: /tara_kaydet AD koşullar
tara_liste - kayıtlı taramalar
tara_sil - kayıtlı taramayı sil: /tara_sil AD
tara_abone - her akşam yalnız değişiklikleri gönder: /tara_abone AD
tara_abonelikler - tarama abonelikleri
tara_abone_iptal - aboneliği bitir: /tara_abone_iptal AD
tara_sanal - taramayı ölçüm amaçlı sanal kitapta işlet (varsayılan kapalı)
tara_alanlar - tarama alanları ve birimleri
tara_aciklama - bir hissede koşulların değeri: /tara_aciklama THYAO rsi<30
tara_devam - son taramanın sonraki 15 satırı
tara_sablonlar - hazır tarama şablonları (TradingView taramalarından)
top - teknik görünümü en güçlü hisseler
analyze - tek hisse: /analyze THYAO
seviye - destek/direnç seviyeleri: /seviye THYAO (öneri değil)
watchlist - takip listesi
watchadd - listeye ekle: /watchadd EREGL
watchremove - listeden çıkar
watchscan - takip listesini tara
trade - gerçekleşmiş işlemi deftere yaz
paper - sanal emir
```

## 9. Destek ve direnç seviyeleri (/seviye; K-49)

**Teknik seviye, öneri değil.** Seviyeler, kapanmış ve kurumsal işlemlere göre düzeltilmiş günlük mumlardan hesaplanır. Bir seviye yalnız o güne kadarki mumları kullanır (test). Hiçbir çıktıda "güçlü destek", "buradan al" ya da "alım bölgesi" yazmaz.

Yöntemler (her seviye yöntem adıyla gösterilir):
- **küme**: salınım tepe ve dipleri. Bir tepe, iki yanındaki 5 seanstan yüksektir ve ancak 5 seans sonra kesinleşir. Tavan/taban günlerinin tepe ve dipleri sayılmaz. Birbirine 0,5 ATR'den yakın tepe ve dipler tek seviyede birleşir. Her seviyenin yanında yazanlar:
  - dokunma sayısı;
  - kırılma sayısı: kapanışın seviyenin öbür yanına 0,5 ATR'den fazla geçmesi;
  - güç puanı (0–100): 100 × (1 − e^(−dokunma/2)) × e^(−yaş/252) × 0,5^kırılma. Formül sabittir, sonuçlara bakılarak değişmez.
- **pivot_gün / pivot_hafta**: klasik pivotlar, son günün ve önceki tamamlanmış haftanın yüksek, düşük ve kapanışından: P, R1, D1, R2, D2.
- **52h_zirve / 52h_dip**: 252 seansın en yükseği ve en düşüğü.
- **psikolojik**: fiyatın iki yanındaki yuvarlak sayı (270 TL'de 250 ve 300).
- **sma50 / sma200**: basit ortalamalar.

**Ortak kurallar:**
- Uzaklık, son kapanıştan ATR ve yüzde olarak verilir.
- Tür, son kapanışa göre belirlenir: altındaki seviye destek, üstündeki direnç. Kırılan direnç bu yolla desteğe döner.
- Hacim profili yoktur: gün içi veri olmadan yanıltıcı olur.

**Komutlar:**
- `/analyze THYAO` en yakın 3 destek ve 3 direnci, görünüm ve ATR satırlarına dokunmadan ekler.
- `/seviye THYAO` tam listeyi verir.

Seviyelerin tarihsel olarak rastgele seviyelerden ayırt edilip edilemediği ayrıca ölçülür (RESEARCH_LOG). Ölçüm sonucu çıkana kadar seviyeler yalnız "teknik seviye" olarak gösterilir.

**Günlük rapor:** her açık pozisyonun altında en yakın küme desteği bir bilgi satırı olarak yazılır. Mevcut ATR iz süren stop uyarısının yerine geçmez.

**Kayıt ve /durum:** her akşam rapordan sonra o günün küme seviyeleri, sonuç bilinmeden `logs/levels_log.csv`'ye yazılır. Kayıt yalnız ekleme yapar; bir gün bir kez yazılır. `/durum`'daki "Seviye hesabı" satırı son tarihi gösterir.

**/tara alanları:** `destek_uzaklik_atr`, `direnc_uzaklik_atr`, `seviye_gucu`, `kirdi_yukari(direnc)`, `kirdi_asagi(destek)`.
- Yalnız küme seviyeleri kullanılır.
- Her gün, o güne kadarki mumlarla hesaplanır. Karne bu alanları da geleceği görmeden hesaplar.
- Kırılma, dünkü en yakın seviyenin bugün 0,5 ATR'den fazla geçilmesidir.

