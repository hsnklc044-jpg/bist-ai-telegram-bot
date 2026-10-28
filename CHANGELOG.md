# Sürüm geçmişi

Sade dille: ne değişti, nasıl doğrulandı. Her sürüm CI'da (ruff, tüm testler, v0.54.1'den beri kapsam ≥ %91) geçti; aksi yazılıysa o sürüm kırmızıydı ve bir sonraki düzeltti. Daha eski sürümler: `git log`.

## v0.92.0 – 28.10.2026 (Özellik A: destek/direnç seviyeleri, hesap ve görünüm)
- `core/analytics/levels.py` eklendi (K-49 tasarımıyla birebir): salınım tepe/dip (N=5, kesinleşme 5 seans sonra, tavan/taban günleri hariç), 0,5 ATR kümeleme, kırılma sayısı, sabit güç puanı, klasik günlük ve haftalık pivotlar, 52 hafta, psikolojik seviye, sma50/200.
- `/seviye THYAO` tam listeyi veriyor. `/analyze` en yakın 3 destek ve 3 direnci ekliyor; görünüm ve ATR satırları değişmedi.
- Doğrulama: `test_levels`. Elle hesaplanan küçük örnekler (fraktal, kümeleme, kırılma, pivot, yuvarlak sayı, güç) ve geleceği görme testi: gelecek değişse de seviyeler aynı.

## v0.91.2 – 28.10.2026 (öz-denetim 7)
- v0.87.0–v0.91.1 denetlendi: kritik ya da yüksek bulgu yok. Düşük bulgular Ö22–Ö26 (ROADMAP).
- Veri borcu kapısı açıldı. Açıklama çalışması (`screens.yml`, 3beeba3) karnenin dışarıda bıraktığı yalnız PAHOL'u gösteriyor (kısa geçmiş).

## v0.91.1 – 28.10.2026 (dışarıda kalan hisselerin nedeni)
- Karne ve araştırmanın dışarıda bıraktığı hisseler artık nedenleriyle yazılıyor: çözülmemiş sıçrama (tarihleriyle), kısa geçmiş (mum sayısı) ya da veri yok. Böylece veri borcunun kapandığı doğrudan görülebiliyor.
- İkinci kaynak doğrulaması (v0.91.0 satırları): 10 hisse, 11.954 hisse-gün, açıklanamayan fark 2 gün (DATA_CORRECTIONS).

## v0.91.0 – 28.10.2026 (veri borcu: 12 sıçrama, KERVT, KPOWR)
- `corporate_actions.csv`'ye 10 kaynaklı satır eklendi: ADEL, BJKAS×2, EUREN, FENER 2024, GSRAY×2, TSPOR×2, TUKAS.
- TSPOR'un 2025'teki birleşik işlemi (sermaye azaltımı + bedelli) için yeni satır türü eklendi: `reduction_rights`.
- Yeni `data/candle_exceptions.csv`: ASUZU'nun bozuk mumu atılıyor, GOLTS'un eksik yarım gün üstündeki gerçek hareketi sıçrama sayılmıyor.
- KERVT → BESLR kod eşlemesi eklendi. KPOWR rapor evreninden çıkarıldı (hiçbir kaynakta yok).
- Doğrulama: `test_candle_exceptions`, `test_corrections` (azaltım+bedelli formülü elle). İkinci kaynak karşılaştırması Actions'ta (DATA_CORRECTIONS).

## v0.90.1 – 28.10.2026 (tasarım: destek/direnç seviyeleri)
- K-49: Özellik Talimatı A'nın tasarımı sonuç görülmeden yazıldı. Kapsadığı: yöntemler (fraktal N=5, 0,5 ATR kümeleme, klasik pivotlar, 52 hafta, psikolojik, ortalamalar), sabit güç formülü, kırılma ve rol değişimi tanımı, anlamlılık ölçümü ve canlı kayıt. Kod, veri borcu kapısı açılınca yazılacak.

## v0.90.0 – 28.10.2026 (profesyonel filtreler Aşama 3: yayın tarihli temel veri deposu)
- `data/fundamentals.csv` deposu eklendi: her kalem yayın tarihiyle; yalnız ekleme; yedekte; şema denetimli; git'e girmez.
- Bir seans, bir kalemi yalnız yayın gününden sonraki seanstan itibaren görür (`as_of`, `panel`). Düzeltilmiş tablolar yeni satır olarak eklenir. TMS 29 tabloları işaretli.
- Veri girişi denetimli dosya içe aktarmasıyla yapılıyor. Ağ kodu yok: KAP koşulları teyit edilene kadar otomatik çekme kapalı (K-48).
- İkinci kaynakla fark raporu var (`--compare`).
- `/durum`'a "Temel veri" satırı eklendi; depo boşken bilgi satırıdır.
- Doğrulama: `test_fundamentals_store`. Kapsananlar:
  - geçersiz satırlar nedeniyle reddediliyor;
  - yalnız ekleme, aynı satır iki kez yazılmıyor;
  - yayın akşamı kullanılmıyor, ertesi seans kullanılıyor;
  - düzeltilmiş tablonun sonraki yayını geçerli;
  - kapsam satırı, karşılaştırma, yedek/şema/gitignore.

