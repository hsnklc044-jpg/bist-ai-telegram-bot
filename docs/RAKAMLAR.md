# Rapordaki ve /durum'daki her satır: nereden geliyor, nasıl yanlış olabilir

Durum: v0.45.11. "Koruma" sütunu, hatayı yakalayan ya da görünür kılan mekanizmayı ve testini gösterir.

Fiyat türleri:
- **Ham (raw):** Yahoo'nun işlem fiyatı, iptal edilen seans çıkarılmış hâli (`daily.raw_bars`). Değer ve kâr/zarar bununla hesaplanır, çünkü defterdeki adetler bu fiyatlara karşılık gelir.
- **Düzeltilmiş (adjusted):** ham fiyata `data/corporate_actions.csv` uygulanmış hâli (`daily.adjusted_bars`). Göstergeler, uyarılar ve risk bununla hesaplanır, çünkü bölünme günlerinde sahte sıçrama olmamalı.
- **Kesinleşmiş mum:** iki fiyat türünde de yalnız kesinleşmiş mumlar kullanılır. Bir gün 18:15'ten sonra (yarım günde 13:15'ten sonra) kesinleşmiş sayılır (`calendar.drop_open_candle`).

## Günlük rapor (`core/reports/daily.py`)

| Satır | Nereden gelir | Nasıl hesaplanır | Nasıl yanlış olabilir | Koruma |
|---|---|---|---|---|
| Başlık "… DD.MM.YYYY kapanışı" | XU100'ün son kesinleşmiş mumu | Mumun tarihi | Yahoo geç kalırsa eski tarih yazar | Aynı veri günü ikinci kez gönderilmez (`runs.already_sent`); `logs/runs.csv`'ye `stale` yazılır, `/durum` "Fiyat verisi" UYARI verir (`test_runs`, `test_health`) |
| XU100 değeri ve günlük % | XU100 düzeltilmiş kapanışı | son / önceki − 1 | Yahoo'da tek günlük yanlış kapanış | XU100, 1202 gün boyunca İş Yatırım ile tutarlı (RESEARCH_LOG, 27.10) |
| "200 günlük ortalamanın %z üstünde/altında" | Son 200 XU100 kapanışı | kapanış / ortalama − 1 | 200 mumdan azsa satır hiç çıkmaz | — |
| Katılım | En az 200 mumu olan liste hisseleri | 50 ve 200 günlük ortalamanın üstündeki hisselerin oranı | Bugünkü listeyle hesaplanır (geçmişte listeden çıkanlar yok). Eski fiyatlı bir hisse eski kapanışıyla sayılır. Düzeltilmemiş bir bölünme sahte "ortalamanın altında" sonucu verir | Bölünme ve sıçrama denetimi (`market.quality`); düzeltme kayıt defteri (DATA_CORRECTIONS.md) |
| Sanal: "Değer X TL (nakit, hisse)" | Defter (`ledger.csv`, hesap `paper`) ve ham son kapanış | nakit = 100.000 + defterdeki tutarlar; hisse = Σ adet × son kapanış | Fiyatı olmayan hisse toplama girmez (Risk satırı "hesaplanamadı" der). Fiyat eskiyse "Güncel olmayan" satırında adı yazar. **Temettü nakde eklenmez (D13)** | `test_report_numbers.ReportByHandTest`; `HeldOutsideUniverseTest` (v0.45.2) |
| Gerçek: "Hisse değeri" | Defter (`real`) ve ham son kapanış | Σ adet × son kapanış | Nakit izlenmez. Fiyat yok ya da eski olabilir (yukarıdaki gibi) | aynı testler |
| "Günlük değişim" | `equity_log.csv` + defter | Gerçek hesap: (değer − aradaki alım/satım tutarı) / önceki kayıt − 1. Sanal hesap: değer / önceki − 1 | **Önceki kayıt dünden eskiyse (PC kapalıydı) birkaç günün toplamıdır ama "günlük" yazar (D14).** Temettü günü kayıp gibi görünür (D13) | `RealAccountFlowsTest` (v0.45.1) |
| Pozisyon satırı "adet × fiyat = değer (maliyet; ±TL / ±%)" | Defter (FIFO lotlar) ve ham son kapanış | maliyet = alış tutarı + alış komisyonu; kâr = değer − maliyet; % = kâr / maliyet | Bedelsiz/bedelli deftere girilmemişse adet ve kâr yanlış görünür. Fiyat eskiyse kâr da eskidir | Defterde işlem satırı yoksa "defter_islem" uyarısı; `test_ledger` (FIFO, bedelsiz, bedelli) |
| Risk: 1 günlük kayıp (%95 tarihsel) | Düzeltilmiş getiriler, son 250 ortak seans | Bugünkü ağırlıklarla geçmiş günlük sonuçların %5'lik dilimi; hesabın payı ve TL | Geçmiş 250 seans geleceği temsil etmeyebilir. 60'tan az ortak seans varsa "hesaplanamadı" yazar. Yeni halka arz hisseler ortak dönemi kısaltır | `RiskByHandTest` (el hesabı), `test_portfolio_risk` |
| Etkin pozisyon sayısı | Pozisyon değerleri | 1 / Σ(pay²); paylar nakit hariç, yatırılan tutara göre | Fiyatı olmayan pozisyon varsa hesaplanmaz | `test_effective_n_ignores_cash`, `RiskByHandTest.test_equal_holdings` |
| En yüksek korelasyon | Son 60 ortak seansın düzeltilmiş getirileri | İkili Pearson korelasyonu | Kısa geçmişte gürültülüdür. Hiç oynamayan hissede tanımsızdır (gösterilmez) | `test_portfolio_risk` |
| Risk uyarıları (🆕/⬆️/✅) | Düzeltilmiş mumlar ve `alerts_log.csv` | Kurallar ve eşikler `core/config/alerts.py`'de: stop (en yüksek kapanış − 2 ATR), taban kilidi, parabolik yükseliş, likidite, %25 yoğunlaşma, %15 zirveden düşüş, 5 günden eski veri | `/report` uyarıları gösterir ama kayda geçirmez; "🆕" işareti 18:30 raporunda yine görünür (v0.45.11). Eski veride uyarı da eskidir | "veri" uyarısı; `test_alerts` |
| Sanal emirler "#id … X TL'den alındı (açılış + kayma, komisyon)" | `paper_orders.csv`, ham mumlar | Fiyat = açılış × (1 ± %0,05), komisyon = fiyat × adet × %0,1. 09:40'tan önce verilen emir aynı gün, sonra verilen ertesi seans dolar. Tavan veya taban kilidinde beklenir | Yahoo'nun "açılış" değeri gerçek açılış seansı fiyatından farklı olabilir. Dolduktan sonraki bir temettü geçmiş açılışı Yahoo'da değiştirir; deftere yazılan fiyat değişmez | `test_paper` (dolum zamanı, kilit, tek dolum, çift yazma koruması) |
| Veri notları: Verisi olmayan / Güncel olmayan | Fiyat deposu | Mumu olmayan liste hisseleri; son mumu 5 takvim gününden eski olan liste hisseleri ve pozisyonlar | Uzun tatilde 5 gün eşiği kısa kalabilir | `HeldOutsideUniverseTest.test_stale_held_stock_is_named` |
| Veri notları: "… okunamadı (satır N …)" | Bozuk `equity_log` ya da `alerts_log` | Dosyaya dokunulmaz, rapor devam eder | — | `test_corrupt_files.DailyReportTest` |
| Canlı ölçüm (cuma) | `signal_log.csv` | 20 seanslık ortalama fark; durum (gün sayısı ya da bağımsız dönem) | Kayıtlar 26.10.2026'da başladı: örneklem küçük | Bağımsız dönem kuralı (v0.45.3) |
| 💾 Yedek | `create_backup` | Kişisel dosyalar SHA-256 manifestli zip'e konur ve geri okunarak doğrulanır | Yedek klasörü verilerle aynı diskteyse ikisi birlikte kaybolabilir | `/durum` "Yedek" uyarısı (v0.43.0); `test_backup` |
| 🔁 Haftalık geri yükleme testi | `backup_market_db` + `test_restore` | En yeni iki yedek geçici klasöre açılıp her dosya kendi koduyla okunur | Yalnız en yeni yedekler denenir | `test_backup_restore` |
| ⚠️ sağlık satırları | `bot_check`, `database_check`, `disk_check`, `schema_check` | Yalnız sorunlu olanlar eklenir | — | `test_health_ops.ReportWarningsTest` |