## v0.89.2 – 28.10.2026 (karar: temel veri kaynağı; keşif karşılaştırması)
- K-48: temel veri kaynağı KAP. Toplu otomatik çekme, kullanım koşulları teyit edilene kadar kapalı; İş Yatırım seçilmedi (robots.txt `/_layouts/` yasağı).
- Denetime D13 eklendi: mevcut ikinci fiyat kaynağı İş Yatırım'ın yasak yolunda; karar kullanıcıda.
- RESEARCH_LOG: profesyonel şablonlar ve eleme grupları, kullanıcının PC keşif sayılarıyla karşılaştırıldı. Yön aynı; elenen grup −%4,1, kalan −%0,3.

## v0.89.1 – 28.10.2026 (açıklama: eleme grupları)
- `templates --explain` (`screens.yml`) artık elenen ve kalan hisse-günlerin 20 seanslık olay ortalamasını da yazıyor (maliyet hariç). Kullanıcının PC keşfindeki "elenen grup" sayısıyla karşılaştırma içindir; seçim için kullanılmaz.

## v0.89.0 – 28.10.2026 (profesyonel filtreler Aşama 2: teknik şablonlar)
- Yeni şablonlar, her biri kaynağı ve reddedilmiş türüyle:
  - `minervini`: Minervini 2013, trend şablonu;
  - `zirveye_yakin`: George & Hwang 2004;
  - `goreli_guc_ust`: Jegadeesh & Titman 1993, 6-1 momentum;
  - `dusuk_oynaklik`: Ang ve diğ. 2006, Blitz & van Vliet 2007.
- Yeni alanlar: `sma150`, `zirve_52h`, `dip_52h`, `zirve_52h_oran`, `dip_52h_oran`, `egim(alan,n)`, `getiri_6a_1a_haric`, `getiri_12a_1a_haric`, `oynaklik_60g`, `rs_puan` ve evren içi sıralar `goreli_guc_yuzdelik`, `momentum_sira`, `oynaklik_sira`.
- Evren içi sıra hesabı tek yerde. Liste, karne ve açıklama aynı yöntemi kullanıyor.
- HANDBOOK'a "Profesyonel filtreler ve elemeler" bölümü eklendi: kaynak, ne seçtiği, BIST'teki durum, sınırlar (K-47).
- Doğrulama: `test_screen_pro_fields`. Her alan elle hesapla ya da ta ile birebir eşit; `egim` dili; sıralar listede ve karnede her gün.

## v0.88.2 – 28.10.2026 (D11 yarım gün yanlış alarmı, D12 karne sırası)
- **D11:** yarım günde /durum 14:30'dan itibaren "rapor gitmedi", "fiyat 1 seans geride" ve "kaydı olmayan seans" diyordu. Artık hepsi tek fonksiyonla raporun saatini esas alıyor: 18:30 + 1:15, yarım gün dahil, tatil hariç.
- **D12:** /tara'da yavaş makinede karne listeden önce gidip "Önce /tara ile bir tarama yap." diyebiliyordu. Karnenin mesajı artık her zaman listeden sonra gidiyor.
- CI'a "yavaş makine" işi eklendi: tek meşgul çekirdek, iki rastgele test sırası. Kilit testi uykudan olaya geçirildi.
- AUDIT.md'de PC satırları doğrulandı: kişisel kayıtlar, sanal portföy, yedek SHA testi, PC sürümü.
- Doğrulama:
  - `test_report_due`: 28.10 14:30 ve 18:00 SAĞLIKLI, 19:45 KRİTİK; normal gün 18:00 SAĞLIKLI; 29.10 bayram bir şey beklemiyor.
  - `test_screen_telegram`: karne listeden önce biterse de sıra doğru, 50 tekrar.

## v0.88.1 – 28.10.2026 (veri: FENER ve CVKMD bedellileri)
- `corporate_actions.csv`'ye 3 kaynaklı satır eklendi: FENER 23.06.2025 (%400, 1 TL), FENER 29.12.2025 (%400, 2 TL), CVKMD 03.08.2026 (%170, 1 TL). Kaynaklar: KAP 1452776, 1466238, 1656455 ve KAP'ı aktaran bir haber (DATA_CORRECTIONS).
- Bu iki hisse artık /tara'da "düzeltilmemiş sıçrama" nedeniyle elenmeyecek. Doğrulama: ikinci kaynakla karşılaştırma (Actions `datacheck`).

## v0.88.0 – 28.10.2026 (profesyonel filtreler Aşama 1: eleme filtreleri)
- Her /tara sonucuna varsayılan dört eleme uygulanıyor:
  - **likidite:** önceki 20 seans ortalaması < 15 mn TL;
  - **kurumsal işlem:** son 60 seansta kayıtlı bedelli, bedelsiz/bölünme ya da halka arz;
  - **aşırı hareket:** 10 seansta 3 tavan/taban ya da listenin en oynak %5'i;
  - **veri sorunu:** düzeltilmemiş sıçrama, sıfır hacim ya da ikinci kaynak farkı.
- Elenen her hisse nedeniyle tek satırda yazılıyor. `ele=hayir` hepsini, `ele_likidite=0`, `ele_kurumsal=0`, `ele_hareket=0`, `ele_veri=0` tek tek kapatıyor.
- Karne aynı elemeleri her gün o günün verisiyle uyguluyor. `/tara_aciklama` eleme nedenini gösteriyor. Sanal köprü de aynı elemeleri kullanıyor (K-45).
- Öz-denetimdeki D2 (yakın tarihli sıçrama) ve D3 (sıfır hacim) bulguları bu sürümle eleme olarak kapandı.
- Doğrulama: `test_screen_elimination` (her kural, kapatma seçenekleri, karnede gün gün uygulama ve geleceği görmeme). Eleme konusu olmayan eski testler `ele=hayir` ile açıkça yazıldı.

## v0.87.0 – 28.10.2026 (öz-denetim 6 = EVRE 0 denetimi)
- `docs/AUDIT.md`: mevcut sistemin kanıta dayalı durum raporu. Neyin doğrulandığı, neyin eksik olduğu, neyin buradan doğrulanamadığı (PC'deki kişisel kayıtlar, sanal portföy, yedekler) ayrı ayrı yazıldı.
- **Hata düzeltmesi (D1):** /tara karnesi, araştırmanın dışarıda bıraktığı çözülmemiş sıçramalı ya da kısa geçmişli hisseleri de sayıyordu. Artık aynı hisseleri dışarıda bırakıyor; şablon karneleri hangilerini bıraktığını yazıyor. Eski karne önbelleği geçersiz sayılıyor ve yeniden hesaplanıyor.
- Paket güvenlik taraması ilk kez çalıştırıldı: temiz.
- Doğrulama: `test_screen_card_jumps`.

## v0.86.1 – 28.10.2026 (/tara Aşama 6: kalite ve belgeler)
- `test_screen_quality` eklendi. Denetledikleri:
  - Telegram menü sınırları ve tüm `/tara` komutlarının menüde olması;
  - HANDBOOK'taki BotFather listesinin menüyle aynı olması;
  - CHARTER §9: `core/screen`'de emir, defter ve token yok; metinlerde öneri dili yok; son satır sabit.
- HANDBOOK'a "CHARTER §9 uyumu (/tara)" bölümü ve BotFather listesi yazıldı.
- /tara görev paketi Aşama 1–6 tamamlandı. Kalan iş: K-36 evren kararı (Kasım sonu) ve BIST30 listesi (kaynak gerekiyor).

## v0.86.0 – 28.10.2026 (/tara Aşama 5: görev şablonları ve reddedilmiş türler)
- `/tara_sablonlar`'a görevin beş örnek şablonu eklendi: `trend_takibi`, `asiri_satim`, `kirilim`, `sikisma`, `goreli_guc`.
- Her şablon ait olduğu reddedilmiş araştırma türünü gösteriyor: "bu tür 27.10.2026'da test edildi, XU100'ü geçmedi" (K-44).
- Doğrulama: `test_screen_templates` (koşullar verildiği gibi; her tür RESEARCH_LOG tablosunda var).

## v0.85.0 – 28.10.2026 (/tara Aşama 4d: sanal köprü + şablon farkları)
- `/tara_sanal AD` (varsayılan kapalı): kayıtlı bir tarama ya da şablon, önceden yazılmış kurallarla ölçüm amaçlı bir sanal kitapta işliyor. Kurallar: eşit ağırlık, en çok 5 pozisyon, 20 seans, 2 ATR stop, ertesi açılış.
- Sonuç `/performans`'ta "SANAL" etiketiyle görünüyor. Kişisel `/paper` emirlerine ve deftere dokunmuyor (K-43).
- RESEARCH_LOG: şablon karnelerimizi senin PC sayılarınla karşılaştırdım. Hükümler aynı: hiçbir şablon XU100'ü geçmiyor. Farkın nedenleri:
  - maliyet;
  - olay ve gün ortalaması;
  - 10/20 günlük hacim tanımı (düşeni kıranda en büyük etki);
  - likidite tabanı etkisiz;
  - örnek sayısı farkı açık.
- Doğrulama: `test_screen_virtual`. Kapsananlar:
  - varsayılan kapalı ve kapalıyken fiyat okunmuyor;
  - ertesi açılışta giriş, 20 seansta çıkış, en çok 5 pozisyon, stop;
  - başlangıçtan önceki sinyal yok sayılıyor;
  - geleceği görme yok;
  - `paper_orders` oluşmuyor;
  - yedek, şema ve gitignore.

## v0.84.1 – 28.10.2026 (şablon farklarının açıklaması)
- `python -m core.screen.templates --explain` ve elle başlatılan `screens.yml` iş akışı eklendi. Her şablonu, kullanıcının PC denemesinden farklı olabilecek tanımlarla yeniden hesaplıyor: likidite tabanı, 10/20 günlük göreli hacim, maliyet hariç/dahil, olay ve gün ortalaması. Yalnız açıklama içindir; şablonlar değişmiyor.

## v0.84.0 – 28.10.2026 (/tara Aşama 4c: /performans "Taramalar")
- `/performans` artık her zaman bir "Taramalar" bölümü gösteriyor. Her /tara kriteri için kayıttan sonraki 5 ve 20 seanslık getiri, kriter özetiyle birlikte yazılıyor. 30'dan az olgun örnek varsa sayı yok, "veri birikiyor (n/30 örnek)" yazıyor.
- Doğrulama: `test_screen_performance`.

## v0.83.0 – 28.10.2026 (/tara Aşama 4a–4b: kayıt listesi, silme, abonelik)
- `/tara_abone AD`: kayıtlı tarama ya da şablon her işlem günü 18:30 raporundan sonra çalışıyor. Yalnız giren/çıkan hisseler gönderiliyor; değişiklik yoksa mesaj yok. Rapor gitmeyen gün (tatil) çalışmıyor. `/tara_abonelikler` ve `/tara_abone_iptal AD` de eklendi. Kayıtlar yeni kişisel dosya `data/screen_subscriptions.csv`'de (yalnız ekleme, yedekte, `/durum` denetler; K-42).
- `/tara_liste` kayıtlı taramaları gösteriyor. `/tara_sil AD` bir taramayı siliyor.
- Silme dosyaya boş koşullu bir satır ekliyor; önceki satırlar değişmiyor. Silinen tarama 20'lik sınıra sayılmıyor, ad yeniden kullanılabiliyor.
- `data/screens.json`'a geçilmedi, kayıtlar `data/screens.csv`'de kalıyor (K-41).
- Doğrulama: `test_screen_saved`, `test_screen_subscriptions` (yalnız değişiklik, aynı gün bir kez, tatilde yok, hata raporu durdurmuyor, yedek/şema/gitignore). Silme yalnız ekliyor; eski sürümün yazdığı dosya aynen okunuyor; silinen ad çalışmıyor; komutlar menüde.

## v0.82.1 – 28.10.2026 (şablon görevi Aşama D: temel veri, yalnız tasarım)
- Temel veri kaynakları için seçenekler DECISIONS K-40'a yazıldı: KAP, İş Yatırım, Yahoo, ücretli sağlayıcılar ve kendimiz hesaplamak. Her birinin lisansı, güncelliği, geçmişi ve kapanmış şirketleri kapsayıp kapsamadığı not edildi. Kod yazılmadı; uygulama ayrı bir karar.
- Tek Tuş Trend şablonundaki not düzeltildi: beta fiyattan hesaplanıyor ve `/tara`'da zaten var.

## v0.82.0 – 28.10.2026 (şablon görevi Aşama C: karne)
- Güven aralığı gün ortalamasıyla hesaplanıyor: her gün bir kez sayılıyor, 20 seanslık bloklarla. Böylece aynı gün çok sinyal veren günler sonucu tek başına sürükleyemiyor.
- Yeni "tüm hisseler" satırı: koşulsuz ortalama ve koşulun ondan farkı. Sonuç maliyet hariç ve dahil yan yana yazıyor.
- Eski biçimde önbelleğe alınmış karneler kendiliğinden yenileniyor.

## v0.81.0 – 28.10.2026 (şablon görevi Aşama B: hazır şablonlar)
- `/tara_sablonlar`: TradingView taramalarının teknik kısmından altı hazır şablon. `/tara duseni_kiran` gibi adıyla çalışıyor.
- Her şablonda kaynağı, atlanan koşullar (temel veri yok) ve karnesi yazıyor. Karneler önceden hesaplandığı için liste beklemiyor.
- Şablonlar filtre şablonudur, öneri değildir. Sonuçlara bakılarak ayarlanmazlar ve araştırma programına aday kural olarak girmezler.

## v0.80.0 – 28.10.2026 (şablon görevi Aşama A + öz-denetim 5)
- TradingView adlarıyla yeni alanlar: `goreli_hacim` (10 gün), `momentum10`, `vwma20`, `ortalama_hacim_30g` (adet), `likidite` (TL), `degisim_1h/1a/3a`, `zirve_1a`. Taramalar TradingView'daki gibi yazılabiliyor.
- `ema(n)` ve `sma(n)` için geçerli dönemler: 5, 10, 20, 40, 50, 100, 200. Başka bir değer yazılırsa hata mesajı geçerli değerleri listeliyor. Girdi sınırı 400 karakter.
- Öz-denetim 5 bulguları:
  - Karne artık listedeki likidite tabanını da uyguluyor; önceden listede hiç görünmeyecek sığ hisseleri sayıyordu.
  - Karne önbelleği 500 kayıtla sınırlandı.
  - Kritik ya da yüksek bulgu yok.

## v0.79.0 – 28.10.2026 (PC'deki gerçek veri bulguları)
- `/tara` artık gerçekten bugünkü BIST 100'ü (100 hisse, resmi üyelik) tarıyor. Eskiden "BIST 100" yazıp 118 hisselik rapor listesini tarıyordu. O liste `evren=quantbist` seçeneği olarak kaldı.
- Günlük fiyat güncellemesi bugünkü BIST 100'ün tamamını kapsıyor. Daha önce 14 üye eksikti: HALKB, VAKBN, ZOREN ve diğerleri.
- ATR uyarısı eklendi: son 14 seansta limit dışı ya da sert bir fiyat hareketi varsa satırda ⚠️ yazıyor. ANELE'nin %45'lik ATR'si veri hatası değil; beş gün taban, iki gün tavan yapmış ve iki kaynak birebir aynı.

## v0.78.0 – 28.10.2026 (/tara Aşama 3: dürüst karne)
- Karne artık işlem maliyetini düşüyor (gidiş-dönüş %0,30). Giriş ertesi seansın açılışından yapılıyor.
- Karnede yeni ölçüler: ortalama ve medyan, isabet, örnek ve bağımsız olay sayısı (bir hissenin çakışan sinyalleri bir sayılıyor), %95 güven aralığı, en kârlı 5 hisse çıkarılınca sonuç.
- Etiketler hiçbir zaman "başarılı" demiyor. Aralık olumlu çıksa bile "çoklu deneme nedeniyle şans olabilir, kanıt değildir" yazıyor.
- Kaç farklı kriter denendiği sayılıyor ve karnede veri gözetlemesi uyarısı olarak gösteriliyor.
- Karne önbelleğe alınıyor. Hesap 60 saniyeyi geçerse liste hemen geliyor, karne ayrı mesajla.

## v0.77.0 – 28.10.2026 (/tara Aşama 2: Telegram arayüzü)
- Yeni komutlar: `/tara_alanlar` (tüm alanlar ve birimleri), `/tara_aciklama THYAO rsi<30` (o hissede her koşulun değeri ve sağlanıp sağlanmadığı), `/tara_devam` (sonraki 15 satır).
- Cevabın altında Devam, Karne ve Kaydet düğmeleri var. Uzun cevaplar satırlar bölünmeden parçalanıyor.
- Sonuç boşsa koşul hunisi gösteriliyor: hangi koşul kaç hisse bıraktı, en çok eleyen hangisi.
- Kullanıcının dört TradingView taraması kabul ölçütü oldu. Bunlar için yeni alanlar eklendi: CCI, VWMA, momentum, beta, getiri(n), ortalama hacim (adet), hacim değişimi, hacim_oran(n). Koşul sınırı 15'e çıktı. Karşılık tablosu HANDBOOK §8'de.

## v0.76.0 – 28.10.2026 (/tara Aşama 1: motor)
- `/tara` yeni motora geçti. Yaklaşık 40 alan var: trend, momentum, oynaklık, hacim, göreli güç ve fiyat konumu (tam liste HANDBOOK §8).
- Yazımda yeni olanaklar: aralık (`rsi 30..50`), kesişim (`kesti_yukari(ema20,ema50)`), pencere (`son(5, ...)`), `ve / veya / değil` ve parantez. Hatalı yazımda hatanın yeri gösteriliyor ve en yakın alan öneriliyor ("'rsi' mi demek istediniz?").
- Evren ve eleme: `evren=izleme` seçeneği eklendi. Likidite tabanı varsayılan olarak açık (10 mn TL, `likidite=0` kapatır). Verisi eski ya da düzeltme bekleyen hisseler adlarıyla yazılıyor.
- Göstergeler canlı analizle birebir aynı hesaptan geliyor. Teknik puanın ATR hesabı da hızlandı; sonuç bit bit aynı.
- Satırlarda 1 ve 2 ATR mesafesi var. Seans sürerken çalıştırılırsa cevap hangi kapanışa göre olduğunu yazıyor.

## v0.75.0 – 28.10.2026
- `/tara`: BIST 100'ü kendi gösterge koşullarınla filtreleyebilirsin (ör. `/tara rsi<30 ema20>ema50`). Desteklenen alanlar:
  - RSI, EMA20/50, MACD ve sinyal çizgisi
  - hacim oranı, ATR yüzdesi
  - 5 ve 20 seans getiri, XU100'e göre göreli güç, kapanış
- Her hisse için sağladığı koşullar, kapanış, 1 ATR risk mesafesi ve 20 günlük ortalama TL işlem gösteriliyor; en fazla 15 satır.
- Listenin altında geçmiş karne var: 2023-08 – 30.10.2026 verisi, holdout kullanılmıyor. Karne bir kanıt değil, yalnızca bir özet.
- Sonuçlar canlı ölçüme kaydediliyor; `/performans` her kriterin 5 ve 20 seanslık sonucunu gösteriyor.
- Taramalar `/tara_kaydet` ile kaydedilebiliyor; kayıtlar yedeğe giriyor.
- Filtre sonucudur, yatırım önerisi değildir.

## v0.74.0 – 28.10.2026
- Haftalık araştırmaya "kanıtlar yan yana" raporu (`triage.txt`) eklendi. Bir hissede kurumsal işlem şüphesi çıkınca rapor KAP'taki sermaye bildirimlerini ve İş Yatırım'ın aynı gündeki hareketini birlikte gösteriyor; iki kanıt da varsa hazır bir öneri satırı yazıyor. Bugün SKBNK'yı elle çözmek birkaç adım sürdü; bundan sonra aynı iş tek okumada biter. Hiçbir şey otomatik uygulanmıyor.

## v0.73.1 – 28.10.2026
- SKBNK'nın %40 bedelli sermaye artırımı düzeltmesi doğru güne (19.10) taşındı. Önceki kayıt (22.10) düzeltilmiş seride iki sahte hareket üretiyordu. Doğrulama: KAP'ın kendi metni (yeni araçla getirildi) ve Yahoo ile İş Yatırım'ın aynı gün gösterdiği fiyat kopukluğu.

## v0.73.0 – 28.10.2026
- KAP bildiriminin metni artık GitHub'dan getirilebiliyor: `kap.yml` iş akışına bildirim numarası verilince metni research-results dalına yazılıyor. Bir şirket işleminin tarihi elle KAP'ta aranmak yerine KAP'ın kendi metninden doğrulanıyor. İlk kullanım: SKBNK bedelli tarihi.

## v0.72.1 – 28.10.2026
- İkinci kaynak kontrolü düzeltildi. Yahoo'nun henüz yayımlamadığı son seansı "fark" sayıyordu. 28.10 çalışmasında 118 hissenin 117'si bu yüzden "fark var" göründü; veri doğruluğu SLO'su yanlışlıkla kötü çıkacaktı. O gün artık "henüz yayımlanmamış" diye ayrı yazılıyor ve bir sonraki çalışmada karşılaştırılıyor.

## v0.72.0 – 28.10.2026
- Öz-denetim 4 (v0.64–v0.71): bir orta bulgu düzeltildi. Sunucu kararı hesabı gece kapanan PC'nin kaybını PC'ye saymıyordu (yalnız uykuyu sayıyordu); artık 20 dakikadan uzun her kesinti de sayılıyor. Kritik ya da yüksek bulgu yok.

## v0.71.0 – 28.10.2026
- `/alarm THYAO altında %5`: seviye yerine yüzde yazılabiliyor. Alarm son kapanışın %5 altına (ya da `üstünde %10` ile %10 üstüne) kurulur. Onay mesajı hesaplanan seviyeyi ve hangi kapanıştan hesaplandığını yazar.

## v0.70.0 – 28.10.2026
- Sunucu kararı artık hesaplanıyor. 13.11 akşam raporu, 27.10'da önceden yazılan ölçüte göre "sunucu önerilir" ya da "PC'de kalınır" kararını kendisi yazacak. Yalnız PC kaynaklı kayıplar sayılıyor: uyku, kapalı kalma, rapor görevinin geç başlaması. Ara durum: `python -m core.reports.server_decision`.

## v0.69.0 – 28.10.2026
- `/performans`: bir görünümün canlı sonucu geçmişten anlamlı saparsa altında "neden?" satırları çıkar. Sistem dört olası nedeni kendisi sınar: sapma birkaç hisseden mi, tek bir günden mi geliyor; piyasa geçmişten farklı mıydı; ölçülen hisselerde kurumsal işlem var mıydı. Sapma yokken hiçbir şey eklenmez.

## v0.68.1 – 28.10.2026
- v0.66–v0.68 toplu taramasında iki düzeltme:
  - Güncelleyici, GitHub API'ye özel başlığı zip ve sürüm dosyası isteklerine de gönderiyordu. Zip indirme bu başlıkla hiç denenmemişti; ilk gerçek kurulumda reddedilebilirdi. Başlık artık yalnız API isteğinde.
  - Alarm dosyası bozuksa `/alarm` cevap vermek yerine hata veriyordu. Artık dosyanın okunamadığını söylüyor ve dosya düzelene kadar hiçbir şey yazmıyor.

## v0.68.0 – 28.10.2026
- PC güncelleyicisi depoya alındı (`scripts/guncelle.py`, `scripts/bildir.py`). Artık yalnız GitHub'da CI'ı yeşil olan sürümü kuruyor ve her sonucu (kuruldu, kurulmadı, geri alındı, hata) Telegram'a "🤖 Otomasyon" olarak yazıyor. Yeni sürüm yoksa sessiz kalıyor.

## v0.67.0 – 28.10.2026
- Araştırma döngüsü a4 ön kayda alındı (H4 eşit ağırlık, H5 düşük işlem hacmi). Kurallar yazıldı ve yalnız yapay veriyle test edildi. Haftalık araştırma bu taramayı ön kaydın izin verdiği 27.04.2027'den önce çalıştırmaz; o tarihten sonra kendiliğinden çalıştırıp sonucu `a4` ailesi olarak kaydeder.

## v0.66.0 – 28.10.2026
- `/alarm THYAO altında 240` (ya da `üstünde`): kapanış fiyatı alarmı. Akşam raporu o günün kapanışıyla kontrol eder ve geçen alarmı bir kez "🔔" satırıyla söyler. `/alarm` listeler, `/alarm sil 1` siler. Gün içi fiyat izlenmez. Kayıt `data/price_alarms.csv` (yalnız ekleme, günlük yedekte, `/durum` sağlam okunduğunu kontrol eder).

## v0.65.0 – 28.10.2026
- Cuma raporuna eğilim satırı: sanal hesap ve XU100'ün son 20 seansı yan yana küçük metin grafiğiyle (▁▂▃▅▇) ve yüzde değişimle.

## v0.64.0 – 28.10.2026
- `/stres [sanal]`: stres testi. Açık pozisyonlar XU100'ün kayıtlı geçmişindeki en kötü 1, 5 ve 20 seanslık düşüşlerini yaşasaydı her hisse kendi o günkü getirisiyle ne kaybederdi. Dönemleri veri kendisi bulur; bilgi amaçlıdır.

## v0.63.1 – 27.10.2026
- Öz-denetim 3: kritik ya da yüksek bulgu yok. KAP bir hafta için beklenmedik cevap verirse haftalık kontrol artık çökmüyor; atlanan aralık çıktıda "Eksik kontrol" diye yazıyor.

## v0.63.0 – 27.10.2026
- `/yil [2026] [gerçek|sanal]`: yıllık döküm. Yıl içindeki satışların sonucu (FIFO maliyet, komisyon dahil), net temettüler ve ödenen komisyon. Defter dökümüdür, vergi danışmanlığı değildir.

## v0.62.1 – 27.10.2026
- KAP takibinin ilk gerçek çalışmasında HEKTS'in *tahsisli* sermaye artırımı yanlışlıkla "kayıtta yok" çıktı; tahsisli artırım mevcut ortaklara hak vermez, fiyat düzeltmesi gerekmez. Artık "tahsisli: fiyat düzeltme gerekmez" yazıyor.

## v0.62.0 – 27.10.2026
- KAP takibi: her cumartesi araştırma çalışması son 14 günün KAP duyurularından bizim hisselerdeki sermaye artırımı/azaltımı ve temettüleri listeler; `corporate_actions.csv`'de kaydı olmayan sermaye işlemi "KAP'ta doğrula" diye bağlantısıyla gelir. Hiçbir şey kendiliğinden uygulanmaz.

## v0.61.1 – 27.10.2026
- KAP takibinin 1. adımı: KAP'ın (resmî API'si yok) sitesinin kullandığı uç noktaları GitHub'dan deneyen komut ve iş akışı (`kap.yml`). Hiçbir veri değişmez; amaç ayrıştırıcıyı tahmin değil gerçek cevap üzerine yazmak.