## /durum (`core/reports/health.py`)

Durumlar: SAĞLIKLI / UYARI / KRİTİK / BİLİNMİYOR. Kontrol yapılamadıysa durum BİLİNMİYOR olur, hiçbir zaman SAĞLIKLI değil.

| Satır | Nereden gelir | Kural | Nasıl yanlış olabilir |
|---|---|---|---|
| Telegram botu | `logs/heartbeat.txt` | Son sinyal 20 dakikadan yeniyse SAĞLIKLI; dosya yoksa BİLİNMİYOR | Bot kilitlenip zamanlayıcı çalışmaya devam ederse yanlış SAĞLIKLI görünür |
| Günlük rapor | `logs/runs.csv` | Kesinleşmiş son seans + 1 saat 15 dakika içinde gönderim, tatil ya da atlama kaydı yoksa KRİTİK; son çalışma hata verdiyse KRİTİK | Windows görevi `runs.csv`'yi başka bir klasöre yazıyorsa rapor gitmiş olsa da KRİTİK görünür |
| Fiyat verisi | XU100'ün son mumu | Beklenen son seansın gerisindeyse UYARI | Tatil dosyası eksikse beklenen gün yanlış hesaplanır ("Tatil takvimi" satırı uyarır) |
| Fiyat veritabanı | `market.db` | Salt okunur `PRAGMA quick_check`; başka bir işlem yazıyorsa UYARI | `quick_check` her bozukluğu bulmaz (`integrity_check` haftalık geri yükleme testinde çalışır) |
| Canlı ölçüm kaydı | `signal_log.csv` | Tekrar eden, okunamayan, eksik ve geç kayıtlar; 0 baytlık dosya | — |
| Sanal hesap kaydı | `equity_log.csv` | Sanal hesabın son değeri | Satır okunamazsa UYARI |
| Veri şeması | Kişisel dosyaların başlık satırları | Bu sürümün okuduğu sütunlardan biri eksikse KRİTİK | Yalnız başlığa bakar; satır içeriğini "Kişisel dosyalar" denetler |
| Kişisel dosyalar | ledger, emirler, hesap kaydı, uyarı kaydı, takip listesi | Her biri son satırına kadar okunur; bozuk satır, dosya ve satır numarasıyla KRİTİK | — |
| Yedek | Yedek klasörü | 4 günden eskiyse UYARI, 10 günden eskiyse KRİTİK; verilerle aynı diskteyse UYARI (sunucuda `pulled.txt` 8 günden yeniyse SAĞLIKLI) | Bulut klasörü yalnız yolun adından tanınır; eşitlemenin gerçekten çalıştığı kontrol edilmez |
| Disk | Veri klasörünün diski | 1 GB'tan az boş alan UYARI, 200 MB'tan az KRİTİK | — |
| Tatil takvimi | `bist_holidays.csv` | İçinde bulunulan yıl yoksa BİLİNMİYOR; aralıkta ertesi yıl eksikse UYARI | Dosya elle güncellenir |
| GitHub araştırması | GitHub API (token gerekmez) | Son tamamlanan çalışma başarısızsa ya da 8 günden eskiyse UYARI; çevrimdışıyken BİLİNMİYOR | Elle başlatılan başarılı bir çalışma, başarısız bir zamanlanmış çalışmayı gizleyebilir |