## v0.61.0 – 27.10.2026
- `/rapor_tekrar`: kaçan ya da silinen günlük raporu kayıttan yeniden gönderir (`/rapor_tekrar 27.10`). `/start` sık kullanılan komutları düğme olarak açar; Telegram "Menu" bütün komutları listeler.

## v0.60.1 – 27.10.2026
- Bot ve rapor görevi izleme durumunu aynı anda yazarsa biri artık kaybolmuyor. İkinci kaynak çökmüşse bilgi mesajı denemesi rapor görevini en fazla bir zaman aşımı kadar uzatıyor (önce ~3 dk).

## v0.60.0 – 27.10.2026
- `/performans`: canlı ölçüm olgunlaşınca her teknik görünüm için geçmiş (backtest) sonucuyla "uyumlu" mu, yoksa "anlamlı sapma" mı olduğunu kendisi söyler. Sunucu kararının ölçütü veriden önce yazıldı (DECISIONS K-23).

## v0.59.3 – 27.10.2026
- Gerçek alarm tatbikatı başarılı (DOWN 22:53, UP 22:56; Telegram ve e-posta). İkinci kaynak mesajı artık yalnız Yahoo gerçekten cevap vermediğinde gider; Yahoo yalnız gecikmişse beklenir (öz-denetim Ö6).

## v0.59.2 – 27.10.2026
- Dışarıdan izleme açıldı (PC, 22:23). Kurulumda yaşanan iki yazım hatası artık kendiliğinden yakalanıyor: adrese giren boşluk silinir; `< >` örnek metni ya da eksik kod `/durum`'da "biçimi hatalı" diye görünür (adres gösterilmez).

## v0.59.1 – 27.10.2026
- Erken öz-denetim (ROADMAP "Öz-denetim 2"): kritik ya da yüksek bulgu yok. Bir orta bulgu düzeltildi: GitHub'daki iş akışları sonuçlarını aynı dala aynı anda yazmaya çalışırsa haftalık araştırma sonuçları kaybolabiliyordu; artık yeniden denerler.

## v0.59.0 – 27.10.2026
- Araştırma programı (docs/RESEARCH_PROGRAM.md): deneme bütçesi, ön kayıt ve 02.11.2026'dan başlayan ileri holdout. Araştırma araçları artık 30.10.2026'dan sonraki fiyatları göremez; bu kodla zorunlu. Günlük rapor ve canlı ölçüm etkilenmez.

## v0.58.0 – 27.10.2026
- Yahoo bir seansın verisini vermezse o gün sessiz geçmiyor: bir kez kısa mesajla XU100 ve elindeki hisselerin İş Yatırım'daki kapanışları gelir ("yalnız bilgi"). Bu veri fiyat deposuna yazılmaz; sanal emirler ve ölçüm Yahoo'yu bekler.

## v0.57.0 – 27.10.2026
- Tek arıza noktası analizi (docs/SPOF.md): PC, internet, Yahoo, Telegram, GitHub ve diğerleri için B planları.
- Günlük rapor göndermeden önce `logs/reports/rapor_<gün>.txt` dosyasına da yazılır: Telegram uzun süre çökse bile o günün raporu kaybolmaz.

## v0.56.3 – 27.10.2026
- Felaket kurtarma tatbikatı temiz Windows makinesinde baştan sona başarılı (yedekten geri yüklenen dosyalar birebir aynı). Tatbikatın `/durum` çıktısı son bir eksik gösterdi: elle ya da aylık yapılan geri yükleme testi "Yedek" hedefine sayılmıyordu. Artık sayılıyor; başarısızlık da kaydediliyor. Sunucudan çekilen yedeklerin denetimi bu makinenin hedefine sayılmaz (`--no-record`).

## v0.56.2 – 27.10.2026
- Felaket kurtarma tatbikatının 2. çalışması kurulumu geçti; 574 testten biri, Windows'ta WSL'in boş `bash` kabuğunu çalıştırmaya çalıştığı için düştü. Bu test Windows'ta artık atlanıyor (Windows'un kendi betiği `pull_backups.ps1`'dir).

## v0.56.1 – 27.10.2026
- İlk felaket kurtarma tatbikatı gerçek bir hata buldu: belgedeki gibi zip olarak indirilen kodda `setup.ps1`, git klasörü olmadığı için Windows PowerShell'de duruyordu. Düzeltildi; kurulum adımları artık çıkış koduyla denetleniyor. Git'siz kopyada tüm testler geçti.

## v0.56.0 – 27.10.2026
- İzleme alarm tatbikatı: `python -m core.infrastructure.ping --drill` bilerek bir alarm üretir, `--recover` geri alır; adres hiçbir yerde yazılmaz (OPERATIONS §7). Windows'ta aylık felaket kurtarma tatbikatı iş akışı (dr-drill.yml). Olgunluk merdiveni (docs/MATURITY.md): S1 kapandı.

## v0.55.3 – 27.10.2026
- Öz-denetim (ROADMAP). Bakım takvimi BIST 100 dönemlerini çeyreğin ilk işlem gününden de tanıyor; aksi halde Ocak 2027'de kalıcı yanlış uyarı verecekti.

## v0.55.2 – 27.10.2026
- SLO'lar kaydın başladığı günden ölçülür: PC'de rapor ve yedek hedefi, kaydı olmayan eski günleri "eksik" sayıp %25 gösteriyordu. Hiç kaydedilmemiş geri yükleme testi artık "bilinmiyor".

## v0.55.1 – 27.10.2026
- Bot açılışında tek bir DNS hatasının ardından bağlantı gelirse botun açılmaya devam ettiği, python-telegram-bot'un gerçek yeniden deneme döngüsüyle test edildi (eski ayarla aynı test başarısız olur). PC doğrulamaları (D13, v0.45.13–v0.46.0) ROADMAP'e işlendi.

## v0.55.0 – 27.10.2026
- `/durum`'a "Bakım takvimi": BIST 100 üç aylık dönem değişikliği yaklaşınca haber, girilmezse uyarı; Python 3.11 destek sonu.
- El kitabı (docs/HANDBOOK.md), bakım takvimi (docs/MAINTENANCE.md), bu dosya.
- Doğrulama: yeni testler; belgelerin bağlantıları test ediliyor.

## v0.54.1 – 27.10.2026
- Test kapsamı kapısı: %91'in altına düşen sürüm CI'da kırmızı olur. "Kalite" hedefi GitHub'daki son CI sonucunu gösterir.
- v0.54.0'daki kırmızı test düzeltildi (gizli bilgi testi kendi örneğini yakalıyordu).

## v0.54.0 – 27.10.2026 (CI kırmızı; v0.54.1 düzeltti)
- Her pazartesi paket güvenlik taraması (pip-audit). Depoda token, izleme adresi ya da kişisel kayıt olmadığını denetleyen test.

## v0.53.0 – 27.10.2026
- Felaket kurtarma belgesi: sıfır bilgisayara kurulum, aylık tatbikat, token sızarsa. Belgedeki her komutu test denetliyor.

## v0.52.1 – 27.10.2026
- Haftalık kurumsal işlem şüphesi taraması (bedelsiz/bedelli/bölünme olabilecek sıçramalar); hiçbir şey kendiliğinden uygulanmaz.

## v0.52.0 – 27.10.2026
- "Veri doğruluğu" hedefi ikinci kaynağa (İş Yatırım) bağlandı; şüpheli hisseler isimle. Araştırmada şüphelileri dışlama seçeneği.

## v0.51.1 – 27.10.2026
- Her rapor çalıştırması için tek, aranabilir log satırı (`RUN daily … status=…`).

## v0.51.0 – 27.10.2026
- Sağlık hedefleri (SLO): `/durum` ve cuma raporunda son 7 günün rapor teslimi, bot ayakta kalma, veri tazeliği, yedek, kayıt bütünlüğü; ölçülemeyen "bilinmiyor".

## v0.50.0 – 27.10.2026
- Disk dolunca rapor yine gider; saat geri alınınca rapor kilitlenmez. Yönetim belgesi (CHARTER) kaydedildi.

## v0.49.3 – 27.10.2026
- v0.49.2'de kırık bırakılan test düzeltildi.

## v0.49.2 – 27.10.2026 (CI kırmızı; v0.49.3 düzeltti)
- Cuma raporuna haftalık sistem özeti.

## v0.49.1 – 27.10.2026
- `/durum`'a dışarıdan izleme satırı; adres asla gösterilmez.

## v0.49.0 – 27.10.2026
- Uyku/uyanma, geç internet, Excel'de açık dosya, elektrikte yarım kalan satır senaryoları; kesinti tablosu (OPERATIONS §8).

## v0.48.x – 27.10.2026
- Bot açılışta ağ hatasında ~7 dk yeniden dener (v0.48.4). Fiyat düzeltme onay kapısı (v0.48.1). Şüpheli mumları İş Yatırım ile yan yana gösterme (v0.48.2–3). Aşama 3: H2/H3 (v0.48.0) reddedildi.

## v0.47.x – 27.10.2026
- Aşama 3 H1 (düşük oynaklık) reddedildi (v0.47.0). İkinci kaynak yanıt vermezse kontrol erken biter (v0.47.1).

## v0.46.x – 27.10.2026
- Dışarıdan izleme (Healthchecks) kodu (v0.46.0); Windows konsolunda emoji çökmesi (v0.46.1); iki bot çakışması açık bir satırla (v0.46.2).
