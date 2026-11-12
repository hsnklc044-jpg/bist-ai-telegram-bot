# Kararlar

Sürekli yol haritası (ROADMAP) gereği Claude'un verdiği teknik kararlar, tarihli ve gerekçeli. En yenisi en üstte.

## 12.11.2026

**K-86. Kullanıcının "roket" TradingView taraması `/tara` şablonu olarak (12.11.2026; kullanıcı isteği). Karneye bakılmadan yazıldı.**
- **Ne:** Kullanıcının TradingView ekranındaki 16 koşullu tarama, diğer şablonlar gibi (K-38) kodda sabit, sonuca göre ayarlanmayan bir filtre şablonu: `roket`. Öneri değildir; araştırma programına aday kural değildir; tür: "Tek hissede trend takibi / kırılım" (RESEARCH_LOG, reddedilen tür).
- **Yeni alanlar (TradingView tanımıyla, yalnız kapanmış mumlardan):** `ichimoku_donusum` (9), `ichimoku_baz` (26), `ichimoku_a` ve `ichimoku_b` (52; öncü çizgiler 25 seans önce hesaplanan değer, TradingView'in çizdiği gibi), `aroon_yukari` (14; 15 seanslık pencere, eşitlikte en yeni zirve), `vwap` (günlük mumda (Y+D+K)/3), `pivot_fib` (bir önceki tamamlanmış takvim ayı; ay eksikse bilinmiyor), `bb_orta`. `ema(14)` için 14 ortalama dönemlerine eklendi.
- **Koşullar:** 16 koşulun 15'i (MAX_CONDITIONS = 15). Çıkarılan "BB üst > BB orta" tanım gereği her zaman doğrudur, sonucu değiştirmez. "Perf 1H" mevcut `degisim_1h` (5 seans, K-37), "Rel vol" `goreli_hacim` (önceki 10 seans) ile eşlendi.
- **Bilinen fark:** Taramada "fiyat > öncü B" yok; fiyat bulutun içinde kalabilir. Şablon verildiği gibi kalır; listede yazılır.
- **Kapsam dışı (CHARTER §9):** TradingView "Strong Buy" derecesi ve "ilk 3'ü alacağız" türü sıralama al/sat etiketidir, eklenmez. Telegram kanal içeriği yeniden yayımlanmaz; yalnız taramanın koşulları kullanıldı.
- **Değişmeyen:** diğer şablonlar, karne yöntemi, holdout, araştırma programı.

## 11.11.2026

**K-85. Resmî gün sonu verisinin kullanımı (11.11.2026; K madde 2–3).**
- **Yahoo kontrolü:** kapanmış ay, günlük getiri, mevcut crosscheck kuralları (yeni eşik yok). Açıklayan günler: borsanın kurumsal işlem kodu ve `corporate_actions.csv`. Özet "Veri doğruluğu" hedefine; kaynak "Borsa İstanbul resmî gün sonu". Araştırmada resmî kapanış esas (kullanımı ayrı sürümde, holdout kuralıyla).
- **Seviye:** kapanmış ayın günleri resmî dosyayla Seviye 1; içinde bulunulan ay Yahoo, Seviye 3. Geçen ayın kontrolü bugünkü fiyatın seviyesini değiştirmez (talimat: "içinde bulunulan ay için Yahoo, Seviye 3").
- **Kurumsal işlem:** talimattaki ham fiyat ile ONCEKI KAPANIS FIYATI farkı yöntemi yeni sistemde çalışmıyor (alan ham; REFERANS FIYAT o günlerde 0). Borsanın günlük kodu kullanılır; eşleşme ±3 gün. Kodların anlamı tahmin edilmez.
- **Üyelik:** resmî işaret yalnız işlem gören satırda olduğundan işlem görmeyen gün karşılaştırılmaz; kod değişiklikleri ALIASES ile.
- **Hatırlatma:** ayın ilk işlem gününden geçen ayın fiyat dosyası ve endeks klasörü gelene kadar tek satır.

**K-84. Borsa İstanbul resmî gün sonu dosyaları: okuma kuralları (11.11.2026; kullanıcı kararı K bölümü).**
- **Kaynak:** DataStore "Gün Sonu Fiyat ve İşlem Hacmi", aylık, 0 TL, yalnız kişisel kullanım; kullanıcı elle indirir. Seviye 1 (K-82).
- **Biçim tanıma:** başlıklar isimle; bilinen üç biçimin alan listesi koddadır (11.11'de 467 dosyanın başlığından). Listede olmayan bir başlık ya da gerekli alanın eksikliği dosyayı reddeder; tahmin yapılmaz.
- **2005 öncesi:** fiyat ÷ 1.000, adet ÷ 1.000, TL hacim ÷ 1.000.000. Kullanıcının talimatı fiyat ve hacim için ÷ 1.000.000 diyordu; talimatın kendi kabul ölçütü ("2004 sonu ile 2005 başı arasında sıçrama yok") bununla sağlanmadı (297 hissede 1.000 kat). Gerekçe: 1 Ocak 2005'te altı sıfırın atılmasıyla birlikte 1.000 eski pay 1 paya birleşti; dosyalardaki fiyat eski payın fiyatıdır. Kanıt: dosyanın 03.01.2005 satırındaki "önceki kapanış" alanı ve hacim/adet/kapanış oranının her yıl ~1 olması.
- **Eski sistem seansları:** kapanış son işlem gören seansın kapanışı; yüksek ve düşük seansların en ucu; hacim ve adet toplam; önceki kapanış ilk seansın. Açılış fiyatı dosyada yoksa boş.
- **Kurumsal işlem kodu:** yeni sistemdeki `OZSERMAYE HALI` ham kod olarak saklanır (boş ve "0" = yok); anlamı tahmin edilmez.
- **Depolama:** `data/official.db`, yalnız normal hisseler ve gereken sütunlar. Ham klasör ve bu veritabanı yedeğe girmez: ham dosyalar DataStore'dan yeniden indirilebilir, veritabanı onlardan yeniden kurulur (DISASTER_RECOVERY).
- **Değişmeyen:** `market.db`, fiyat akışı, hesaplar. Resmî verinin araştırmada ve "Veri doğruluğu" hedefinde kullanımı ayrı sürümde.

**K-83. Fiyat satırının kaynağı ayrı tabloda; lisanslı kaynak arayüzü (11.11.2026; J madde 4).**
- **Ne:** Her fiyat satırının kaynağı `price_sources(symbol, date, source)` tablosunda, `prices` ile aynı anahtarla. Kaydı olmayan satır Yahoo'dur (bu sürümden önce yazılmıştır).
- **Neden sütun değil tablo:** 0.99.125 ve öncesi `INSERT OR REPLACE INTO prices VALUES (7 değer)` ile yazar. `prices`'a 8. sütun eklenirse geri dönüşte eski sürüm fiyat yazamaz. Ayrı tablo eski sürüme görünmez; geri dönüş güvenli kalır.
- **Arayüz:** `PriceSource` (fetch, ad, seviye, köken) ve `FundamentalSource` (statements). Adaptör yalnız kaynağın kullanım şartları DATA_SOURCES'a yazıldıktan sonra yazılır. Bağlantı için `.env`'de ad ve anahtar; anahtarın girilmesi kullanıcının şartları kabul etmesidir. İlk iş karşılaştırma raporu ve ikinci kaynak kontrolünün yeniden açılmasıdır.
- **Değişmeyen:** fiyatların kendisi, okuma yolu (`store.read`), hesaplar.

**K-82. Veri güven seviyeleri (11.11.2026; kullanıcı kararı "filtreler sağlam veriye dayanmalı").**
- **Seviyeler:** 1 resmî ya da lisanslı kaynak (Borsa İstanbul, KAP, lisanslı dağıtıcı, aracı kurum API'si); 2 resmî olmayan ama ikinci bağımsız kaynakla doğrulanmış; 3 resmî olmayan ve doğrulanmamış.
- **Yahoo fiyatları:** Seviye 3. Seviye 2'ye çıkma koşulu "Veri doğruluğu" hedefinin ölçüsüdür, yeni eşik yok: kullanıcının ikinci kaynak dosyası kontrolü (`logs/price_second_source.json`) son 8 günde ve en fazla %1 hisse farklı.
- **Taşıma:** Bir puan, tarama ya da filtre kullandığı en zayıf verinin seviyesini taşır.
- **Gösterim:** Seviye 3'te fiyat verisine dayanan Telegram mesajlarının başlığı altında tek satır "Veri: doğrulanmamış kaynak"; `/durum`'da kaynak ve seviye.
- **Araştırma:** H6a, H6b, H7a, H7b ve sonraki hipotezler yalnız Seviye 1 ya da 2 veriyle "geçti" kararı alabilir; Seviye 3'te sonuç "ön bulgu" diye işaretlenir. Karar kuralı (blok bootstrap, Bonferroni) değişmez.
- **Değişmeyen:** hesaplar, kurallar, karne puanları, holdout.

## 10.11.2026

**K-81. Araştırma raporuna aşırı uyum ölçüleri: Deflated Sharpe Ratio ve PBO (10.11.2026; kullanıcı onayı "Evet, kaydet"). Ölçüm yapılmadan, araştırma sonuçlarına bakılmadan yazıldı.**
- **Soru:** Haftalık araştırma birden çok strateji deniyor. En yüksek Sharpe'lı stratejinin üstünlüğü, deneme sayısı hesaba katıldığında şans eseri olabilir mi?
- **Bilgi, karar değil:** Mevcut karar (21 seanslık blok bootstrap, Bonferroni düzeltmeli güven aralığı; "aralık sıfırın üstünde değilse XU100'ü geçmiş sayılmaz") değişmez. DSR ve PBO raporda yalnız bilgi satırıdır; eşik yok, hiçbir kararı, sinyali, ayarı tetiklemez.
- **Veri:** Bonferroni'nin saydığı test edilen stratejiler (al-tut karşılaştırmaları hariç). Günlük getiriler, ortak tarihler (iç birleşim). Holdout'a dokunulmaz; araştırmanın kendi dönemi kullanılır.
- **DSR (Bailey ve López de Prado, 2014):** SR, T, γ₃, γ₄ ortak dönemde en yüksek günlük Sharpe'lı stratejinin; N = test edilen strateji sayısı; V[SR] = test edilen stratejilerin günlük Sharpe oranlarının varyansı (ddof=1).
  - SR₀ = √V[SR] · ((1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))), γ = 0,5772156649.
  - DSR = Φ((SR − SR₀)·√(T − 1) / √(1 − γ₃·SR + (γ₄ − 1)/4·SR²)); γ₄ basıklık (normalde 3).
  - N < 2 ya da karekök içi ≤ 0 ise "hesaplanmadı".
- **PBO, CSCV (Bailey, Borwein, López de Prado, Zhu, 2017):** Ortak getiri matrisi S = 16 ardışık, eşit boyda bloğa bölünür; 8 bloğun her seçimi eğitim, kalan 8 test: C(16,8) = 12 870 ayrım.
  - Ölçü: birleştirilmiş blokların günlük Sharpe oranı.
  - Eğitimde en iyi stratejinin testteki sırası r (1 = en kötü; eşitlikte ortalama sıra); ω = r/(N + 1); λ = ln(ω/(1 − ω)).
  - PBO = λ ≤ 0 olan ayrımların oranı.
  - N < 2 ya da blok başına 5 seanstan az gözlem varsa "hesaplanmadı".
- **Rapor satırı:** "Aşırı uyum (bilgi, K-81; karar değişmez): en yüksek Sharpe <strateji> · DSR %NN (N strateji) · PBO %NN (CSCV, 16 blok)".
- **Doğrulama (ölçümden önce yazılan testler):** tek strateji → hesaplanmadı; belirgin pozitif kaymalı tek strateji + gürültüler → DSR yüksek, PBO düşük; yalnız gürültü → PBO yaklaşık %50; aynı en iyi stratejiye daha çok gürültü stratejisi eklemek DSR'ı düşürür.

## 05.11.2026

**K-80. K-64 saatlik ileri testi: yöntem, veri ve iki indirme kuralı (05.11.2026; kullanıcının "onay beklemeden devam" talimatı, önerilen yanıtlarla). Holdout verisine bakılmadan yazıldı.**
- **Soru:** K-64'ün dondurulmuş kuralı (K-79), görmediği dönemde (02.11.2026 ve sonrası) onayladığı sinyallerde tüm sinyallerin oranından ayırt edilebilir bir isabet veriyor mu?
- **Yöntem (b):** Tek model, holdout öncesi veriyle bir kez eğitilir; yalnız holdout sonrası olaylarda sınanır. `signal_filter.main()` her zaman `HOLDOUT_START`'ta kestiği için bu bölme yeni modülde: `core/ml/k64_forward.py`. Dondurulmuş `events`, `fit`, `_bootstrap`, `APPROVE`, `MIN_APPROVED`, `FEATURES`, `SPEC["saatlik"]` değiştirilmeden kullanılır.
  - **Eğitim verisi:** yalnız dondurulmuş görüntü A (Actions 41880444802, veri özeti `4fc8a1bc97045caebb14a914097df181418883e841eb96bfee3e23474c506a0b`). Etiketi `HOLDOUT_START`'tan önce biten olaylar. Özet uyuşmazsa çalıştırma durur.
  - **Test:** zamanı `HOLDOUT_START` ve sonrası, etiketi ortak son tarihten önce biten olaylar.
  - **Kural:** K-64 ile aynı. Olasılık ≥ `APPROVE` (0,60) onay; en az `MIN_APPROVED` (50) onay; gün bootstrap aralığının alt ucu temel oranın üstünde.
- **İki indirme (K-63 için de geçerli):**
  - Tam olarak iki indirme. İlki 03.02.2027 ya da sonrası; ikincisi ilkinden en az 7 gün sonra. Üçüncü indirme yok.
  - Veri üretmeden teknik olarak düşen indirme bir kez tekrarlanabilir; bu kaydedilir.
  - İkisi de aynı ortak son tarihe (ilk indirmeden önceki bir gün; öneri 02.02.2027), aynı holdout başlangıcına ve aynı aralığa kesilir.
  - Her indirme dondurulur (`provenance freeze`); özeti ve yolu kayda yazılır.
- **Kalite kapısı (yalnız ileri pencere, BIST takvimi, her hisse):**
  - son saatlik mumu (17:30; yarım gün 11:30) eksik seans payı ≤ %5;
  - 9'dan az mumlu tam seans payı ≤ %5;
  - hiç mumu olmayan seans = 0;
  - hacmi 0 olan mum payı ≤ %2.
  Kapıdan geçemeyen indirmenin yerine yenisi alınmaz; sonuç ÖLÇÜLEMEDİ.
- **Karar tablosu (seçme yok, ortalama yok):**
  - ikisi geçti → GEÇTİ;
  - biri geçti, biri geçmedi → VERİYE DUYARLI (geçmiş sayılmaz);
  - ikisi de geçmedi → GEÇMEDİ;
  - biri kapıdan geçemedi → ÖLÇÜLEMEDİ.
- **Geçmiş kararlar:** Tek indirmeyle verilmiş K-63/K-64 kararları geçerli kalır; RESEARCH_LOG'a "tek indirme, veri duyarlılığı ölçülmedi" notu düşüldü. GEÇMEDİ kararları değişmez.
- **Tarih ve ölçüt değişmez (03.02.2027).** Beklenti, ölçümden önce yazıldı: geçmişte test edilen olayların yaklaşık %9,5'i onaylandı (380'de 36). 02.11.2026 – 02.02.2027 penceresinde yaklaşık 135 olay, yani yaklaşık 13 onay beklenir. En olası sonuç "onaylı sinyal az" nedeniyle GEÇMEDİ'dir. 50 onaya ulaşmak için pencere, parametre ya da tarih değiştirilmez.
- **Kayıt için fark analizi (karar dışı):** A ile B (05.11, 32 onaylı çalıştırmanın verisi `2d126a5a…`) arasındaki 17:30 mumu ve hacmi 0 sayıları `scripts/veri_farki.py saatlik` ile sayılır. K-64 kodu çalıştırılmaz; hangi indirmenin doğru olduğu söylenmez.
- **Reddedilen:** Dondurulmuş kodu değiştiren bir veri temizleme kuralı (seçenek 2).
- **Dondurma:** `core/ml/k64_forward.py` tamamıyla K-79 dondurma testine eklendi (aşağıdaki K-79 eki).
- **Düzeltme (v0.99.96; kullanıcı onayı 05.11.2026, holdout verisi okunmadan):** Hacmi 0 eşiği yazıldığı haliyle ölçülemezdi. Yahoo 09:30 mumunda hacmi neredeyse her seans 0 veriyor; holdout öncesi Ağustos–Ekim 2026'da pay A'da %11,4, B'de %11,3 ve 30 hissenin 30'u %2'nin üstündeydi, yani sonuç her durumda ÖLÇÜLEMEDİ olurdu. 09:30 mumu bu sayımdan çıkarıldı, eşik %2 kaldı; 09:30 payı bilgi olarak raporlanır. Aynı dönemde pay A'da %0,16, B'de %0,08 ve iki indirme de kapıdan geçiyor. Başka eşik değişmedi.
- **Düzeltme 2 (v0.99.98; kullanıcı onayı 05.11.2026: "benim kararıma kalan her şeye onay veriyorum"; holdout verisi okunmadan):** "Hiç mumu olmayan seans = 0" eşiği toplamda sıfırdı; tek bir hissenin tek gün işlem görmemesi bütün testi ÖLÇÜLEMEDİ yapıyordu (B'de holdout öncesi 14 mumsuz seans, hepsi KONTR ve TRALT'ta). Eşik pay oldu: mumsuz hisse-seans payı ≤ %0,5. 30 hisse ve yaklaşık 65 seansta bu en fazla 9 hisse-seans demektir. Başka eşik değişmedi.
  - **Açık karar:** "Mumsuz seans = 0" eşiği değişmedi. B'nin Mayıs–Temmuz 2026 üç ayında tek bir hisse-gün bu kapıyı kapatıyor (A'da 58). Tek hissenin işlem görmemesinin testi durdurup durdurmayacağına kullanıcı karar verecek.
  - **Sonuç metni:** GEÇMEDİ'nin nedeni yazılır. Onay < 50 ise "örneklem yetersiz, model hakkında sonuç vermez". Ölçüt ve karar tablosu değişmedi.
- **Doğrulama:** `tests/test_k64_forward.py` (14 sentetik test). Eğitimin holdout'tan bir şey okumadığı, yalnız pencere içindeki olayların sayıldığı, eşiklerin dondurulmuş sabitler olduğu, her kalite eşiğinin kapıyı kapattığı, karar tablosu ve tarih kuralı sınanıyor.

**K-78. Uzun vadeli fiyat faktörleri: keşif ölçümünün kuralları (05.11.2026; kullanıcının "onay beklemeden devam" talimatı). Faktör verisine ve fiyat getirilerine bakılmadan yazıldı. Henüz ölçüm yok.**
- **Soru (2 faktör, sabit):**
  - **Momentum:** t−252 seans kapanışından t−21 seans kapanışına getiri. Hipotez: en yüksek üçte birlik dilimin maliyet sonrası aylık getirisi, aynı ayın eşit ağırlıklı evren getirisinden yüksek.
  - **Düşük oynaklık:** son 252 seansın günlük log getirilerinin standart sapması. Hipotez (tek test): en düşük üçte birlik dilim (a) maliyet sonrası aylık getiride evrenden yüksek VE (b) 54 aylık getiri serisinin standart sapması evreninkinden düşük. Karşılaştırma evrene karşı.
  - Değer ve kalite: geçmiş bilanço verisi yok, kapsam dışı. Sonuca bakılarak faktör eklenmez.
- **Evren:** Her ay sonunda o günkü gerçek BIST 100 üyeleri (01.04.2022'den). Ay sonu üye sayısı 55/55 tarihte 100 (fiyatsız sayım). BIST 30 kullanılmaz. Likidite: üyelerin son 20 seans medyan günlük TL hacmine göre en düşük %20'si çıkarılır.
- **Veri:** Yahoo `auto_adjust=True` ve `corporate_actions.csv`. Çift düzeltme koruması: her şirket işlemi için ham veride ex_date'te beklenen sıçrama (kayıttaki faktörün ±%10'u) aranır; yoksa kayıt uygulanmaz ve raporda listelenir. Faktörler yalnız formasyon günü kapanışına kadarki fiyatla.
- **Getiri:** TL nominal, maliyet sonrası, dilim − eşit ağırlıklı evren. Maliyet alışta %0,15, satışta %0,15, yalnız devir üzerinden; %0,30/%0,30 bilgi satırı. Bilgi (karar dışı): XU100'e göre, reel. Yalnız uzun.
- **Yöntem:** Ay sonu kapanışında sıralama, ertesi seans açılışında giriş, sonraki ay sonu kapanışında çıkış. Dilim floor(n/3), eşitlikte kod alfabetik, eşit ağırlık. 252 seans geçmişi olmayan üye o ay hem dilimden hem evrenden çıkar. Dönem: formasyon 29.04.2022 – 30.09.2026, 54 tutuş ayı. Holdout fiyatı okunmaz. Bir ay, likidite sonrası en az 60 hisse ve üyelerin en az 80'inde veri varsa geçerli; geçerli ay < 36 ise "ölçülemedi".
- **Uygulanabilirlik (dilime ve evrene aynı):** tavanda açılış (≥ %9,5, `limit_up`) ya da giriş günü verisi yok → o ay dışarıda. Ay içinde kalkan: son kapanıştan çıkılmış sayılır. Tedbirli hisseler ayıklanamaz (sınır). Fiyatı olmayan üye ölçüm dışı; sayısı raporlanır.
- **Aralık:** Tek yönlü %97,5 alt sınır (Bonferroni, 2 faktör). Hareketli blok bootstrap, 3 aylık blok, 10.000 tekrar, tohum 0. Her çalıştırma deneme dosyasına ve RESEARCH_LOG'a yazılır. Parametre taraması yok.
- **Geçme (KEŞİFTE GEÇTİ):** (1) ortalama aylık fazla getiri > 0; (2) alt sınır > 0; (3) 2023, 2024, 2025'in en az ikisinde yıllık ortalama > 0; (4) düşük oynaklık için ayrıca 1(b).
- **Güç ve "yanıtlanamadı":** Sentetik güç analizinde %80 güçle yakalanan aylık etki: oynaklık %2 → %0,8; %3 → %1,2; %4 → %1,6; %5 → %2,0. Literatürdeki %0,3–0,5 için güç %15–40. Ölçüt sağlanmazsa: iki yönlü %95 aralığın üst ucu aylık %0,5'in altındaysa "GEÇMEDİ (literatür büyüklüğünde etki dışlandı)", değilse "YANITLANAMADI (güç yetersiz)". En olası sonuç budur.
- **İki indirme (kullanıcının eki, K-80 ile aynı yapı):** Ölçüm iki günlük indirmeyle yapılır: dondurulmuş günlük görüntü (`56016f59…`, 04.11) ve ondan en az 7 gün sonra (11.11.2026 ya da sonrası) alınıp dondurulan ikincisi. İkisi aynı son tarihe (30.10.2026) kesilir. Ölçümden önce `scripts/veri_farki.py gunluk` ile likidite eleme listelerinin kaç ay sonunda değiştiği sayılır (fiyat ya da getiri sonucuna bakılmadan). Sonuçlar K-80 tablosuyla birleştirilir: ikisinde geçti → KEŞİFTE GEÇTİ; biri → VERİYE DUYARLI (geçmiş sayılmaz); hiçbiri → iki etiket aynıysa o etiket (GEÇMEDİ ya da YANITLANAMADI), farklıysa YANITLANAMADI. Kapsam eşiğini geçemeyen indirme → ÖLÇÜLEMEDİ.
- **İleriye dönük izleme (yalnız keşifte geçen faktör):** 03.02.2027'den sonraki ilk ay sonu (en erken 26.02.2027 formasyonu). 12 tutuş ayı, değerlendirme bir kez, Mart 2028'de. Seçimler formasyon günü workflow ile `research-results` dalına yalnız ekleme yapılarak yazılır; ara getiri hesaplanmaz ve gösterilmez. Etiketler: UYUMLU / UYUMSUZ (en az 10 geçerli ay) / ÖLÇÜLEMEDİ.
- **Yeniden çalıştırma:** Yalnız sonuç üretmeden düşen teknik hata için, bir kez.
- **Sınırlar:** Tek bir yüksek enflasyon rejimi; 2022–2026 başka kurallar için incelendi, holdout değil; Yahoo düzeltmesi bağımsız doğrulanmadı; tedbirliler ayıklanamadı. Sonuç ne olursa olsun canlı kurala, karta, /saglik'e ya da K-64'e otomatik geçiş yok.
- **Ölçümden önce:** sentetik testler (çift düzeltme, uygulanabilirlik kuralları dilim ve evrende aynı, kapsam sayıları getirisiz) ve K-79 dondurma testi yeşil.
- **Süre:** testler ve kod 1 oturum; keşif ölçümü 2 Actions çalışması (~30 dk); ileri izleme aylık workflow.
- **Ekler (v0.99.96; kullanıcı onayı 05.11.2026; getiri ve faktör değeri görülmeden). Aşağıdakiler, yukarıda çelişen ifadelerin yerine geçer:**
  - **Dönem:** Geçerli ay 48'dir, 54 değil. 1(b)'deki seri ölçümde kaç geçerli ay varsa odur.
  - **Güç:** `factor_study.power`, 48 ay, 2000 deneme, 1000 bootstrap. Yalnız aralık koşulu; diğer koşullar gücü yalnız düşürebilir. Etki %0,3 / %0,5 / %1,2 için: oynaklık %2 → %20 / %44 / %99; %3 → %12 / %24 / %80; %4 → %9 / %16 / %57; %5 → %8 / %12 / %42. Etki 0 ve %3 oynaklıkta yanlış alarm %3,3. Önceki "%15–40" ifadesi kullanılmaz; oynaklık ölçümden önce bilinmediği için tablo geçerlidir.
  - **İkinci indirme:** İkinci görüntü, A gibi boş depoya baştan indirilir: 11.11.2026 ya da sonrasında Yahoo'dan, `auto_adjust=True`. Biriken bir `market.db`'den alınan görüntü ikinci indirme sayılmaz. Manifest kaynağı "Yahoo auto_adjust=True, boş depoya baştan indirildi" ve indirme gününü yazar; ölçüm kodu bunu denetler. (Önceki metin A'yı biriken depo gibi anlatıyordu; yanlıştı: `snapshot.yml` A'yı da Actions'ta boş depoya indirir.)
  - **Etiket (v0.99.104; kullanıcı onayı 05.11.2026; getiri görülmeden):** Alt sınır > 0 olup yıl ya da risk koşulu sağlanmazsa etiket "GEÇMEDİ (alt sınır pozitif, ek koşul sağlanmadı)" olur. Önceki kural bunu "YANITLANAMADI (güç yetersiz)" yapıyordu; sorun güç değildi. Diğer eşikler ve geçme ölçütü değişmedi.
  - **Tek çalışma (v0.99.104):** `scripts/k78_tek_calisma.py` iş başlamadan önceki çalışmaları Actions'tan sayar. Başarılı çalışma varsa ya da iki deneme yapıldıysa iş durur; sayım okunamazsa da durur. Denemeler `research-results` dalında `k78/denemeler.csv` dosyasına, sonuç `k78/` altına yazılır; RESEARCH_LOG'a sonuçtan sonra elle eklenir.
  - **Sıra (v0.99.104):** `measure` önce K-79 dondurma testini, sonra `veri_farki.py gunluk` sayımını çalıştırır. Rapor, K-78'in istediği sayımları ve XU100 ile reel bilgi satırlarını da yazar; bunlar kararı değiştirmez.
  - **Sınır:** Kilitli çıkış gecikirse pozisyon sonraki ayın tutuşuyla örtüşebilir; sonuç metninde sınır olarak yazılır.
  - **Veri kırığı:** Kaydı uygulanmamış ve verideki sıçraması ±%10'u aşan ya da denetlenemeyen şirket işlemi veri kırığıdır. Hisse, formasyondan önceki 253 kapanış ile tutuş ayı sonu arasına o tarih düşen aylarda evrenden ve dilimlerden çıkar; sayısı raporlanır. Eşik gevşetilmez. BJKAS 07.04.2025 bu kuraldadır; hissenin son BIST 100 ay sonu 31.12.2024 (tutuş Ocak 2025), bu yüzden o tarihi okuyan hiçbir ayda üye değil, K-78 sayıları değişmez ve "%26'lık yapay düşüş" evrene girmez.
  - **Açık:** Taban ya da işlem görmeme nedeniyle ay sonu kapanışında çıkılamayan hisse için kural henüz yok. Ölçüm kodundan önce yazılır.
- **Ön testler (v0.99.94):** `core/analytics/factor_study.py` ve `tests/test_factor_study.py` (13 sentetik test). Çift düzeltme koruması, mevcut `corrections._already_adjusted`'tan ayrı olarak K-78'in yazılı kuralıyla (faktörün ±%10'u) uygulandı ve sıçramayı o ana kadar düzeltilmiş veride arıyor; böylece aynı kayıt iki kez yazılsa da bir kez uygulanıyor. Ölçüm ve getiri kodu henüz yok.
- **Kapsam sayımı sonrası (v0.99.95; getiri görülmeden):** Giriş günü tatil dosyasından değil veriden belirleniyor (tatil dosyası 2026'dan başlıyor). Geçerli ay 48/54; ilk 6 ay 253 kapanış geçmişi olmadığı için kendiliğinden "ölçülemedi". Kurallar ve eşikler değişmedi; BJKAS 07.04.2025 kaydı K-78 kuralıyla uygulanmıyor ve sınır olarak yazılacak. Ayrıntı: RESEARCH_LOG "K-78 kapsam sayıları".
- **Tabanda çıkış (v0.99.97; getiri hesaplanmadan, projenin Karar 2 kuralıyla aynı):** Çıkış, tutuş ayının son kapanışıdır. O gün tabanda kilitliyse (bütün gün tek fiyat ve kapanış taban hareketi) satış dolmaz; çıkış, kilitli olmayan ilk sonraki günün açılışından yapılır. `HOLDOUT_START` ve sonrası okunmaz: o güne kadar kilitsiz gün yoksa son kilitli kapanış kullanılır ve raporda sayılır. Böyle aylar ölçümden atılmaz, çünkü atılırsa en kötü aylar silinmiş olur. Kural dilim ve evren için aynıdır (`factor_study.exit_fill`; 4 sentetik test).
- **Ölçüm kodu (v0.99.101; getiri hesaplanmadan, yalnız sentetik testlerle):** `core/analytics/factor_measure.py`. Uygulamada netleştirilen iki ayrıntı: (1) devir maliyeti önceki geçerli ayın hedef ağırlıklarına göre hesaplanır; ay içi ağırlık kayması modellenmez. Kural dilim ve evren için aynıdır. (2) Yıl koşulu tutuş ayının yılına göre sayılır. Eşik ve ölçütlerin hiçbiri değişmedi. Kod gerçek veride henüz çalıştırılmadı; ölçüm iki dondurulmuş günlük görüntüyle tek Actions çalışmasında yapılacak.

**K-79. K-64, 03.02.2027 ileri testi için donduruldu (05.11.2026; kullanıcı onayı).**
- **Ne:** `tests/test_k64_freeze.py`, K-64 ölçümünün ve canlı `/tara ai` modelinin dayandığı her parçanın kaynak kodunu özetliyor (satır sonundan bağımsız). Bir parça değişirse CI kırmızı olur. Kapsam:
  - kural, eşik ve etiket: `SPEC`, `APPROVE`, `MIN_APPROVED`, `features`, `labels`, `events`;
  - değerlendirme: `_purged_folds`, `fit` (model parametreleri ve ızgara dahil), `evaluate`, `_bootstrap`, `decide`, `text`;
  - canlı model: `fit_live`, `load_live`, `model_file`;
  - tetik: `core/market/extended.py`'nin tamamı;
  - küme ve aralık: `dip_study.events`, `day_bootstrap`;
  - tavan sınırı (`limit_up`), `HOLDOUT_START`;
  - saatlik veri: `load_hourly`, `clean`, `_split`;
  - paket kilidi (`requirements.lock`).
- **Dondurulduğu nokta:** c598008 (v0.99.90). 213f71d'den (son K-64 ölçümü) bu yana değişen tek K-64 parçası `fit_live`: v0.99.78'de (5b89a6c) canlı model holdout'u görmeyecek şekilde sınırlandı. K-64 saatlik ileri testi `fit_live`'ı kullanmıyor; değerlendirme kendi katlarını `fit` ile eğitiyor.
- **Kural:** Özetler yalnız kullanıcının açık onayıyla ve gerekçesi burada yazılarak güncellenir; CI'ı yeşile çevirmek için asla güncellenmez.
- **Doğrulama:** Onay eşiği, ağaç sayısı ya da kilit dosyası geçici olarak değiştirildiğinde test kırmızı oldu; geri alınınca yeşil. CRLF'li bir kopyada aynı özetleri veriyor.
- **Ek (v0.99.92), `tests/test_k64_isolation.py`:**
  1. K-64 ölçümü canlı modele dokunmuyor. `main()`'den erişilebilen hiçbir fonksiyon `load_live`, `fit_live`, `model_file` ya da `joblib` adını içermiyor (kod analizi). Bunlar hata fırlatacak şekilde değiştirildiğinde de ölçüm dondurulmuş görüntüyle çalışıyor.
  2. `/tara ai` modeli yalnız `fit_live` ile eğitebiliyor. `ai.py`'de başka bir eğitici ya da model yazma çağrısı yok. Eski model `fit_live` ile yeniden eğitiliyor; 10 günden genç model yeniden eğitilmiyor.
  `evaluate` içine geçici olarak bir `load_live()` çağrısı eklendiğinde iki test de kırmızı oldu.
- **Dondurulmuş veri görüntülerinin kalıcı kopyası (05.11.2026; kullanıcı onayı, A3):**
  - **Birincil kopya:** özel depo https://github.com/hsnklc044-jpg/quantbist-veri. GitHub API'si `"visibility": "private"` döndürdü. Commit `eab856b` zip'leri, `aac3c75` `ICERIK.md`'yi ekledi.
  - **Saatlik görüntü:**
    - zip `hourly-snapshot-41880444802.zip`, sha256 `ec889f40dc6787a0143e9c6e9f4f9a191f875483f2ea18e441530b23a64c63d0`;
    - veri özeti `4fc8a1bc97045caebb14a914097df181418883e841eb96bfee3e23474c506a0b`;
    - 30 hisse, 62.075 mum, 05.11.2025 09:30 – 30.10.2026 17:30.
  - **Günlük görüntü:**
    - zip `daily-snapshot-41880444802.zip`, sha256 `30f278894b7e86067ae6cd2ad1a8ffa47aa4e33a75107a3d779568d2baaf9e4e`;
    - veri özeti `56016f5992f458527a3100321379a11a5a6753730e0e1fbc848ce30505508a18`;
    - 208 hisse, 238.667 mum, 01.11.2021 – 30.10.2026.
  - **Kaynak:** Actions çalışması 41880444802, commit `46c226f`.
  - **Doğrulama:** Zip özetleri üç kaynakta aynı: artifact kaydı, kullanıcının bilgisayarı, özel depo. İki görüntü temiz bir klasörde `thaw` ile açıldı; veri özetleri DOĞRULANDI. Herkese açık artifact da `snapshot-check.yml` ile doğrulandı (çalışma 41987336455).
  - **İkinci yedek (yerelde doğrulandı, 05.11):** `C:\Users\hsnkl\OneDrive\QuantBIST-yedek\veri_goruntuleri`.
    - `daily-snapshot-41880444802.zip` → `30f278894b7e86067ae6cd2ad1a8ffa47aa4e33a75107a3d779568d2baaf9e4e`
    - `hourly-snapshot-41880444802.zip` → `ec889f40dc6787a0143e9c6e9f4f9a191f875483f2ea18e441530b23a64c63d0`
    - İkisi de yukarıdaki zip özetleriyle karakter karakter aynı.
    - OneDrive bulut eşitlemesini kullanıcı ayrıca teyit edecek.
- **Ek (v0.99.96, K-80 düzeltmesi):** `core/ml/k64_forward.py` içinde `Quality`, `quality`, `main`, `__all__` özetleri güncellendi; `OPEN_CANDLE` ve `verdict_reason` eklendi. Gerekçe: kapı her indirmeyi eliyordu (K-80 "Düzeltme"). Kullanıcının açık onayıyla. K-64'ün kendi parçalarının (`signal_filter`, `dip_study`, `hourly`, `limits`, `extended`) özetleri değişmedi.
- **Ek (v0.99.98, K-80 düzeltme 2):** `core/ml/k64_forward.py` içinde `quality` ve `Quality` özetleri güncellendi; `MAX_EMPTY_SESSIONS` kaldırıldı, `MAX_EMPTY_SHARE` eklendi. Kullanıcının 05.11.2026 açık onayıyla. K-64'ün kendi parçalarının özetleri değişmedi.
- **Ek (v0.99.94, K-80):** `core/ml/k64_forward.py` (ileri test giriş noktası, kalite kapısı eşikleri, karar tablosu, eğitim görüntüsü özeti) tamamıyla `PARTS`'a eklendi; 17 yeni özet `FROZEN`'a yazıldı. Var olan özetlerin hiçbiri değişmedi. Gerekçe: K-80 koşulu "giriş noktası dondurma testine alınır"; kullanıcının 05.11 "onay beklemeden devam" talimatıyla. Doğrulama: `MAX_ZERO_VOLUME` geçici olarak değiştirildiğinde test kırmızı oldu; geri alınınca yeşil.
  - **Düzeltme (05.11):** `scripts\olcum.ps1` bu görüntünün kopyası değildir. Veriyi yeniden indirip yeni bir görüntü dondurur; saatlik pencere kaydığı için özeti farklı çıkabilir. O görüntü ayrı bir kayıttır.
  - Kullanıcı asıl zip'leri OneDrive kopyası doğrulanana kadar silmeyecek.
  - Özel depoya anahtar ya da gizli bilgi konmadı. Claude GitHub uygulamasının erişimi yalnız `bist-ai-telegram-bot` ve `quantbist-veri` ile sınırlı.
- **Açık risk:** `/tara ai`, modeli 10 günden eskiyse yeniden eğitebiliyor. Bu yol yalnız dondurulmuş `fit_live`'ı kullanıyor (test). Bilgisayardaki model 03.11.2026'da eski kuralla eğitildi; 02.11'den sonra kart yazılmadı. 06.11 cuma eğitimi `scripts/kart_modeli_kontrol.py` ile doğrulanacak. Aradaki kartlar silinmeden `logs/kart_holdout_isareti.csv`'ye "holdout etkisi olabilir" olarak yazılır.

## 04.11.2026

**K-77. ML filtresinin (M30, K-59/K-62) ölçüm yöntemi, yeni ölçümden önce (04–05.11.2026, Faz C 1. parti).**
- **Neden:** M30 bağımsız doğrulamasının 1, 2, 3, 5 ve 9 numaralı bulguları. Model kapalı ve bu kararla yeniden ölçülmüyor. Bundan sonraki ilk ölçüm aşağıdaki yöntemle yapılır. Kurallar sonuca bakılmadan, ölçümden önce yazıldı.
- **Karar:**
  1. `stop_hedef` aralığı Wilson ile değil, art arda tarih blokları yeniden örneklenerek hesaplanır. Blok uzunluğu 20 seanstır, yani HORIZON'un iki katı; 05.11'deki yeniden doğrulamadan sonra 10'dan çıkarıldı, ölçümden önce. `goreli20` aynı kalır: test günleri 20 seans arayla, aralık tek tarihlerle.
  2. Ölçüm, kaynaklı BIST 100 değişiklik kaydının ilk gününden (01.04.2022) başlar. İlk test yılı ondan sonraki ilk tam yıldır (2023). Daha önceki üyelik bugün hayatta kalanlardan oluşuyor.
  3. Etiketi holdout'ta (02.11.2026 ve sonrası) biten test satırı test edilmez.
  4. Geçme kuralına üç koşul eklenir; hepsi sağlanmalıdır:
     - sinyallerin maliyet sonrası ortalaması pozitif olmalı;
     - bu ortalama tüm girişlerin ortalamasını geçmeli;
     - sinyallerin en kötü %5'i tüm girişlerin en kötü %5'inden kötü olmamalı.
     Önceki koşullar ve eşikler (en az 100 sinyal, %60 isabet, aralığın alt ucu tabanın üstünde) değişmez.
  5. 10. seansı tabanda kilitli olan etiket, ilk kilitsiz açılıştan kapanır; o açılış henüz yoksa etiket yazılmaz.
  6. `/tara`'daki ML değeri "ml_skor" adını taşır ve "kalibre değil, olasılık değildir" notuyla gösterilir.
- **Sınır:** K-64 (`core/ml/signal_filter.py`) ve 03.02.2027 ileri testi etkilenmez. K-59 ve K-62 kararları KAPALI kalır.

**K-76. Her ölçüm hangi veriyle ve hangi kodla çalıştığını yazar; veri dondurulur (04.11.2026).**
- **Neden:** K-64 saatlik ölçümü aynı gün iki kez çalıştı ve 41 ile 36 onay verdi. Kayıtlar farkın nedenini ayırmaya yetmedi. 15:39 çalışmasında K-63 ve K-64 adımları veriyi ayrı ayrı indirmişti ve K-64 adımı veri aralığını yazmamıştı (RESEARCH_LOG 04.11, FAZ_B_KAPANIS). 03.02.2027 ileri testinin sonucu ancak tekrarlanabilirse savunulabilir. Kullanıcı bu işi 04.11'de onayladı (seçenek 1).
- **Karar:**
  1. K-63, K-64 (günlük ve saatlik) ve K-68 komutları rapordan önce iki satır yazar. Birinci satır veriyi tanımlar: hisse sayısı, mum sayısı, ilk ve son zaman, holdout sınırı ve verinin SHA-256 özeti. Özet hisse, zaman ve OHLCV değerlerinden hesaplanır; dosya biçimine ya da sıraya bağlı değildir. İkinci satır kodu tanımlar: sürüm, `core`'un yüklendiği klasörün git commit'i, kaydedilmemiş değişiklik olup olmadığı ve klasör yolu. Rapordan sonra raporun özeti de yazılır.
  2. Günlük ölçüm yapan iş akışları (card-study, screens, scenarios) fiyat deposunun aynı tanımını ayrı bir adımda yazar.
  3. `hourly.yml` saatlik veriyi bir kez indirir ve dondurur (yalnız 02.11.2026 öncesi). K-63 ve K-64 bu görüntüyü `--veri` ile okur. Görüntü 90 gün artifact olarak saklanır.
  4. Dondurulan görüntü yazıldıktan hemen sonra geri okunur. Okunan verinin özeti manifest ile uyuşmazsa görüntü kabul edilmez.
  5. `snapshot.yml` saatlik ve günlük veriyi dondurur. Saatlik veriyi 5 dakika arayla ikinci kez indirip hisse hisse karşılaştırır. K-63 ve K-64'ü aynı görüntüde, ayrı süreçlerde iki kez çalıştırır; raporlar birebir aynı değilse iş kırmızı olur.
  6. (v0.99.77) Aynı kontrol bilgisayarda tek komutla yapılabilir: `scripts\olcum.ps1`. Görüntü yedek klasörüne (OneDrive) yazılır, kısa rapor `logs\olcum_report.txt`'ye gider. Böylece rutin kontrol bir sohbet oturumu ya da GitHub artifact'ı gerektirmez; kullanıcı 04.11'de rutin işlerin Python/PowerShell ile yürümesini istedi. Dondurulmuş veriyle (`--veri`) çalışan K-63 ve K-64 sonuç dosyasına yazmaz, böylece bir kontrol, kayıtlı ölçümün yerine geçemez.
- **Sınır:** Bu karar hiçbir kuralı, eşiği, geçme koşulunu ya da 03.02.2027 ölçütünü değiştirmez. Görüntüler holdout verisi içermez. `snapshot.yml`'deki iki çalıştırma tekrarlanabilirlik sınamasıdır, karar ölçümü değildir; K-63 ve K-64 kararları kayıtlı haliyle kalır. Fiyat verisi depoya konmaz (depo herkese açık); yalnız artifact olarak ve kullanıcının kendi yedeğinde tutulur.

**K-75. Tavan ve taban kuralı tek yerde; kilitli günde dolum yok (04.11.2026).**
- **Neden:** Bağımsız doğrulama (M27-9, M30-6, M31-11, M32-7, M5-3, M32-9, M27-6, M30-5) aynı kuralın 11 yerde farklı yazıldığını gösterdi. Bazı yerler `>`, bazıları `>=` kullanıyordu; hiçbiri kayan nokta payı taşımıyordu. 100 → 109,5 bir modülde tavan sayılıyor, ötekinde sayılmıyordu.
- **Karar 1 (v0.99.73):** Tavan ve taban kuralı `core/market/limits.py`'de tek yerde. Hareket %9,5 ya da daha fazlaysa limittir; karşılaştırma 1e-9 pay taşır. Bütün modüller bu fonksiyonları kullanır. Bir test, hiçbir modülün sınırı kendi başına karşılaştırmadığını denetler. `/tara`'nın veri sıçraması eşiği (%10,5) ayrı bir kavramdır; adı `JUMP_MOVE` oldu.
- **Karar 2 (sonraki adım):** Tavanda kilitli günde giriş, tabanda kilitli günde çıkış dolmaz. Kilitli gün, en yüksek ile en düşük fiyatın eşit olduğu limit günüdür. Çıkış, ilk kilitsiz günün açılışından yapılır.
- **Ölçümler:** Kural değiştiği için etkilenen çalışmalar (K-59, K-63, K-64, K-68, `/tara` karnesi, senaryo karnesi) GitHub Actions'ta yeniden çalıştırılır. Eski ve yeni sonuç RESEARCH_LOG'da yan yana yazılır. Eşikler ve geçme koşulları değişmez.

**K-74. "Kullanılamaz" model, kapı tarafından uygulanıyorsa uyarı değil bilgidir (04.11.2026).**
- **Neden:** M30 ve M31 bağımsız doğrulamada "kullanılamaz" çıktı. `/durum`'daki Model doğrulama satırı bu yüzden kalıcı ⚠️ oldu. Hiç kapanmayan bir uyarı yeni sorunları gizler (v0.99.40'taki eski eksik kayıt kararıyla aynı ilke).
- **Karar:** "Kullanılamaz" kararı ℹ️ olarak gösterilir ve metin model kapısının (K-72) otomatik eylemleri kapalı tuttuğunu yazar. ⚠️ yalnız yapılacak bir iş varsa çıkar: süresi geçmiş doğrulama. Kararın kendisi değişmez; "tam güvenilir" ölçütü (14/14 raporlu) de değişmez.

**K-73. Ölçülmemiş güç, güç gibi gösterilmez (M1 ve M8 YÜKSEK bulguları; 04.11.2026).**
- **M1:** "Güçlü pozitif" ve benzeri etiketler korunuyor; göstergelerin o günkü durumunu anlatıyorlar ve canlı ölçüm kayıtlarında anahtar olarak kullanılıyorlar. Değiştirmek ileriye dönük ölçümün sürekliliğini bozar. Bunun yerine:
  - `/top` başlığı "Teknik skoru en yüksek hisseler (sıralama, öneri değil)" oldu.
  - "Getiri tahmin gücü bulunmadı" uyarısı listenin sonundan başına alındı.
  - Komut açıklaması "tahmin gücü yok" diyor.
- **M8:** Gösterildiği her yerde "güç" puanının yanına "ölçülmemiş puan" yazılıyor. Küme yönteminin "rastgeleden ayırt edilemedi" notu zaten duruyordu.
- Raporların kararı değişmiyor; bu düzeltmeler yeniden doğrulamada değerlendirilir.

**K-72. Model kapısı (kullanıcının "ModelGovernor" isteği; 04.11.2026).**
- **Kural:** Yüksek riskli bir model kendiliğinden bir şey değiştirebilmek için güncel bir bağımsız doğrulama raporuna ve "kullanılabilir" kararına sahip olmalı. Kendiliğinden değişiklik: sanal sinyal yazmak ya da pozisyon açmak. "Kısıtlı kullanılabilir", "kullanılamaz", süresi geçmiş ya da hiç olmayan rapor: model yalnız bilgi verir.
- **Neden "%90 skor" değil:** Bağımsız doğrulama bir yüzde değil, gerekçeli bir karar üretiyor. Kapı, modelin kendi sonuçlarından değil doğrulama raporundan okunur; bir model kendi kapısını açamaz.
- **Kapsam:** Kendiliğinden eylem yapan tek model M30 (ML filtresi, günlük sinyal adımı). Sinyal adımı artık iki koşul arıyor: örneklem dışı geçiş (K-59) ve açık kapı. M11, M12, M14, M16, M24 ve M28 zaten yalnız uyarı ya da hesap veriyor. `/tara ai` kartları kullanıcı düğmesiyle girildiği için kapıya bağlı değil; kart doğrulama durumunu ve geçmiş ölçümleri yazıyor.
- **Görünürlük:** `/durum`'da "Model kapısı" satırı her otomatik eylemi ve açık ya da kapalı olduğunu gösterir.

**K-71. Güncelleyici yeni klasörde, git ile ve saatte bir (04.11.2026).**
- **Neden:** Kullanıcı her sürümden sonra `git pull` yapıp botu yeniden başlatmak zorunda kalıyordu. Otomatik güncelleyici (K-27) eski klasöre (`C:\Projeler\QuantBIST`) sabitti. Yeni klasör bir git deposu; zip kopyalamak çalışma ağacını kirletir ve sonraki `git pull`'u bozardı.
- **Karar:**
  - Proje, güncelleyicinin kendi bulunduğu klasördür; sabit yol yok.
  - Git deposunda yalnız ileri sarma yapılır (`git merge --ff-only <yeşil commit>`). Proje başka bir daldaysa ya da izlenen dosyalarda yerel değişiklik varsa güncelleyici durur ve bildirir; hiçbir şeyin üzerine yazılmaz. Geri alma: eski commit'e dönmek.
  - Diğer kapılar aynen geçerli: yalnız CI'ı yeşil sürüm, önce yedek, deneme kopyasında ruff ve testler, paket kilidi değişirse geçici ortamda deneme, bot açılmazsa geri alma.
  - Görev her gün 07:40'tan itibaren saatte bir, 16 saat çalışır. 18:00–20:00 arası rapor saatidir; o arada bekler. Yeni sürüm yoksa sessiz kalır.
- **Kurulum:** Görevi kullanıcı bir kez kurar: `scripts\register_update_task.ps1`. Eski görev aynı adla değiştirilir.

**K-70. Güvenilirlik talimatı resmi iş sırası (kullanıcı, 04.11.2026).**
- **Genel kural:** Eksik veri tahminle ya da sonradan doldurulmaz. Başarısız model başarılı raporlanmaz. Yeni bir kaynağa otomatik erişim, kullanım koşulları doğrulanıp kullanıcı onaylamadan açılmaz.
- **Maddeler ve kabul ölçütleri:**
  1. Eksik günlerin nedeni: 30.10 ve 02.11; veri girilmez. Neden AUDIT'e yazılır; tekrar ederse uyaran bir kontrol olur.
  2. Yedek güvencesi: hata ya da telafi Telegram'a bildirilir. 20 seans %100 yedek ve her hafta başarılı geri yükleme.
  3. Veri doğruluğu: elle indirilen dosya Yahoo'yla gün gün karşılaştırılır. 20 seansta hisselerin ≥ %99'u tutarlı.
  4. Sinyal kaydı ve sanal portföy: gerekçe, risk ve geçerlilik kaydedilir; BIST 100 karşılaştırması yapılır; kazanan ve kaybedenler ayrı ölçülür. Açıklanamayan fark 0.
  5. Model doğrulama: sırayla M31, M32, M30, M1, M5, M8, M27. 14/14 raporlu; geçemeyen kısıtlı kalır.
  6. Temel veri: KAP'tan elle indirilen CSV içe aktarılır. En az 10 hissede hesaplar elle doğrulanır.
  7. İzleme: Windows görevleri PC'den doğrulanır; ölçülemeyen SLO "ölçülemiyor" gösterilir.
- **Tamamlanma:** Bütün SLO'lar en az 20 seans hedefte kalır ve 14/14 model raporlu olur. Bu sağlanmadan sistem "tam güvenilir" sayılmaz.
- **Mimari notu (aynı gün):** Kullanıcı üç modül istedi: otomatik yedekli veri yönlendiricisi, ağırlık düşüren RiskController ve dosya izleyen KAP ETL'si. Uygulanan biçimleri:
  - Doğrulama kaynağı birincil kaynağa (Yahoo) asla geri düşmez. Bağımsız kaynak yoksa sonuç "ölçülemiyor" olur. robots.txt aşılmaz (`core/market/second_source.py`).
  - Modeller sinyal ağırlığı taşımadığı için RiskController yerine bir model kapısı (ModelGate) yapılacak: doğrulanmamış ya da kullanılamaz bir yüksek riskli model hiçbir şeyi otomatik değiştiremez.
  - KAP ETL'si, botun düzenli baktığı bir posta kutusu klasörüyle (`data/inbox/temel/`) yapılacak. Otomatik çekme kapalı kalır.

## 03.11.2026

**K-69. Sürekli açık bot, raporun kaçırdığı günlük işleri telafi eder (03.11.2026, v0.99.30–v0.99.34).**
- **Neden:** 03.11'de kur 23.10'da takılı kaldı ve 02.11'in yedeği yoktu. Bunların ikisi de yalnız 18:30 raporuna bağlıydı. Ayrıca uzun süren bir `/tara ai`, `/panik`'i iki dakika bekletti.
- **Karar:**
  - `/tara ai` arka planda çalışır; aynı anda yalnız bir tane. Acil durdurma hiçbir komutun arkasında beklemez.
  - Bot saatte bir, eksik TCMB kur bültenlerini sorar (en çok 10 istek, 30 sn). Günün bülteni 16:00'dan önce sorulmaz; erken gelen 404 kalıcı "bülten yok" kaydı olurdu.
  - Bot her seans günü 21:00'de günün yedeğine bakar; yoksa alır.
  - Her kur çekişinin sonucu `logs/usd_fetch.json`'a yazılır; kur 5 günden eskiyse `/durum` nedeni gösterir.
  - Bot ve rapor iki ayrı süreç olduğundan her atomik kayıt kendi geçici dosyasını kullanır (`ad.<pid>.tmp`).
- **Sınır:** Bot geçmiş günleri dolduramaz. Kaçırılan canlı ölçüm kaydı (30.10) geri gelmez; 7 günlük SLO penceresinden çıkınca uyarı kalkar.

**K-68. Kartın kendi kuralının ölçümü; ölçümden ÖNCE yazıldı (03.11.2026).**
- **Neden:** `/tara ai` kartı dip dönüşü tetiğinde ertesi açılışta girişi, %2 iz süren stopu, %4 kâr alı ve en çok 10 seansı önerir (K-67). Bu kural hiç ölçülmedi. K-63 saatlik veride 16 mum sonra kapanışı ölçtü; K-64 ise 10 seans sonra en az +%3 etiketini. Modül: `core/analytics/card_study.py`.
- **Veri:** BIST 30 listesindeki hisselerin (`core/config/bist30.py`) düzeltilmiş günlük mumları. Göstergeler ısındıktan sonraki dönem; 02.11.2026 ve sonrası (holdout) kullanılmaz. Bugünkü listenin geçmişe uygulanması hayatta kalma yanlılığı taşır; sonuç bunu not eder.
- **Olay:** Günlük `trigger_mask`'ın doğru olduğu seans. Aynı hissede önceki olaydan sonraki 10 seans içinde gelen tetik yeni olay sayılmaz.
- **Sonuç:** Sanal defterin takip fonksiyonu (`core.signals.store._follow`) birebir kullanılır.
  - Ertesi açılışta giriş; %2 iz süren stop; %4 kâr al; 10. seansın kapanışında süre dolumu.
  - Aynı mumda ikisi birden olursa stop sayılır; boşlukta açılış fiyatı kullanılır; %0,15 maliyet düşülür.
  - Açılış önceki kapanışın %9,5 üstündeyse işlem dolmamış sayılır.
- **Karşılaştırma (taban):** Aynı hisselerin tüm seanslarından aynı giriş ve çıkış kuralıyla yapılan işlemlerin ortalama net getirisi. Fark = olay ortalaması − taban ortalaması.
- **%95 aralığı:** Gün blok bootstrap, 2000 tekrar, tohum 0.
- **Geçme koşulu:**
  - en az 100 olay;
  - farkın %95 aralığının alt ucu 0'ın üstünde;
  - olayların maliyet sonrası ortalaması 0'ın üstünde.
- **Raporlanan:** olay sayısı; hedef, stop ve süre dolumu oranları; ortalama net getiri (olay ve taban); fark ve aralığı.
- **Geçerse ya da geçmezse:** Kartın "Geçmiş ölçüm" satırına bu sonuç da eklenir. Kural, eşik ya da parametre sonuca bakılarak değiştirilmez.
- **Sonuç (03.11.2026, Actions 41716706686): GEÇMEDİ.**
  - 207 olay, 30 hisse. Ortalama net %+0,10; taban %-0,09; fark %+0,19, %95 aralık %-0,25 – %+0,61. Aralık sıfırı içeriyor.
  - Hedef %26, stop %74, süre dolumu %0.
  - Kart bu sonucu v0.99.37'den beri gösteriyor. Kural değiştirilmedi. Yeni bir kural ancak önce burada yazılıp 02.11.2026 sonrası veride ölçülebilir.

**K-67. v3.0: butonla manuel onay, %1 risk lot hesabı, iz süren stop (03.11.2026).**
- **Manuel onay:**
  - `/tara ai`'nin %60 üstü kartları "onay bekliyor" olarak deftere yazılır ve altına [✅ İşleme Gir] [❌ İptal Et] düğmeleri eklenir.
  - İşleme Gir: sinyal "bekliyor" olur, ertesi seans açılışında girilir ve takip başlar. İptal Et: "reddedildi".
  - Düğme yalnız kartın günü geçerlidir; ertesi gün basılırsa "zaman aşımı" olur, çünkü analiz eskimiştir ve giriş açılışı geçmiş olabilir. v0.99.39'dan beri basılmayan kart da ertesi gün kendiliğinden "zaman aşımı" olur.
  - Panik kilidi ya da şalter açıkken düğme işlem açmaz. Düğmeler komutlarla aynı kullanıcı kimliği listesinden geçer.
- **K-64 ile ilişkisi:** Model doğrulanmadığı için sistem kendiliğinden işlem açmaz. Düğmeyle giren pozisyon kullanıcının kendi sanal kararıdır. Kartta "model doğrulanmadı" uyarısı kalır.
- **Lot hesabı:** lot = taban(kasa × %1 ÷ (fiyat × %2)), eldeki nakitle sınırlı.
  - Kasa = gerçekleşmiş sanal kasa. Nakit = kasa − açık pozisyonların maliyeti.
  - Bu kural pozisyonu kasanın %50'si yapar; kart bunu ve boşluklu açılışta kaybın %1'i aşabileceğini yazar.
  - Lot kart anındaki son kapanışla hesaplanır; giriş ertesi açılış olduğundan maliyet biraz değişir.
- **İz süren stop:**
  - Stop, girişten bu yana görülen en yüksek fiyatın %2 altıdır; başlangıçta giriş × 0,98, yalnız yukarı gider.
  - Aynı mumun yükseği o mumun stopunu yükseltmez; mum içi sıra bilinmez.
  - %4 kâr al aynen kalır. /durum zirveyi ve güncel stopu gösterir.
  - Bu kural, ML etiketlerinin ölçtüğü sabit %2 stoptan farklıdır. Defter artık ölçülen kuralı değil, kullanıcının işlem kuralını izler.
- **Panik:** "onay bekliyor" kartları da iptal eder; düğmeler kilitliyken işlem açmaz.

**K-66. Çift yönlü yönetim: kullanıcı kimliği listesi, /panik ve /devam, /tara ai, /durum kasası (03.11.2026).**
- **Kullanıcı kimliği listesi:** Komutlar ve düğmeler yalnız CHAT_ID sohbetinden ve USER_ID kullanıcısından gelirse işlenir. USER_ID boşsa CHAT_ID kullanılır; özel sohbette ikisi aynıdır.
- **/panik:**
  - Bekleyen ve açık sanal sinyalleri "iptal" yapar; sonuçları sayılmaz.
  - `data/panic.lock` dosyasını yazar. Kilit sürerken saatlik takip, günlük sinyal adımı, tarama abonelikleri, yeni sinyal, haftalık model eğitimi ve /tara durur.
  - Bot kapanmaz. Tam kapansaydı Windows görevi 5 dakika sonra yeniden başlatırdı ve telefondan /devam verilemezdi. Bu yüzden "ana döngü" bot süreci değil, otomatik işler olarak yorumlandı.
  - Kilit dosyada olduğu için yeniden başlatmada sürer. /devam kilidi kaldırır.
- **/durum:** Sanal kasa (gerçekleşmiş ve açık pozisyonlar son fiyattan), her açık sinyalin anlık kâr/zararı, stop ve hedefi, panik ve şalter durumu. Defter yoksa dosya oluşturulmaz, kasa 100.000 TL yazılır.
- **/tara ai:**
  - BIST 30 günlük mumlarında dip dönüşü tetiği; her aday sinyal onay katmanına (K-64) soruluyor.
  - Olasılık ≥ 0,60 ise zengin mesaj: hisse, teknik durum, güven skoru, giriş bölgesi, %2 stop, %4 kâr al. Altındaysa "AI Reddi: olasılık %X".
  - Katman örneklem dışı ölçümde geçmedi; bu sürece mesajlar "doğrulanmamış, bilgi amaçlı" etiketi taşır ve sanal deftere sinyal yazılmaz (K-64'e bağlı kalındı).
  - "Alım bölgesi" yerine "giriş bölgesi (ertesi seans açılışı)" yazılır; stop ve hedef gerçek açılışa göre kesinleşir.
- **Model:** İlk /tara ai'de yoksa eğitilir, sonra her Cuma günlük raporun ardından o güne kadar bilinen tüm etiketlerle yeniden eğitilir.

**K-65. Sinyal defteri: seans içi saatlik takip; şalter kapanan işlem zararına göre; kilit /tara'yı da kapsar (03.11.2026).**
- **Talep:** Kullanıcı açık sinyallerin yfinance güncel fiyatlarıyla gerçek zamanlı denetlenmesini istedi. Şalterin tanımı: "bir gün içinde gerçekleşen ve kapanan zararlar %6'ya ulaşırsa bot o gün tüm taramaları ve sinyal üretimini durdurur, kendini kilitler".
- **Takip:**
  - Seans içinde (10:00–19:00, işlem günleri) her saat açık sinyallerin hisseleri saatlik mum olarak indiriliyor; stop ve hedef mum mum denetleniyor. Kural aynı: aynı mumda ikisi birden stop; boşlukta açılışta dolum.
  - Yahoo'nun saatlik mumu yaklaşık 15 dakika gecikmeli. "Gerçek zamanlı" son biten saat demek.
  - 10 seanslık süre dolumuna yalnız günlük kapanış karar veriyor; saatlik veri seansın bittiğini bilemez.
- **Şalter (K-60'ın yerine):** O gün kapanan sinyallerin net sonucu, günün başındaki gerçekleşmiş defter değerinin %6'sı kadar ya da daha fazla zarar ise şalter açılır.
  - Açık pozisyonların kâğıt zararı sayılmaz (kullanıcının tanımı "gerçekleşen ve kapanan").
  - Şalter açıkken `/tara`, tarama abonelikleri ve yeni sinyal o günün sonuna kadar reddedilir; ertesi gün kendiliğinden açılır.
- **Sınır:** Defter sanal; emir ve aracı kurum bağlantısı yok. Sinyaller yalnız ML filtresi örneklem dışı testi geçerse yazılıyor (K-59). Şu an filtre kapalı, yani defter boş kalıyor.

**K-64. Sinyal onay katmanı (meta-etiketleme); ölçümden ÖNCE yazıldı (03.11.2026).**
- **Ne:** Teknik tetik ("dip dönüşü", `core.market.extended.trigger_mask`) bir aday sinyal üretir. RandomForest bu sinyalin başarı olasılığını verir. Olasılık ≥ 0,60 ise "onaylandı", altındaysa "yalancı sinyal". Modül: `core/ml/signal_filter.py`.
- **Olay:** Tetiğin doğru olduğu mum. Aynı hissede önceki olaydan sonraki X mum içinde gelen tetik yeni olay sayılmaz.
- **Etiket:** Giriş ertesi mumun açılışı. X mum sonraki kapanış girişin en az Y üstündeyse 1, değilse 0.
  - Günlük veri: X = 10 seans, Y = %3.
  - Saatlik veri: X = 16 mum, Y = %1,5.
  - Tavan açılışta giriş yok. Etiketin bilindiği an, X mum sonraki kapanış.
- **Öznitelikler (yalnız o mum ve öncesi):**
  - RSI, ADX, Stoch %K ve %D, MACD histogramı, Bollinger %b, ATR / kapanış, CMF;
  - EMA 50 ve EMA 200'e yüzde uzaklık;
  - hacim anomalisi: o mumun hacmi ÷ önceki 5 mumun ortalaması − 1.
- **Model:** RandomForest; 300 ağaç, sınıf ağırlığı dengeli.
  - `max_depth` {3, 4, 5} ve `min_samples_leaf` {10, 25, 50} arasından seçilir.
  - Seçim yalnız eğitim verisi içinde yapılır: 3 katlı zaman sıralı çapraz doğrulama, katlar arası X mum boşluk, ölçüt log-loss. Test verisi ayar seçiminde hiç görülmez.
- **Değerlendirme:** Olaylar zamana göre sıralanır; genişleyen pencereyle 5 dış kat. Eğitim satırının etiketi test katının ilk olayından önce bilinmiş olmalı (temizleme). 02.11.2026 sonrası (holdout) kullanılmaz.
- **Raporlanan:** doğruluk (accuracy), taban oran (tüm olaylarda 1 oranı), onaylanan sinyal sayısı ve isabeti, isabetin gün blok bootstrap %95 aralığı (2000 tekrar, tohum 0).
- **Geçme koşulu:** en az 50 onaylı sinyal ve onaylı isabet aralığının alt ucu taban oranın üstünde. Doğruluk tek başına ölçüt değildir; taban oranı düşükse her şeye "hayır" diyen model de yüksek doğruluk alır.
- **Ölçülecek iki veri:**
  - BIST 100 günlük, 2022'den bugüne; her gün o günkü üyelik, geçmiş üyelik doğru.
  - BIST 30 saatlik, son 1 yıl.
- **Bağlama:** Geçmezse `/tara` ve deftere bağlanmaz. Eşikler (0,60, X, Y, ızgara) sonuca göre değişmez.

**K-63. "Dip dönüşü" tetiğinin ölçümü; ölçümden ÖNCE yazıldı (03.11.2026).**
- **Karar:** Saatlik tetik bota bağlanmadan önce ölçülecek. Ölçülmemiş bir kuralın her saat bildirilmesi kanıtsız sinyal yayınlamak olur.
- **Veri:** BIST 30'un (`core/config/bist30.py`) Yahoo'dan son 1 yıllık saatlik mumları. 02.11.2026 ve sonrası (holdout) kullanılmaz.
- **Olay:** Tetiğin (`core.market.extended.trigger_mask`) doğru olduğu saatin kapanışı. Aynı hissede önceki olaydan sonraki 16 mum içinde gelen tetik yeni olay sayılmaz; üst üste binen sonuçlar böylece ayrılır.
- **Sonuç:** Ertesi saatin açılışında giriş, 16 mum (yaklaşık 2 seans) sonraki kapanışta çıkış; %0,15 maliyet düşülür. Yan sonuç olarak 8 mum da raporlanır, ama karar 16 mumla verilir.
- **Karşılaştırma:** Aynı hisselerin tüm saatlerinden aynı kuralla (ertesi açılış → 16 mum sonra kapanış, maliyetli) yapılan girişlerin ortalaması. Fark = olay ortalaması − taban ortalaması.
- **%95 aralığı:** Gün blok bootstrap (aynı gündeki olaylar birlikte yeniden örneklenir), 2000 tekrar, tohum 0.
- **Geçme koşulu:**
  - en az 100 olay;
  - farkın aralığının alt ucu > 0;
  - olayların maliyet sonrası ortalaması > 0.
- **Sonrası:** Geçerse saatlik tarama bota "kural çıktısı" olarak bağlanır. Geçmezse bağlanmaz ve sonuç olduğu gibi kaydedilir. Tetiğin eşikleri (RSI 35, Stoch 20, %b 0,10) sonuca göre değiştirilmez.

**K-62. ML filtresi için ikinci kural; ölçümden ÖNCE yazıldı (03.11.2026).**
- **Neden:** İlk kural (K-59: %2 stop / %4 hedef) örneklem dışında %34 isabet verdi; taban %33,8. Rastgeleden ayırt edilemedi. Eşik gevşetilmiyor. Kullanıcı farklı ve önceden tanımlı bir kuralla yeniden denemeyi istedi.
- **Kural "goreli20":** Etiket şu soruya evet ise 1: "Hisse, ertesi açılıştan 20. seansın kapanışına kadar, %0,15 maliyetten sonra XU100'ün aynı dönemdeki getirisini geçti mi?"
  - XU100 getirisi t kapanışından t+20 kapanışına ölçülür.
  - Tavan açılışta giriş yok.
  - Etiketin bilindiği gün t+20'dir.
- **Öznitelikler:** K-59'dakilerle aynı; hiçbiri eklenmedi ya da çıkarılmadı.
- **Model:** K-59'dakiyle aynı; ayarlar değişmedi.
- **Ölçüm:**
  - takvim yılı bazında genişleyen pencere, temizleme (purge) ve holdout aynı;
  - test günleri 20 seans arayla seçilir, böylece aynı hissenin test etiketleri üst üste binmez;
  - isabetin %95 aralığı, test tarihleri yeniden örneklenerek hesaplanır (tarih blok bootstrap, 2000 tekrar, tohum 0). Aynı gündeki hisseler birlikte hareket ettiği için tek tek bağımsız sayılmaz.
- **Açılma koşulu (K-59 ile aynı):** en az 100 sinyal, isabet ≥ %60 ve aralığın alt ucu taban oranın üstünde.
- **Evren:** yaklaşık BIST 30 ve BIST 100; ikisi de raporlanır.
- **Bağlama:** Kural geçerse sanal deftere bağlamak ayrı bir adım olacak (defter şimdilik stop/hedef kuralıyla çalışıyor). Geçmezse sonuç olduğu gibi kaydedilir.

**K-61. Codex dosyaları incelendi; hiçbiri ana koda alınmadı (03.11.2026).**
- **Kaynak:** Kullanıcı Codex ile yapılan işleri `codex/bist30` dalına gönderdi (`codex_import/`, 4 dosya, 214 satır).
- **`quantbist-verified-fixes-...patch`:** `setup.ps1` git kontrolü ve `test_runs` saat sabitlemesi. İkisi de kodda zaten var.
- **`price_fix_gate.py` ve `safe_research.py`:** Fiyat düzeltme onay kapısı. `core/market/corrections.py` aynı kapıyı zaten uyguluyor; üstüne kaynak zorunluluğu ve tek özel kopyadan okuma da var. Codex sürümü PC'deki tek bir araştırma veritabanının SHA'sına sabitli, başka makinede çalışmaz.
- **`local_pc_audit_m.py`:** Denetim raporunu `docs/` içine yazıyor. PC yolları herkese açık depoya girerdi; alınmadı.
- Dal olduğu gibi duruyor; silinmedi.

**K-60. Sanal sinyal defteri SQLite'ta; %6 şalter (03.11.2026).**
- **Dosya:** `data/signals.db`. Kişisel dosya; depoya girmez (`data/*.db`), günlük yedeğe girer.
- **Kurallar:** Takip, ML etiketleriyle aynı kurallarla yapılıyor: ertesi açılışta giriş, %2 stop, %4 hedef, en çok 10 seans, aynı seansta ikisi birden stop sayılır, tavan açılışta giriş yok, %0,15 maliyet. Ölçülen ile izlenen aynı şey olsun diye.
- **Sanal bakiye:** 100.000 TL; her sinyal 10.000 TL.
- **Fiyat:** Takip seans sonu kesin mumlarla yapılıyor. Yahoo'nun gün içi fiyatı 15 dakika gecikmeli ve tavan/taban sırasını bilmiyor.
- **Şalter:** Defterin değeri bir seansta %6 veya daha fazla düşerse, o seansın kapanışında üretilen sinyaller kaydedilmez. Ertesi kapanışta kayıt yeniden açılır.
- **Sınır:** Gerçek parayla emir ve aracı kurum bağlantısı yok.

**K-59. BIST 30 tarama robotu hedefi; ML filtresi yalnız örneklem dışı ölçümle açılır (03.11.2026).**
- **Talep:** Kullanıcı yeni mimariyi verdi: BIST 30, genişletilmiş göstergeler, RandomForest filtresi (%60 eşik), SQLite sinyal kaydı (%2 stop, %4 hedef), günlük %6 sanal zarar şalteri, `/tara` ve `/durum` bağlantısı. Bütün adımlara onay verdi. Sınırlar aynı: gerçek parayla emir yok, aracı kurum bağlantısı yok.
- **Göstergeler:** pandas-ta yerine mevcut `ta` kütüphanesi kullanıldı (pandas-ta numpy 2 ile açılmıyor). Eksik olan CMF eklendi; diğerleri zaten vardı.
- **Etiket:** Ertesi açılışta giriş, %2 stop, %4 hedef, en çok 10 seans. Aynı seansta ikisine birden dokunursa stop sayılır. Tavan açılışta giriş yok. Net sonuçtan %0,15 maliyet düşülür.
- **Model:** RandomForest; 300 ağaç, derinlik 6, yaprakta en az 100 örnek. Ayarlar sonuç görülmeden sabitlendi.
- **Ölçüm:** Takvim yılı bazında genişleyen pencere. Eğitim satırının etiketi test yılından önce bilinmiş olmalı (temizleme). 02.11.2026 sonrası (holdout) hiç kullanılmaz.
- **"%60" tanımı:** Model sinyal verdiğinde (olasılık ≥ 0,5) hedefe önce ulaşma oranı. Filtre üç koşulla açılır:
  - en az 100 sinyal;
  - isabet ≥ %60;
  - %95 aralığının alt ucu, tüm girişlerde hedefe ulaşma oranının üstünde.
  Üçüncü koşulun nedeni: taban oran zaten yüksekse %60 bir şey katmaz. Koşullar sağlanmazsa filtre kapalı kalır ve nedeni yazılır.
- **Evren:** Resmi BIST 30 listesinin kaynağı yok. Kaynak gelene kadar yaklaşık liste kullanılıyor: her gün, o günün BIST 100 üyelerinden önceki 20 seansın TL hacmine göre en likit 30 hisse (geçmişe dönük doğru üyelik).

## 27.10.2026

**K-58. Talimat F'nin geri kalanı açıldı; bağımsız doğrulama başladı (29.10.2026).**
- **Kapı:** F'nin kapısı "B'nin bitti ölçütü"ydü. B'den kalan tek şey canlı senaryo kaydının PC kanıtı. Var olan modellerin doğrulanması o kanıta bağlı değil. Kullanıcının devriyle (K-54) F2 şimdi başlıyor; B'nin kanıtı ayrıca izleniyor.
- **Bağımsızlık (F3):** her doğrulama, modeli geliştirmemiş ayrı bir alt ajan tarafından yapılır.
  - Doğrulayıcı DECISIONS, ROADMAP, CHANGELOG ve git geçmişini görmez; yalnız kodu, testleri, kullanıcı belgelerini ve veriyi görür.
  - Yalnız `docs/validation/<model>.md` yazar.
  - Sıra MODELS.md'deki yüksek risk sırasıdır.
- **Rapor biçimi (F2):** kavramsal sağlamlık, elle hesaplanmış örneklerle uygulama doğruluğu, sonuç analizi, sınırlamalar ve karar. Raporda "Tarih: YYYY-MM-DD" ve "Karar: kullanılabilir / kısıtlı kullanılabilir / kullanılamaz" satırları zorunlu.
  - YÜKSEK bulgu düzeltilmeden model "kullanılabilir" sayılmaz.
  - Bulgular önem sırasıyla ROADMAP'e yazılır.
- **İzleme (F5–F6):**
  - `/durum` "Model doğrulama" satırı kaç yüksek riskli modelin doğrulandığını gösterir.
  - Süresi geçen (yüksek risk 1 yıl, orta risk 2 yıl) ya da "kullanılamaz" çıkan model UYARI verir.
  - Takvim MAINTENANCE.md'de.
- **Değişiklik kontrolü (F4):** bir modelin hesabını değiştiren sürüm, CHANGELOG'da modelin kodunu (M..) ve "yeniden doğrulama gerekir" notunu yazar. Bu notu öz-denetim denetler.

**K-57. Profesyonel filtreler Aşama 4: temel puanlar (29.10.2026; formüller veri görülmeden sabitlendi).**

**Kaynak ve dönemler:**
- Kaynak `data/fundamentals.csv` (K-48, yayın tarihli). Bir değer yayımın ertesi gününden itibaren kullanılır.
- **Dönem:** en son yayımlanan dönem (t) ve bir yıl önceki aynı dönem (t−1). Türkiye'de ara dönem tabloları yılbaşından kümülatiftir, aynı çeyrekler karşılaştırılır.
- **TMS 29:** t ile t−1'in enflasyon düzeltmesi farklıysa (biri 1, diğeri 0) değişim içeren ölçüler hesaplanmaz: "TMS 29 geçişi".
- Bir kalem eksikse o ölçü "veri yok" olur. Eksik kalem sıfır sayılmaz.
- Dönen/kısa vadeli ayrımı olmayan bilançolarda (`current_assets` yok, örneğin bankalar) Altman Z ve Beneish M "uygulanamaz" olur. Sektör bilgisi yok (K-54); ayrım bilanço yapısından yapılır.

**1. Piotroski F (0–9; Piotroski 2000).** Her biri 1 puan:
- ROA > 0 (net kâr ÷ toplam varlık);
- işletme nakit akışı > 0;
- ΔROA > 0;
- işletme nakit akışı > net kâr;
- Δ(uzun vadeli finansal borç ÷ toplam varlık) < 0;
- Δ(dönen varlık ÷ kısa vadeli yükümlülük) > 0;
- ödenmiş sermaye artmadı;
- Δ brüt marj > 0;
- Δ(hasılat ÷ toplam varlık) > 0.
Bir bileşen hesaplanamazsa puan "kısmi (n/9 bileşen)" olarak gösterilir, tam puan sayılmaz.

**2. Altman Z'' (gelişen piyasalar sürümü, Altman 2005).** Z'' = 3,25 + 6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4.
- X1 = (dönen varlık − kısa vadeli yükümlülük) ÷ toplam varlık.
- X2 = geçmiş yıllar kârları ÷ toplam varlık.
- X3 = FVÖK ÷ toplam varlık.
- X4 = özkaynak ÷ toplam yükümlülük.
- Okuma (Altman): < 1,1 sıkıntı bölgesi; 1,1–2,6 gri; > 2,6 güvenli bölge.

**3. Beneish M (8 değişkenli, Beneish 1999).** M = −4,84 + 0,920·DSRI + 0,528·GMI + 0,404·AQI + 0,892·SGI + 0,115·DEPI − 0,172·SGAI + 4,679·TATA − 0,327·LVGI.
- DSRI = (alacak ÷ hasılat)_t ÷ (…)_{t−1}.
- GMI = brüt marj_{t−1} ÷ brüt marj_t.
- AQI = (1 − (dönen + MDV) ÷ TV)_t ÷ (…)_{t−1}.
- SGI = hasılat_t ÷ hasılat_{t−1}.
- DEPI = (amortisman ÷ (amortisman + MDV))_{t−1} ÷ (…)_t.
- SGAI = (GYG ÷ hasılat)_t ÷ (…)_{t−1}.
- LVGI = ((KVY + UV finansal borç) ÷ TV)_t ÷ (…)_{t−1}.
- TATA = (net kâr − işletme nakit akışı) ÷ TV_t.
- Okuma: M > −1,78 "kazanç kalitesi incelenmeli" (Beneish). Bu bir uyarı etiketidir, hile tespiti değildir.

**4. Sihirli formül bileşenleri (Greenblatt 2005).**
- Kazanç getirisi = FVÖK ÷ (piyasa değeri + finansal borç − nakit).
- Sermaye getirisi = FVÖK ÷ ((dönen varlık − kısa vadeli yükümlülük) + MDV).
- Piyasa değeri = son kapanış × ödenmiş sermaye (nominal 1 TL = 1 pay).
- Sıra, evren içinde iki sıranın toplamıdır (`/tara` evreni).

**5. Kalite + değer (Novy-Marx 2013).**
- Brüt kârlılık = brüt kâr ÷ toplam varlık.
- Defter/piyasa = özkaynak ÷ piyasa değeri.
- Birleşik sıra iki sıranın ortalamasıdır.

**Gösterim ve sınama:** `/temel THYAO` her ölçünün değerini, bileşenlerini ve dönemini gösterir; veri yoksa "veri yok" der. Bunlar kural çıktısıdır, öneri değildir. Hiçbir puan sonuçlara bakılarak ayarlanmaz. "Kârlılık + değer" hipotezi yalnız Aşama 5'in ön kaydı ve kullanıcının onayıyla sınanır.

**K-56. Talimat E: risk bütçesi, ölçüler ve pencereler (29.10.2026; sonuç görülmeden).** Sistem ölçer; sınırları kullanıcı koyar. Öneri yok.

**Sınır dosyası `data/risk_limits.csv`:**
- Kişisel; yedeğe ve şema denetimine girer; git'e girmez.
- Sütunlar: `account` (gercek / sanal / hepsi), `limit`, `value` (yüzde), `note`.
- Sınırlar:
  - `tek_hisse`: bir pozisyonun hesaba oranı.
  - `tek_sektor`: sektör kaynağı olmadığı için (K-54) ölçülmez, "bilinmiyor".
  - `oynaklik`: yıllık portföy oynaklığı.
  - `dusus`: hesabın zirveden düşüşü.
  - `var_1g`: 1 günlük %95 tarihsel kayıp.
- Dosya yoksa ya da bir sınır yazılmamışsa yalnız ölçülür ve "sınır tanımlı değil" yazar.

**Ölçüler** (pencereler sabit):
- **Ağırlık:** pozisyon değeri ÷ hesap değeri (sanal hesapta nakit dahil; gerçek hesapta yalnız hisse değeri, çünkü nakit izlenmiyor).
- **Portföy oynaklığı:** son 60 seansın günlük getirilerinden kovaryans Σ; σ = √(wᵀΣw) × √252.
- **Risk katkısı:** w_i·(Σw)_i ÷ (wᵀΣw), yüzde olarak; toplamı %100.
- **Beta:** son 250 seansta bugünkü ağırlıklarla portföy getirisinin XU100'e göre kovaryans ÷ varyansı.
- **Korelasyon kümeleri:** 60 seansta korelasyonu ≥ 0,80 olan çiftler (mevcut kural).
- **Etkin pozisyon sayısı:** mevcut tanım.
- **1 günlük kayıp:** mevcut tarihsel VaR (250 seans, %95).
- **Likidite:** pozisyonun kapanması için gereken gün = pozisyon değeri ÷ (önceki 20 seansın ortalama TL hacmi × %20 katılım).
- **Düşüş:** hesap performans endeksinin (alım-satım nakit akışı arındırılmış) en yüksek değerinden bugüne düşüşü.
- **Stres:** mevcut `/stres`'e bağlantı verilir.
- **Durum:** kullanım = ölçü ÷ sınır. Yeşil < %80, sarı ≥ %80, kırmızı > %100.
- **Hesaplanamayanlar:** fiyatı olmayan pozisyon sessizce düşmez, "hesaplanamadı: nedeni" yazılır. Gerçek ve sanal hesap hiçbir hesapta karışmaz.

**Komutlar:**
- `/risk [gercek|sanal]`: tablo (varsayılan sanal).
- `/risk ekle THYAO 100 [gercek|sanal]`: son kapanışla 100 adet eklenseydi tablo nasıl değişirdi. Emir oluşturmaz.
- `/risk denge [gercek|sanal]`: tanımlı sınırlara dönmek için gereken azaltma, yalnız matematik.
  - `tek_hisse` aşan pozisyon sınıra indirilir.
  - Oynaklık ya da VaR aşılırsa bütün pozisyonlar aynı oranda (sınır ÷ ölçü) küçültülür.
  - Etiket: "hesap sonucu, öneri değil".

**Uyarılar:** sarı ve kırmızı sınırlar mevcut uyarı kaydına (`alerts_log`) "risk_siniri:<ad>" kuralıyla girer. Aynı uyarı tekrar etmez (mevcut sistem). Günlük raporda tek satırlık risk bütçesi özeti çıkar.

**K-55. Özellik B: üç senaryo şablonu (29.10.2026; SONUÇ GÖRÜLMEDEN commit edildi, parametreler bundan sonra değişmez).** Bu bir hesap aracıdır, öneri sistemi değildir. Seviyeler K-49'un küme seviyeleridir. Bir günün seviyeleri yalnız o güne kadarki mumlarla hesaplanır. ATR = o günün ATR14'ü.

**Ortak kurallar** (sinyal günü t, kapanıştan sonra):
- **Giriş varsayımı:** t+1 açılışı.
  - t+1 açılışı t kapanışının %9,5 üstündeyse (tavan) ya da altındaysa (taban) senaryo dolmaz: "dolmadı".
  - Canlı çıktıda giriş henüz bilinmediği için R, t kapanışıyla yaklaşık olarak gösterilir ve bu yazılır.
  - **Ek (29.10, ilk gerçek karnede görülen tanımsız durum; parametre değişikliği değil):** t+1 açılışı geçersizliğin altında ya da hedefin üstündeyse girilecek senaryo kalmamıştır: "dolmadı". Önceden R tanımsız kalıyordu ve karne aralığı hesaplanamıyordu.
- **Maliyet:** her yön %0,10 komisyon + %0,05 kayma (c = %0,15).
  - R = (hedef·(1−c) − giriş·(1+c)) ÷ (giriş·(1+c) − geçersizlik·(1−c)).
  - **R < 1,5: "elverişsiz".** Geçersizlik girişin altında değilse ya da hedef girişin üstünde değilse senaryo kurulmaz.
- **Sonuç** (karne ve canlı kayıt aynı tanımla), t+1'den itibaren her seans için:
  - Açılış geçersizliğin altındaysa çıkış açılıştan (boşluk). Değilse düşük ≤ geçersizlik ise çıkış geçersizlikten.
  - Açılış hedefin üstündeyse çıkış açılıştan. Değilse yüksek ≥ hedef ise çıkış hedeften.
  - **Aynı seans ikisi birden: geçersizlik sayılır** (temkinli).
  - 20 seansta hiçbiri olmazsa 20. seansın kapanışından çıkılır: "süre doldu".
  - Sonuç maliyet sonrası R olarak (kâr ÷ giriş riski) ve aynı süredeki XU100'e göre fark olarak yazılır.
- **Tavan/taban riski:** çıktıda her zaman yazılır: geçersizliğe uzaklık % olarak ve "tek seansta ±%10 limit hareketi geçersizliği atlayabilir". Son 10 seansta limit günü varsa ayrıca belirtilir.

**1. `destek_tepkisi`**
- Koşul: kapanışın altındaki en yakın küme desteği S, güç puanı ≥ 50 ve kapanış − S ≤ 0,5 ATR.
- Geçersizlik: S − 1 ATR.
- Hedef: kapanışın üstündeki en yakın küme direnci. Yoksa senaryo kurulmaz.

**2. `direnc_kirilimi`**
- Koşul: dünün kapanışın üstündeki en yakın küme direnci D, bugün kapanışla 0,5 ATR'den fazla aşılmış (K-49 kırılım tanımı) ve hacim ≥ 1,5 × önceki 20 seansın ortalaması.
- Geçersizlik: D − 1 ATR.
- Hedef: bugünkü seviyelerde kapanışın üstündeki en yakın küme direnci. Yoksa giriş + 2 × (giriş − geçersizlik).

**3. `trend_geri_cekilme`**
- Koşul: sma50 > sma200, kapanış > sma50 ve |kapanış − sma20| ≤ 0,5 ATR.
- Geçersizlik: kapanışın altındaki en yakın küme desteği − 1 ATR. Yoksa sma50 − 1 ATR.
- Hedef: kapanışın üstündeki en yakın küme direnci. Yoksa giriş + 2 × (giriş − geçersizlik).

**Not (öz-denetim 9, Ö35):** "giriş + 2 × (giriş − geçersizlik)" hedefi sinyal günü sabitlenir. O gün giriş bilinmediği için kapanışla kurulur. Ertesi açılış farklıysa gerçekleşen R 2'den biraz sapar; geleceği görmemenin bedelidir.

**Adet hesabı (yalnız gösterilir):**
- Risk tutarı = hesap değeri × risk bütçesi (varsayılan %1; kullanıcı `risk=%0,5` yazabilir).
- Adet = taban(risk tutarı ÷ (giriş − geçersizlik)).
- Likidite sınırı: adet × giriş ≤ önceki 20 seansın ortalama TL hacminin %5'i. Hangisi küçükse o yazılır ve nedeni belirtilir.
- Sanal emir yalnız kullanıcının `/paper` komutuyla oluşur.

**Ölçüm:**
- Karne: tarama dönemi; holdout yok; BIST 100 geçmiş üyeleri; eleme varsayılanları. Şunlar ölçülür: olay sayısı, hedef / geçersizlik / süre doldu oranları, ortalama R (maliyet sonrası), en kötü ardışık geçersizlik serisi, XU100'e göre fark.
- Canlı kayıt: her akşam tetiklenenler `logs/scenarios_log.csv` dosyasına sonuç bilinmeden yazılır. `/performans` "Senaryolar" bölümü sonuçları gösterir.
- "İşe yaradığı" iddiası yalnız a5 döngüsüyle sınanabilir (ön kayıt, bütçe, holdout; en erken 28.04.2027).

**K-54. Kullanıcı kararları devretti; bekleyen kaynak ve kapı kararları (29.10.2026).** Kullanıcı: "karar kısımlarını bana sormana gerek yok, en profesyonel haline getirmek için onay gerekmeden devam et". Kesin sınırlar aynen geçerli. Bunlar kullanıcı istese bile benim yapamayacağım şeylerdir: gerçek para, aracı kurum, ödeme, hesap açma, şifre ya da token, al/sat önerisi, KAP/Telegram içeriğini yeniden yayımlamak, git geçmişini yeniden yazmak, kişisel kayıt silmek. Kaynak koşulları 29.10'da yeniden arşivlendi: `sources/2026-10-29_09-28-44`.

1. **D13 – İş Yatırım: otomatik kullanım kapatıldı.**
   - Gerekçe: robots.txt bütün botlara `Disallow: /_layouts/` diyor; veri ucumuz bu yolun altında. Kural: otomatik çekmeyi yasaklayan kaynak kullanılmaz. Kaynak isteğe bağlı bir ikinci kaynaktı.
   - Uygulama: `crosscheck.ENABLED = False`, tek nokta.
   - Bedel: "Veri doğruluğu" SLO'su "bilinmiyor (D13)" olur. Yahoo çökünce gelen bilgi mesajı gelmez. Kurumsal işlem şüphelerinde ikinci kaynak kanıtı yoktur; KAP metni ve fiyat kopukluğu kalır.
   - Karşılaştırma kodu duruyor ve kayıtlı veriyle test ediliyor.
2. **D15 (yeni) – Yahoo'nun şartları da otomatik toplamayı yasaklıyor.** Arşiv `007.html`: "access or collect data … using any automated means … without our express, prior permission".
   - Ücretsiz ve otomatik çekmeye izin veren bir BIST gün sonu fiyat kaynağı bulunamadı. Borsa İstanbul saklamayı yasaklıyor (D14); İş Yatırım ve Yahoo otomatik erişimi yasaklıyor; geri kalanlar ücretli.
   - Sistem fiyat olmadan çalışmaz. Uyumlu çözüm lisanslı (ücretli) bir veri kaynağıdır; ödeme kararı benim veremeyeceğim kararlardandır.
   - **Karar:** mevcut kişisel, ticari olmayan ve düşük hacimli kullanım (günde bir toplu indirme) belgelenmiş risk olarak sürer. Yahoo kullanımı genişletilmez: hisse başına ek sorgu ya da sayfa kazıma yok.
   - Kullanıcıya seçenek olarak yazıldı (AUDIT D15).
3. **D14 – Sektör ataması: kaynak yok, "bilinmiyor".**
   - Borsa İstanbul listesi saklanamıyor.
   - KAP şirket kartı: koşulu teyit edilmedi, ayrıca kullanıcı kuralı KAP içeriğini depoya koymayı yasaklıyor.
   - Yahoo sektörü hisse başına ek sorgu ister, yani D15'i genişletir.
   - Tahminle sektör (örneğin korelasyonla) C3 gereği yapılmaz.
   - Sonuç: C, sektör kısmı dışında tamam sayılır. `/piyasa`'daki sektör endeksi fiyatları (dört ana endeks, mevcut toplu indirmenin içinde) kalır.
4. **E'nin kapısı açıldı.** Sektör yoğunlaşması sınırı, sektör kaynağı olmadığı için etkin değildir ve "bilinmiyor" yazar. Risk bütçesinin geri kalanı sektöre bağlı değil.
5. **B'nin kapısı açıldı.** A'nın kodu tamamlandı; PC kanıtı (seviye kaydı, 30.10 akşamı) izlenmeye devam ediyor. Şablonlar sonuç görülmeden DECISIONS'a yazılır.
6. **KAP koşulu:** kullanım koşulu sayfası bulunamadı (404). robots.txt GitHub sunucusuna hata sayfası döndü.
   - Mevcut düşük hacimli kullanım (haftalık KAP kontrolü, elle `kap.yml`) sürer. KAP metni depoya girmez.
   - D (günlük otomatik KAP izleme) koşul bulunana kadar kapalı kalır. Bu, otomatik kullanımın genişlemesi olurdu.

**K-53. Eleme filtresinin canlı ölçümü (29.10.2026, ileri hedef 1).**
- **Ne ölçülür:** her akşam bugünkü BIST 100'e `/tara`'nın varsayılan eleme ayarları uygulanır (K-45: likidite, kurumsal, hareket, veri; ikinci kaynak şüphelileri dahil). Koşul her hissenin sağladığı `kapanis>0`'dır, böylece yalnız eleme ayırır.
  - Elenenler "elenen", kalanlar "kalan" görünümüyle `signal_log`'a "eleme" kaynağıyla yazılır. Puan 0'dır; eleme nedeni `details` sütununa girer.
  - Her hisse ve veri günü için bir kez yazılır.
- **Nasıl ölçülür:** canlı ölçümle aynı tanım. Giriş ertesi açılıştır; 5 ve 20 seans tutulur; sonuç XU100'e göre farktır.
  - Gruplar ayrı ayrı özetlenir.
  - "Fark", gün gün (elenen ortalaması − kalan ortalaması) serisinin ortalamasıdır. Aralığı mevcut `summarize`'ın çakışmayan dönemleriyle hesaplanır.
  - En az 30 olgun elenen kaydından önce sayı gösterilmez.
- **Referans:** kullanıcının PC keşif testinde elenen grup −%3,07 [−5,53; −0,06] (20 seans, maliyet hariç, tarama dönemi). Bu bir referanstır, kanıt değildir. Asıl soru ileri veride tekrar edip etmediği.
- **Değişmeyen:** teknik görünümün canlı ölçümü ve onun karar ölçütü (H, Kasım sonu). Yeni kaynak "sorulan kayıtlar" sayımına girmez.

**K-52. C kapısı açıldı; TÜFE kaynağı TCMB tablosu; yeni aylar ilk görüldüğü günle (29.10.2026).**
- **Kapı:** kullanıcı 28.10 akşamı "daha da ötesini yapabilirsin" dedi. Bir önceki mesajım "'C'yi şimdi başlat' yazarsanız başlarım" diyordu; bunu C'nin kapısını açma onayı olarak okudum.
  - D'nin kapısı açılmadı: KAP kullanım koşulunun teyidi ek ön koşuldur.
  - E (C'nin bitmesi) ve F'nin geri kalanı (B'nin bitmesi) aynı kaldı.
- **TÜFE kaynağı değişti:** K-51 TÜİK bülteninden elle girişi seçmişti. TCMB'nin "Tüketici Fiyatları" tablosu aynı TÜİK rakamlarını veriyor ve şartları arşivli (kaynak gösterilerek, ticari olmayan). Bu yüzden ondan alındı. Elle tek satır bile yazılmadı; dosya arşivlenmiş sayfadan bir betikle üretildi.
- **Yayım tarihi:**
  - Geçmiş aylar: kural (ayın 3'ü; hafta sonuysa pazartesi) ve iki kaynaklı istisna.
  - PC'nin eklediği yeni aylar: ilk görüldüğü gün. Bu tarih gerçek açıklamadan önce olamaz.
  - Bilinen sınır: kaynağı olmayan başka bir erteleme olduysa, geçmişte en çok birkaç gün erken görülmüş olabilir. Etkisi bir aylık TÜFE'nin birkaç günlük kayması kadardır; birincil ölçüt bunu kullanmaz.
- **Kur önbelleği:** `data/macro/usdtry.csv` yerel ve git dışındadır. Akşam raporu ve v0.99.32'den beri bot da (saatte bir, K-69) son 14 günden eksik bültenleri ister (en çok 10 istek). Bülteni olmayan gün (tatil, yarım gün; 404) hatırlanır, ağ hatası hatırlanmaz.
- **Gösterim:** dört baz yalnız ek satırdır.
  - Günlük raporda her hesabın altında "ilk kayıttan bu yana".
  - `/performans`'ta sanal hesap ve aynı dönemin XU100'ü.
  - Canlı ölçümün XU100'e göre fazla getiri ölçütü ve araştırmanın birincil ölçütü değişmedi.

**K-51. C/D/E/F paketi: kapıların okunuşu ve C1 tasarımı (28.10.2026; sonuç görülmeden yazıldı).**

**Kapılar.** Paket C ve D için "Talimat 1'in", F için "Talimat 2'nin" bitti ölçütünü şart koşuyor. Bu adlarla bir belge depoda yok. Yüklenen PROFESYONEL_TALIMAT_1'de ne "bitti ölçütü" ne de "§2" var. Özellik A ise "Talimat 1 §2" ile veri borcunu anıyordu.
- **Okuyuş:** Talimat 1 = Özellik Talimatı A (destek/direnç), Talimat 2 = Özellik Talimatı B (senaryolar). Gerekçe: paket C/D'yi "Talimat 1'den sonra", E'yi "C'den sonra" sıralıyor. F'nin doğrulayacağı modeller arasında "senaryolar" var; bu model B bitmeden yok.
- **Ek koşul:** A'nın kendi giriş kapısı olan veri borcu da kapandı (K-50). Böylece iki okuyuşun ikisinde de C/D'nin kapısı aynı noktada açılır: A'nın bitti ölçütü, yani PC'de seviye kaydının yazıldığının kanıtı.
- **Kanıt:** en erken 30.10 akşam raporu (29.10 bayram).
- **Düzeltme:** kullanıcı başka bir belgeyi kastediyorsa bu karar değişir; o zamana kadar kod yazılmaz.

**C1.1 Kaynaklar** (ayrıntı docs/DATA_SOURCES.md):
- **USD/TRY:** TCMB gösterge kuru XML'i, `ForexBuying`.
  - d gününün kuru d bülteninden alınır (yaklaşık 15:30, kapanıştan önce). Bülten yoksa son bülten ileri taşınır.
  - İkinci kaynak Yahoo `USDTRY=X`. Fark %1'i aşarsa `/durum`'da veri notu çıkar; değer değiştirilmez.
  - EVDS anahtarı yalnız XML yolu kapanırsa gerekir.
- **TÜFE:** TÜİK bülteni, otomatik çekme yok (koşul teyit edilmedi). Her ay elle tek satır girilir, yayım tarihi ve kaynakla.
- **Faiz:** mevcut `data/cash/policy_rate.csv`.
- **Sektör:** Borsa İstanbul'un pay–endeks dosyası (`hisse_endeks_ds.csv`) kullanılmaz. Telif bildirimi bilginin yazılı izinsiz saklanmasını yasaklıyor (AUDIT D14).
  - Kalan yollar: Borsa İstanbul'dan yazılı izin, KAP şirket kartı (koşul teyit bekliyor) ya da Yahoo sektörü (farklı sınıflama, adıyla yazılır).
  - Seçim kullanıcı kararıdır. O zamana kadar sektör "bilinmiyor" olur. C'nin sektör kısmı bu karara, reel/USD/nakit ve rejim kısmı yalnız kapıya bağlıdır.
  - Sektör endeks fiyatları Yahoo'dan gelir (mevcut kaynak).

**C1.2 Reel getiri** = (1 + nominal) / (TÜFE_son / TÜFE_baş) − 1.
- Her ucun TÜFE'si o gün **bilinen** son değerdir. Bir değer yayım gününün ertesi gününden itibaren kullanılır; temel veri deposuyla aynı ve daha güvenli kural.
- Ay içi tahmin yok. Bu yüzden bir aydan kısa pencerede reel getiri nominale eşit ya da ona çok yakın çıkabilir. Çıktıda "TÜFE: son yayımlanan (AA.YYYY), tahmin değil" yazar.

**USD getiri** = (1 + nominal) × (kur_baş / kur_son) − 1.

**Nakde göre:** mevcut nakit hesabı (K-22 RESEARCH_PROGRAM birincil ölçütü değişmez; dört baz ek bilgidir).

**C1.3 Piyasa rejimi** (sabit; eşikler sonuçlara göre ayarlanmaz). Her gün yalnız o günün kapanışına kadarki veriyle hesaplanır:
- **Trend:** XU100 kapanışı 200 seanslık basit ortalamasının üstünde ya da altında.
- **Oynaklık:** XU100 günlük log getirilerinin 20 seanslık standart sapması. Bu değerin önceki 252 seans içindeki yüzdeliği bulunur; ≥ 80 ise "yüksek oynaklık".
- **Genişlik:** o gün BIST 100 üyesi olan (geçmiş üyelik) hisselerden kapanışı kendi EMA50'sinin üstünde olanların oranı. Tanım Talimat 1 Evre 4'ten alındı.
- **Etiket:**
  - "yüksek oynaklık": oynaklık yüzdeliği ≥ 80; diğerlerinden önce gelir.
  - "yükseliş": trend üstte ve genişlik ≥ %50.
  - "düşüş": trend altta ve genişlik < %50.
  - "karışık": diğer durumlar.
  - "bilinmiyor": herhangi bir girdi yok (200 seans geçmiş, 252 yüzdelik penceresi ya da 20'den az üye).
- **Kullanım:** rejim bir etikettir, sinyal değildir. `/tara`'da yalnız filtre olarak kullanılır. Araştırma raporundaki 63 seanslık rejim (`reliability.market_regime`, MODELS M19) ayrı kalır ve adı ayrı yazılır.

**C1.4 Sektör göreli gücü:**
- Sektör endeksinin 1, 5 ve 20 seanslık getirisi eksi XU100'ünki (puan).
- Hisse için: 20 seanslık getirisi eksi sektör endeksininki.
- Sektör endeksi fiyatı yoksa "bilinmiyor".

**C1.5 Veri yeri:** `data/macro/` (kaynaklı kamu verisi, kişisel değil): `usdtry.csv`, `cpi.csv`, `sectors.csv` (hisse, sektör, endeks kodu, kaynak, tarih). Tazelik `/durum`'da görünür. Bunların hepsi kapı açılınca yazılır.

**Tasarım dışı kalanlar:** D, E ve F'nin tasarımı kendi kapıları açılınca yazılır ("koşulu oluşmamış iş için boş iş üretilmez"). Tek istisna F1 envanteridir (docs/MODELS.md).

**K-50. Veri borcunun kapatılma biçimi (28.10.2026, Özellik Talimatı A'nın kapısı).**
- **Kurumsal işlemler:** her sıçrama kaynaklı bir kurumsal işlem satırıyla kapatıldı; oranı fiyattan tahmin eden `--apply-suggestions` kullanılmadı.
  - Kaynak tercih sırası: KAP metni (Actions `kap.yml` ile alınır), aracı kurum duyurusu, KAP'ı aktaran haber.
  - KAP metni olmayan satırlarda bu, notta yazılıdır. Fiyat kopukluğuyla tutarlılık ve ikinci kaynak doğrulaması şarttır.
- **Kurumsal işlem olmayan sıçramalar** için yeni `data/candle_exceptions.csv`, iki eylemle:
  - `drop`: ikinci kaynağın gösterdiği bozuk mum atılır. Uydurma bir fiyat konmaz; mum yok sayılır.
  - `real_move`: ikinci kaynağın gösterdiği gerçek hareket (ör. Yahoo'da eksik bir seansın üstünden iki tavan) sıçrama sayılmaz.
  - Kaynaksız satır okunmaz. İkinci kaynağın fiyatı depoya yazılmaz (K-21 aynen).
- **KPOWR rapor evreninden çıkarıldı.** Hiçbir kaynakta yok ve evren listesi zaten "teyit bekliyor" diyordu. Rapor bu hisse için hiçbir zaman veri üretmedi, yani rapor değişmez. K-36 evren kararı Kasım sonunda ayrıca verilecek.
- **KERVT kod değişikliği (BESLR)** üyelik eşlemesine eklendi.
- Bu değişikliklerle karne ve araştırmanın dışarıda bıraktığı hisse listesi boşalmalı. Kalan olursa adıyla yazılır, kapı kapalı kalır.

**K-49. Destek ve direnç seviyeleri: tasarım (yalnız tasarım; 28.10.2026, Özellik Talimatı A §1).** Kod, veri borcu kapısı açılınca yazılır: çözülmemiş sıçramalar, KPOWR ve KERVT. Talimatın andığı "Talimat 1 §2" belgesi depoda yok; kapının içeriği talimattaki parantezden alındı. Aşağıdaki her sabit sonuçlar görülmeden yazıldı ve sonuçlara bakılarak değiştirilmez. Yeni bir değer yeni bir yöntem sayılır.

**Girdi:** düzeltilmiş (kurumsal işlemleri uygulanmış) kapanmış günlük mumlar. Düzeltilmemiş sıçraması olan hisse için seviye hesaplanmaz ("veri sorunu", K-45). Bu yüzden kapı şart. Bakış penceresi 252 seans. ATR = ATR14 (Wilder).

**Yöntemler** (her seviye yöntem adıyla gösterilir):
1. **Salınım tepe/dip (`fraktal`, N = 5).**
   - t günü tepedir, eğer `yüksek[t] > max(yüksek[t−5..t−1])` ve `yüksek[t] ≥ max(yüksek[t+1..t+5])`. Dip simetrik, düşüklerle.
   - Tepe ancak t+5 kapandıktan sonra kesinleşir. O güne kadar hiçbir hesap onu görmez.
   - Kapanıştan kapanışa ±%9,5'i aşan günlerin (tavan/taban) tepe ve dipleri sayılmaz: fiyat orada serbest oluşmadı, kilitlendi.
2. **Kümeleme (`küme`).**
   - Tepe ve dipler fiyata göre sıralanır. Bir öncekine 0,5 ATR'den (hesap günündeki ATR) yakın olan aynı kümeye girer.
   - Seviye fiyatı = kümedeki tepe/diplerin ortalaması.
   - Dokunma sayısı = kümedeki tepe/dip sayısı. Son dokunma = en yeni tepe/dibin tarihi.
   - **Kırılma:** kapanış seviyenin öbür tarafına 0,5 ATR'den fazla geçerse bir kırılma sayılır. Fiyat tekrar geçmeden aynı yönde yeni kırılma sayılmaz.
3. **Klasik pivotlar (`pivot_gün`, `pivot_hafta`).** Önceki günün ve önceki tamamlanmış haftanın yüksek (Y), düşük (D) ve kapanışından (K):
   - P = (Y+D+K)/3
   - R1 = 2P−D, D1 = 2P−Y
   - R2 = P+(Y−D), D2 = P−(Y−D)
4. **Diğerleri:**
   - `52h_zirve`, `52h_dip`: 252 seans, gün içi yüksek/düşük.
   - `psikolojik`: fiyatın büyüklüğüne göre yuvarlak sayı. Adım = 10^⌊log10(fiyat)⌋ / 2: 270 TL'de 50 (250, 300); 27 TL'de 5; 2,7 TL'de 0,5. Yalnız fiyatın iki yanındaki en yakın ikisi.
   - `sma50`, `sma200`.
5. **Hacim yoğunluğu: uygulanmaz** (isteğe bağlıydı). Gün içi veri yok; günlük mumla yapılan "profil" yanıltıcı olur.

**Tür (rol değişimi):** her gün mevcut kapanışa göre belirlenir. Altındaki seviye destek, üstündeki direnç. Kırılan direnç bu yolla kendiliğinden desteğe döner. Kırılma sayısı seviyenin geçmişinde kalır.

**Güç puanı** (yalnız `küme` seviyeleri; diğer yöntemlerin puanı yok, "—"):
- güç = 100 × (1 − e^(−dokunma/2)) × e^(−yaş/252) × 0,5^kırılma
- yaş = son dokunmadan bu yana geçen seans
- Tam sayıya yuvarlanır.

**Uzaklık:** (seviye − kapanış) / ATR ve aynı fark yüzde olarak.

**Gösterim etiketi:** "teknik seviye, öneri değil". "Güçlü destek" gibi bir iddia yok. Anlamlılık ölçümü (§3.3) fark göstermezse her seviyenin yanında "tarihsel olarak rastgele seviyeden ayırt edilemedi" yazar.

**Anlamlılık ölçümü (tanımlayıcı, bütçe dışı):**
- Tarama döneminde (2023-08 – 30.10.2026, holdout yok), kapanış bir `küme` seviyesine 0,25 ATR'den yakın kapandığında bir "yaklaşma" sayılır.
- Sonraki 5 seansta fiyat seviyeden geldiği yöne 1 ATR uzaklaşırsa "dönüş", seviyenin öbür yanına 0,5 ATR geçerse "kırılma", ikisi de olmazsa "belirsiz".
- Aynı hisse ve günde, [52h dip, 52h zirve] aralığında düzgün rastgele seçilmiş aynı sayıda sahte seviyeyle karşılaştırılır (sabit tohum).
- Fark, gün bazlı blok bootstrap ile %95 aralıkla yazılır.

**Canlı kayıt:** her akşam rapordan sonra `logs/levels_log.csv`. Satır: tarih, hisse, yöntem, fiyat, tür, güç, dokunma. Yalnız ekleme. Sonuç bilinmeden yazılır.

**K-48. Temel veri kaynağı: KAP; otomatik çekme kullanım koşulu teyidine kadar kapalı. İş Yatırım'ın robots.txt bulgusu (28.10.2026, profesyonel filtreler Aşama 3).**

Kanıt: sayfalar 28.10.2026'da `sources.yml` ile arşivlendi (`research-results: sources/2026-10-28_18-17-26/`, SHA'larıyla).

**İş Yatırım:**
- `robots.txt` (004, 200) bütün botlara `Disallow: /_layouts/` diyor.
- Mali tablo uç noktasını kullanan topluluk paketleri de (isyatirimhisse, borsa-mcp) bizim ikinci fiyat kaynağımız da (`/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil`) bu yolun altında.
- Kullanım koşulları sayfası bulunamadı (005, 006: 404).
- **Karar:** İş Yatırım temel veri için **seçilmedi**; yeni hiçbir otomatik kullanım eklenmez.
- **Mevcut kullanım (D13):** haftalık ve olay bazlı fiyat çapraz kontrolü düşük hacimli ve yalnız doğrulama amaçlı. Kullanıcının daha önce onayladığı bir güvenlik kontrolü olduğu için kendiliğinden kapatılmadı.
  - Kapatılırsa "veri doğruluğu" SLO'su ölçülemez hale gelir.
  - Karar kullanıcıda: kapat, ya da yazılı izin iste.

**KAP:**
- Yasal olarak kamuya açık bildirimler.
- Her bildirimin yayın zamanı ("Gönderim Tarihi") var: look-ahead önlemi için şart.
- Geçmiş 2018'den derin.
- Borsadan çıkmış şirketlerin bildirimleri de duruyor: survivorship riski düşük.
- TMS 29 (2023 sonu sonrası enflasyon düzeltmeli tablolar) bildirimde işaretli.
- Kullanım koşulları sayfası bu ortamdan bulunamadı (002, 003: 404). `robots.txt` otomatik isteğe "erişim problemi" sayfası döndürdü (001, 666).
- **Karar:** temel veri kaynağı KAP olacak. **Ama toplu otomatik çekme, kullanım koşulları teyit edilene kadar açılmaz.** Bu en güvenli yol.

**Şimdi kurulan:**
- `data/fundamentals.csv` deposu: her kalem yayın tarihiyle; yalnız ekleme; yedekte; şema denetimli; `/durum`'da "Temel veri" satırı.
- Veri girişi ağ kullanmadan, dosyadan içe aktarma ile: KAP'tan elle alınmış ya da lisanslı bir kaynaktan dışa aktarılmış satırlar.
- Karne ve tarama, bir kalemi yalnız yayın tarihinden **sonraki** seanstan itibaren görür.

**Ücretli sağlayıcılar** (Fintables, Matriks, lisanslı KAP dağıtıcıları) kullanıcı kararıdır; BENİM ADIMLARIM'a yazıldı.

**K-47. Teknik profesyonel şablonlar ve alanları (28.10.2026, profesyonel filtreler Aşama 2).** Dört şablon görevde verildiği gibi kodlandı ve sonuçlara bakılarak değiştirilmez: `minervini`, `zirveye_yakin`, `goreli_guc_ust`, `dusuk_oynaklik`. Belirsiz noktalarda seçilen yol:
- **52 hafta zirve/dip:** 252 seans, bugün dahil, gün içi en yüksek/en düşük. Eski `zirve_uzaklik` alanı kapanışla hesaplanıyor ve aynı kaldı.
- **Oranlar:** dil çarpma yazmadığı için "zirvenin %75'i" ve "dibin %30 üstü" `zirve_52h_oran` ve `dip_52h_oran` alanlarıyla yazıldı (kapanış / 52 hafta değeri × 100).
- **`egim(alan,n)`:** alanın n seanstaki yüzde değişimi. "sma200 en az 21 seanstır yükseliyor" görevdeki gibi `egim(sma200,21)>0` olarak yazıldı; 21 seanslık net artış demektir, her gün artış değil.
- **`goreli_guc_yuzdelik`:** `rs_puan`'ın evren içi sırası. `rs_puan` = 0,4×getiri(63) + 0,2×getiri(126) + 0,2×getiri(189) + 0,2×getiri(252), IBD/O'Neil "RS rating" yaklaşımı. IBD'nin tam formülü yayımlanmadığı için bu bir yaklaşımdır ve şablonun kaynağında yazılıdır.
- **6-1 ve 12-1 momentum:** kapanış[t−21] / kapanış[t−126 ya da t−252] − 1.
- **Üst ve alt dilimler:** "en üst %20" = sıra ≥ 80, "en düşük %20" = sıra ≤ 20; sıralar 0–100 yüzdeliktir.
- **Ortak sıra hesabı:** `fields.rank_last` (liste, `/tara_aciklama`) ve `fields.rank_panel` (karne, her gün o günkü üyeler). Eskiden yalnız `gg_sira` için yazılmış üç ayrı kod tek yere toplandı.
- **Etiketler:** her şablonun kaynağında yazar ve yıl, yanında RESEARCH_LOG'daki reddedilmiş türü yazar. Momentum ve 52 hafta zirvesi "Kesitsel momentum", düşük oynaklık "Düşük oynaklık (H1)", Minervini "Tek hissede trend" türündedir. Hiçbiri araştırma programına aday değildir.

**K-46. "Rapor ne zaman gitmeliydi" tek fonksiyon; yavaş makine CI işi (28.10.2026, D11 ve D12).**
- `core.market.calendar.report_due_day(now)` bir seans gününü 18:30 + 1:15 = 19:45'ten itibaren "beklenen" sayar. Yarım günler de dahildir: mum 13:15'te kesinleşir ama rapor yine 18:30'da çalışır. Tatil ve hafta sonu hiçbir şey beklemez.
- Bu fonksiyonu kullananlar: `/durum` rapor ve fiyat kontrolleri, canlı ölçüm denetimi ("kaydı olmayan seans"), SLO penceresi.
- Rapor çalışmasının kendi içindeki kontroller (`daily` içinde "bayat veri" ve tazelik) mumun kesinleştiği saati kullanmaya devam eder, çünkü 18:30'da mum zaten kesindir.
- SLO'nun "zamanında" eşiği (19:00) ayrı bir ölçüttür ve değişmedi.
- **Tolerans:** 1:15 eski değer olarak korundu. Normal günde de 18:00 ile 19:45 arasında alarm yok; 19:45'te gönderim yoksa KRİTİK.
- **Karne sırası:** karnenin mesajı her zaman listeden sonra gider. Hesaplama beklemez, yalnız gönderim bekler. Liste adımı hata verirse olay yine kurulur ve karne asılı kalmaz.
- **Yavaş makine CI işi:** testler tek çekirdekte, aynı çekirdeği meşgul eden bir döngüyle ve tohumlu iki rastgele sırayla çalışır (`QB_SHUFFLE_SEED`, conftest). Yeni paket eklenmedi.
- CI'ın bir işi kırmızıysa güncelleyici o sürümü kurmaz. Yanlış alarmla bir sürüm kaçabilir; bu, kırık bir sürümü kurmaktan daha güvenli.
- Zamana bağlı testler tarandı:
  - `test_runs` eşzamanlı kilit testi `sleep(0.2)` yerine olayla çalışıyor.
  - Hız testi (`test_screen_engine`, < 5 sn) artık duvar saatini değil işlemin CPU süresini ölçüyor. Yerel provada meşgul tek çekirdekte duvar saati 6 sn tuttu; kod yavaşlamadan test kırılıyordu. Ölçüt aynı kaldı, yalnız doğru şey ölçülüyor.

**K-45. Eleme filtreleri: tanımlar ve belirsiz noktalarda seçilen en güvenli yol (28.10.2026, profesyonel filtreler Aşama 1).**
Dört filtre her /tara sonucuna varsayılan olarak uygulanır ve tek tek kapatılabilir. Elenen her hisse nedeniyle yazılır. Belirsiz noktalardaki seçimler:
- **Likidite:** önceki 20 tam seans, bugün hariç (talimat).
  - Eski `likidite=` seçeneği aynı tabanın adı olarak kalır. Varsayılan 10'dan 15 mn TL'ye çıktı.
  - Canlı ölçüm 28.10'da başladı ve 30 olgun örnek yok; eski ve yeni tabanın karışması önemsiz.
  - Sıfır hacimli gün 0 TL sayılır, yani tabanı düşürür. Ayrıca "veri sorunu" eler (D3).
- **Kurumsal işlem:** yalnız kayıtlı işlemler sayılır: `corporate_actions.csv`'de bedelli (`rights`), bedelsiz (`bonus`) ve bölünme (`split`).
  - `factor` satırları veri düzeltmesidir, kurumsal işlem değildir.
  - Kaydı olmayan hisse için durum "bilinmiyor"dur ve elenmez (talimat). KAP'tan otomatik çekip kayıt saymak yok (K-24).
  - Halka arz = ilk mumu fiyat deposunun başlangıcından 5 seanstan fazla sonra olan hisse. Deponun başlangıcından beri işlem gören hissenin halka arz tarihi bilinmez.
- **Aşırı hareket:** tavan/taban, ±%9,5'i aşan kapanıştan kapanışa değişimdir.
  - ATR sırası taranan listenin içindedir. 20'den az hisselik listede bu kural uygulanmaz: izleme listesindeki 3 hissenin en oynağını elemek anlamsız olurdu.
- **Veri sorunu:**
  - Düzeltilmemiş sıçrama penceresi 252 seanstır, çünkü 52 haftalık alanlar sıçramanın iki yanından kurulur (D2). Karne zaten bu hisseleri bütünüyle dışarıda bırakıyor (D1).
  - "Düzeltme onayı bekleyen" için ayrı bir liste yok: fiyat düzeltmeleri kapalı ve onay dosyası boş. Onay bekleyen durum, çözülmemiş sıçrama ve ikinci kaynak farkıyla aynıdır.
- **Karne:** aynı elemeler her gün o günün verisiyle uygulanır (geleceği görme yok; test). Önbellek `CARD_FORMAT=4` ile yenilenir.
- Elemeler hisse seçmez; "güvenilir" ya da "temiz" etiketi yoktur.

**K-44. Görevin beş örnek şablonu eklendi, her şablon reddedilmiş türünü gösteriyor (28.10.2026, /tara Aşama 5).** `trend_takibi`, `asiri_satim`, `kirilim`, `sikisma` ve `goreli_guc` görevde yazıldığı gibi kodlandı.
- Görevdeki "fiyat > ema200" `kapanis>ema200` olarak yazıldı.
- "Son 20 günün en yükseği" bugün hariç alındı (`yuksek_20g`). Bugün dahil edilirse kapanış ondan büyük olamaz.
- "6 ayın en düşük %10'u" 126 seanslık yüzdelik sıradır (`bb_genislik_yuzdelik<10`).

Her şablonun yanında RESEARCH_LOG'daki "Reddedilen fikir türleri" tablosundan türü yazar: "bu tür 27.10.2026'da test edildi, XU100'ü geçmedi". Eşleme:
- **Teknik sinyal:** RSI ve hacim koşulları.
- **Tek hissede trend/kırılım:** EMA dizilimi, kırılım ve sıkışma (dryup_breakout'un akrabası).
- **Kesitsel momentum:** göreli güç sırası.

Test, her türün tabloda adıyla durduğunu denetler. Şablonlar yine aday kural değildir.

**K-43. /tara_sanal: ayrı, ölçüm amaçlı sanal kitap; varsayılan kapalı (28.10.2026, /tara Aşama 4d).**
- Kurallar görevde yazıldığı gibidir ve sonuçlara bakılarak değiştirilmez:
  - eşit ağırlık, en çok 5 pozisyon, 20 seans tutma;
  - stop = giriş − 2 × sinyal günündeki ATR14;
  - sinyal kapanışta, giriş ertesi açılışta, alfabetik sırayla;
  - maliyet her yönde %0,15.
- Kriter açıldığı anda dondurulur. Kayıtlı tarama sonradan değişse de kitap eski kriterle sürer; değişiklik için kapatılıp yeniden açılır ve bu yeni bir başlangıç olur.
- Kitap hiçbir yere yazılmaz. Her `/performans`'ta açılış tarihinden bugüne, yalnız o güne kadarki fiyatlarla yeniden hesaplanır.
- Neden: kişisel `/paper` emirlerine (`data/paper_orders.csv`) ve deftere dokunmamak (test kaynak kodu da denetler), ve fiyat düzeltmesinde kitabın kendiliğinden düzelmesi.
- `data/screen_virtual.csv` yalnız aç/kapat satırlarını tutar: kişisel, yalnız ekleme, yedekte, şeması denetlenir.
- En çok 3 kitap açık olabilir. 30 kapanmış işlemden önce "veri birikiyor" yazılır.
- `/performans`'ta "SANAL, yalnız ölçüm" etiketiyle, kişisel sanal hesaptan ayrı gösterilir.

**K-42. /tara aboneliği raporun arkasından, yalnız değişiklik (28.10.2026, /tara Aşama 4b).**
- `/tara_abone AD` kayıtlı bir taramayı ya da hazır bir şablonu izler. 18:30 raporu gönderildikten hemen sonra çalışır (`daily._screen_subscriptions`).
- Rapor gitmeyen gün (tatil, yeni mum yok, ikinci çalıştırma) abonelik de çalışmaz. Tatil takvimi böylece aynen izlenir.
- Yalnız giren ve çıkan hisseler gönderilir; değişiklik yoksa mesaj yok. İlk çalıştırma listenin tamamını "ilk liste" olarak gönderir. Kriter değişirse liste yeniden başlar. Aynı veri günü ikinci kez çalışmaz.
- En fazla 5 abonelik. Kayıtlı bir tarama silinirse aboneliği de biter.
- `data/screen_subscriptions.csv` kişisel dosya: yalnız ekleme (abone/iptal satırları), yedekte, `/durum` okur ve şemasını denetler, git'e girmez. Son listeler türetilmiş durumdur: `logs/screen_subscriptions_state.json`, mesajlar gittikten sonra yazılır.
- Bir taramanın hatası diğerlerini ve raporu durdurmaz.
- Abonelik çalışmaları canlı ölçüme yazılmaz. Aynı kriter her gün otomatik kaydedilirse `/tara` kayıtlarıyla çift sayılırdı. Ölçüm `/tara` ve sonraki `/tara_sanal` ile yapılır.

**K-41. Kayıtlı taramalar CSV'de kalıyor; silme = boş satır (28.10.2026, /tara Aşama 4).** Görev "data/screens.json" diyordu. JSON'a geçilmedi, çünkü:
- Bir JSON dosyası her kayıtta baştan yazılır. Kişisel kayıtlarda "silme/üzerine yazma yok" kuralı var; mevcut `data/screens.csv` yalnız eklemeli çalışıyor.
- Dosya zaten yedekte, `/durum` sonuna kadar okuyor, şema denetimi var ve güncellemede korunuyor (güncelleyici `data/`'ya dokunmuyor).
- Geçiş olmayınca şema değişikliği de yok: geçiş testi, yedek ve geri dönüş gerekmiyor.

`/tara_sil AD` aynı ada **boş koşullu bir satır** ekler; önceki satırlar değişmez. `load_saved` boş koşullu adı yok sayar. Silinen taramalar 20'lik sınıra sayılmaz; ad yeniden kullanılabilir. Geri dönüş yolu: eski bir sürüm boş koşulu yine okur, yalnız o adı çalıştırınca "koşul yok" der. `/tara_liste` kayıtları listeler.

**K-40. Temel veri: seçenekler (yalnız tasarım, kod yok; 28.10.2026, şablon görevi Aşama D).** Kullanıcının taramalarında piyasa değeri, F/S, gelir artışı, özsermaye kârlılığı, borç/öz kaynak geçiyor. **Uygulama için ayrı karar gerekir.**

Seçenekler:
- **(A) KAP finansal raporları.** Resmi kaynak. Raporlar XBRL tabanlı. Artısı: kapanan ve endeksten çıkan şirketler de var (survivorship riski düşük), her raporun yayım tarihi belli. Eksisi: belgelenmiş açık bir API bulunamadı; KAP'a bu ortamdan erişilemiyor, yalnız GitHub Actions'tan (`kap.py` gibi). XBRL/taksonomi ayrıştırması emek ister. Kullanım koşulları okunmalı.
- **(B) İş Yatırım mali tablo uç noktası.** Topluluk paketleri (isyatirimhisse, borsa-mcp) kullanıyor; tek istekte üç tablo, sanayi (XI_29) ve banka (UFRS) şablonları. Artısı: kolay, çeyreklik, fiyatlarda zaten ikinci kaynağımız. Eksisi: resmi değil, değişebilir, kullanım koşulları belirsiz, geçmiş derinliği ve kapanmış şirketler doğrulanmalı.
- **(C) Yahoo (yfinance).** Piyasa değeri ve beta yalnız bugünün anlık değeri; tablolar birkaç yıl. Geçmiş karnede kullanılırsa geleceği görme riski taşır; en çok canlı filtre için.
- **(D) Ücretli sağlayıcılar** (lisanslı KAP veri dağıtıcıları, Fintables, Matriks vb.). Ödeme gerektirir; BENİM ADIMLARIM'a girer, kullanıcı kararı.
- **(E) Kendimiz hesaplamak.** Beta fiyattan hesaplanıyor, zaten var (`beta`). Piyasa değeri = ödenmiş sermaye (KAP sermaye bildirimleri) × fiyat; sermaye geçmişi KAP'tan kurulabilir.

Her seçenekte zorunlu kurallar:
- **Zamanlama:** bir tablo ancak KAP'taki **yayım tarihinden** sonra bilinir. Dönem sonu tarihi kullanılırsa geleceği görmek olur.
- **Enflasyon muhasebesi:** TMS 29 (2023'ten beri) büyüme oranlarını önceki dönemlerle karşılaştırılamaz kılar. Düzeltilmiş ve düzeltilmemiş tablolar ayrı tutulmalı.
- **Kapsam:** endeksten çıkmış ya da kapanmış şirketler de kapsanmalı.
- **Araştırma kuralları:** holdout (02.11.2026 sonrası) ve araştırma bütçesi temel veri için de aynen geçerli; temel verili bir kural ancak ön kayıtla denenir.

**Öneri (karar değil):** önce (E) ile piyasa değeri. İçinde ödeme ve belirsiz lisans yok, KAP sermaye bildirimleri zaten okunuyor. Tablolar için (A) asıl kaynak, (B) çapraz kontrol. Bu sırayla bir keşif (`kap.yml` gibi bir deneme iş akışı) ayrı bir görev olarak verilirse yapılır.

Kaynaklar: [isyatirimhisse](https://gittrend.io/repo/urazakgul/isyatirimhisse), [borsa-mcp İş Yatırım sağlayıcısı](https://glama.ai/mcp/servers/@saidsurucu/borsa-mcp/blob/728c8332f33398b82fe218e3607af09513a486ed/providers/isyatirim_provider.py), [XBRL.org: Türkiye'nin XBRL tabanlı açıklama sistemi](https://www.xbrl.org/news/turkey-launches-xbrl-based-public-disclosure-system/), [pykap](https://github.com/cemsinano/pykap).

**K-39. Karne: gün ortalaması, 20 seanslık blok, "tüm hisseler" karşılaştırması, maliyet iki türlü (28.10.2026, şablon görevi Aşama C).** (1) Güven aralığı artık gün ortalamasıyla hesaplanıyor: önce her giriş gününün olay ortalaması alınır, sonra bu seri 20 seanslık dairesel bloklarla bootstrap edilir (2000 örnek, sabit tohum). Böylece çok olaylı günler aralığı tek başına belirleyemez. Etiket bu aralığa bakar. Olay ortalaması ve medyan da yazılır. K-35'teki 21 tarihlik olay bloğunun yerini aldı. (2) "Tüm hisseler" satırı: aynı dönem, aynı evren (o günkü BIST 100), aynı likidite tabanı ve aynı maliyetle koşulsuz gün ortalaması; koşulun bundan farkı da yazılır. Kullanıcının keşif testindeki karşılaştırma satırıyla aynı fikir. (3) Olay ortalaması maliyet dahil ve hariç yan yana. Kullanıcının PC sayıları maliyet hariçti; karşılaştırma yapılabilsin diye. (4) Önbellekteki eski biçim karneler yeni alanlar olmadan görünmesin diye veri sürümüne karne biçim numarası (`CARD_FORMAT`) eklendi; biçim değişince karneler yeniden hesaplanır.

**K-38. Hazır şablonlar kodda sabit, kullanıcı kayıtlarından ayrı (28.10.2026, şablon görevi Aşama B).** Altı şablon görevde verildiği gibi yazıldı (`core/screen/templates.py`), sonuçlara bakılarak değiştirilmez. Adlarında övgü sözcüğü yok: dosya adındaki "Şampiyonları" kullanılmadı, "Harekete Hazır EMA" taraması "Düşeni Kıran" ile aynı dizilim olduğundan ayrı şablon olmadı. Kayıtlı bir tarama şablon adını alamaz (`save_text` reddeder). Şablon karneleri bot açılışında ayrı bir iş parçacığında ısıtılır; liste yalnız önbelleği okur (`card.peek`), hiçbir zaman beklemez. Haftalık araştırma bütün şablon karnelerini yazar (gerçek veride karşılaştırma için). Kullanıcının PC'deki keşif sonuçları (maliyet hariç) RESEARCH_LOG'a not olarak yazıldı; şablonlar RESEARCH_PROGRAM'a aday kural olarak girmez (`test_screen_templates` denetler).

**K-37. TradingView adlarıyla alanlar; ema/sma dönemleri sınırlı; 400 karakter (28.10.2026, şablon görevi Aşama A).** Görev `core/analytics/screen.py`'yi anıyordu; motor v0.76.0'dan beri `core/screen/`'de. Aşama A'nın çoğu (kesişim, pencere, aralık, adx, cci, stokastik, 15 koşul) orada zaten vardı; yalnız eksikler eklendi. Yeni alanlar TradingView'daki adlarıyla: `goreli_hacim` (önceki 10 seans; mevcut 20 günlük `hacim_oran` ayrı kalır, ikisi ayrı belgelenir), `momentum10`, `vwma20`, `ortalama_hacim_30g` (adet; `ort_hacim(n)` milyon adet), `likidite` (TL; `likidite=` seçeneği milyon TL), `degisim_1h/1a/3a` (5/21/63 seans), `zirve_1a` (bugün dahil 21 seans; TradingView "Yüksek, 1A"; `yuksek_20g` bugünü dışarıda bırakır). Hepsi kütüphaneyle ya da elle hesaplanmış örnekle birebir eşit (`test_screen_tv_fields`). `ema(n)`/`sma(n)` için n ∈ {5,10,20,40,50,100,200}; dışındaki değerde geçerli değerleri sayan Türkçe hata. Girdi sınırı 400 karakter.

**K-36. /tara'nın varsayılan evreni bugünkü resmi BIST 100 (28.10.2026, PC'deki gerçek veri bulgusu).** Kullanıcının v0.75.0 denemesi gösterdi: çıktı "BIST 100" diyordu ama tarama `data/universe.csv`'yi kullanıyordu. Bu liste 118 hisse (kaynak btcturk-2026-07); 32'si bugün BIST 100'de değil (ör. ADESE, 2022-04-01'de çıktı), bugünkü 14 üye ise listede yok (HALKB, VAKBN, ZOREN…). Karar: (1) `evren=bist100` artık bugünkü resmi üyeliği alır (`bist100_stable.csv` + değişiklikler, karnenin de kaynağı; 100 hisse). Eski liste `evren=quantbist` seçeneğidir ve etiketinde adı ve sayısı yazar. (2) Günlük fiyat güncellemesine bugünkü BIST 100 üyeleri eklendi; aksi halde 14 üye "veri eksik" görünürdü. (3) Günlük raporun, katılım oranının ve canlı ölçümün evreni **şimdilik değişmedi**: ölçüm sürerken evreni değiştirmek ölçümü bozar. Bu ayrı bir karar olarak açık (ROADMAP). (4) ATR uyarıları: son 14 seansta ±%10 limitini aşan bir kapanış hareketi (veri ya da kurumsal işlem) ya da %30'dan büyük bir fiyat değişimi (ATR başka bir fiyat düzeyinde oluşmuş) satırda ⚠️ ile yazılır. ANELE'nin %45'lik ATR'si ikinci durumdur: 19–23.10 beş taban, 26–27.10 iki tavan; iki kaynak birebir aynı (veri doğru, düzeltme yok).

**K-35. /tara Aşama 3: dürüst karne (28.10.2026).**
(1) Giriş ertesi seansın açılışıdır. Maliyet araştırmayla aynıdır: her yönde %0,10 + %0,05, gidiş-dönüş %0,30. Fazla getiri XU100'ün aynı seanslarına göre ölçülür.
(2) Bağımsız olay sayısı: bir hissenin sinyalleri içinde, son sayılandan en az h seans sonra gelen ilk sinyal yeni bir olaydır. Basit ve tekrar üretilebilir bir sayımdır.
(3) Güven aralığı: dairesel blok bootstrap. Bloklar 21 giriş tarihinden oluşur; aynı tarihin olayları birlikte taşınır, çünkü aynı gün aynı piyasayı yaşarlar. 2000 örnek, sabit tohum (aynı kriter her seferinde aynı aralığı verir). Araştırmanın `bootstrap_excess` fonksiyonu günlük seri için yıllıklandırılmıştır; olaylara uymadığı için aynı yöntem burada olaylar için yazıldı.
(4) Etiketler hiçbir zaman "başarılı" demez. Aralık sıfırın üstündeyse bile "çoklu deneme nedeniyle şans olabilir, kanıt değildir" yazar. Tamamen altında olan durum için de bir etiket var ("XU100'ün gerisinde; kanıt değildir").
(5) Deneme sayacı: "bu oturumda N. deneme" (bot açıldığından beri bu sohbette denenen farklı kriter sayısı) ve "bugüne kadar M farklı kriter" (`logs/screen_trials.csv`; yalnız kriter metni, kişisel kayıt değil).
(6) Önbellek anahtarı kriter metni + veri sürümüdür. Veri sürümü, tarama dönemi sonu ile `corporate_actions.csv`, `price_fix_approvals.csv` ve BIST 100 üyelik dosyalarının özetidir. Önbellek bellekte ve `logs/screen_cards.json`'da tutulur.
(7) Bot listeyi karne için en çok 60 saniye bekletir. Karne daha uzun sürerse arka planda tamamlanır ve ayrı mesajla gelir.
(8) Yan bulgu: bot üzerinden giden testler gerçek `data/signal_log.csv` dosyasını oluşturdu; yazma koruması yakaladı. Dosyada yalnız test satırları vardı ve silindi. Artık conftest her testte `signals_log`'u geçici klasöre yönlendiriyor.

**K-34. /tara Aşama 2: kullanıcının kendi taramaları kabul ölçütü; koşul sınırı 15 (28.10.2026).** Kullanıcı dört TradingView taramasının ekran görüntüsünü "bunlar sana ölçüt olsun" diye verdi. Her birinin fiyat tabanlı koşulları `/tara`'da yazılabilir olmalı (`tests/test_screen_user_screens.py`). (1) "Düşeni Kıran" 14 fiyat koşulu içeriyor; paketteki 10 sınırıyla yazılamazdı. Kullanıcının daha yeni talimatı (kendi taraması) esas alındı: sınır 15, karakter sınırı 300 aynen. (2) Eklenen alanlar: `cci(n)`, `vwma(n)`, `mom(n)`, `beta` (252 seans, XU100), `getiri(n)`, `ort_hacim(n)` (milyon adet), `hacim_degisim`, `hacim_oran(n)`. `hacim_oran(20)`, puanın kendi fonksiyonundan gelir (`volume_ratio_series` pencere aldı, varsayılan 20 değişmedi). (3) Sistemde verisi olmayanlar (piyasa değeri, FSO, borsa pazarı) taklit edilmez; HANDBOOK §8 tablosunda yazılır. "HO derecelendirmesi: Güçlü al" bir al/sat etiketidir, eklenmez (CHARTER §9). (4) Sonuç boşsa koşul hunisi gösterilir: her koşul tek başına ve öncekilerle birlikte kaç hisse bırakıyor, en çok eleyen hangisi. TradingView yalnız "filtreleri azaltın" diyor. (5) "Kaydet" düğmesi ad soramadığı için kopyalanacak hazır `/tara_kaydet AD …` satırını verir; kendiliğinden ad uydurulmaz. Son tarama sohbet başına bellekte tutulur (`/tara_devam`, düğmeler); yeniden başlatmada unutulur. Düğmeler yalnız izinli sohbete cevap verir. (6) Mantık değerlendirmesi numpy dizilerinde üç değerli (Kleene) yapılır; eksik veri hiçbir zaman "sağlandı" sayılmaz, "değil" de bunu değiştirmez. Hız testi ölçüm sırasında kapsam izleyicisini durdurur (kapsam izi kodu ~2× yavaşlatır); sınır gerçek hızda 5 saniye.

**K-33. /tara motoru (Aşama 1, 28.10.2026): canlı analizle aynı hesap, kendi ayrıştırıcı, isimle eleme.** (1) `score_frame`'de olan alanlar (ema20, ema50, rsi, macd, hacim_oran, atr_yuzde) doğrudan ondan alınır; diğerleri aynı kütüphaneden (`ta`) gelir. ATR ve ADX için kütüphanenin satır satır `.iloc` döngüsü 5 yıllık veride taramayı 5 saniyenin üstüne çıkarıyordu. Aynı işlemleri aynı sırayla numpy dizisinde yapan sürümler yazıldı; sonuçlar kütüphaneyle bit bit aynıdır (`FastAtrTest`, `FastAdxTest`). `score_frame` de hızlı ATR'yi kullanır; günlük puan değişmez. (2) Ayrıştırıcı özyinelemeli inişle kendi yazıldı; eval/exec yok. İzin verilen karakter kümesi dışındaki her şey konumuyla reddedilir. (3) "Son 20 günün en yükseği" bugünü dışarıda bırakır; aksi halde "kapanış > son 20 günün en yükseği" hiç sağlanamazdı. 52 hafta = 252 seans, kapanışla. (4) "Düzeltme bekleyen" = ikinci kaynakta farkı olan hisse (`crosscheck/latest.json`, saatte bir okunur). Bu hisseler, son kapanışı eski olanlar ve likidite tabanının altındakiler adlarıyla yazılır. (5) Likidite tabanı 20 günlük ortalama işlem hacmidir (milyon TL, varsayılan 10). Taban, `gg_sira` hesaplandıktan sonra uygulanır; sıra taranan bütün listede ölçülür. (6) BIST 30 listesi sistemde yok; kaynaksız liste yazılmaz. `evren=bist30` kaynaklı bir `data/bist30.csv` eklenene kadar açık bir mesaj verir (ROADMAP'te açık iş). (7) Sıralama: `goreli_guc` = 20 seanslık göreli getiri ve `hacim` = hacim oranı büyükten küçüğe; `rsi` küçükten büyüğe. Hiçbiri "en iyi" anlamına gelmez. (8) Kriter metni evreni ve likiditeyi içerir, sıralamayı içermez. Canlı ölçüm kriter metni ve 8 haneli özetiyle kaydedilir.

**K-32. /tara bir filtredir; karnesi geçmişin özetidir, kanıt değildir (28.10.2026, kullanıcı isteği).** Kullanıcı kendi gösterge koşullarıyla BIST 100'ü süzer. Dil: "al/sat/öneri/en iyi" yok; sıralama alfabetik ya da göreli güce göre; her listede "Filtre sonucudur, yatırım önerisi değildir." Karne: aynı koşullar 2023-08-01 – 30.10.2026, o günkü BIST 100 üyeleri, ertesi açılıştan 5/20 seans sonra XU100'e göre fazla getiri; ortalama, isabet, örnek sayısı; 30'dan az örnekte "yetersiz örnek". Holdout iki yerde kapalı: `load_frames` keser, karne de kendi içinde 30.10.2026'da keser (`test_screen.HistoryCardTest`, kesim kaldırılınca test kırmızı). Anlamlılık testi yok ve "başarılı" denmez: koşullar serbestçe denenebildiği için araştırma bütçesi (K-22) dışında kalır; bir koşul araştırılacaksa ön kayıtla bir döngüye girer. Göstergeler teknik puanla aynı pencereler (RSI 14, EMA 20/50, MACD 12/26/9, ATR 14). Eşleşmeler canlı ölçüme "tara" kaynağıyla, kriter metniyle yazılır; aynı hisse aynı gün iki kriterde ayrı sayılır.

**K-31. K-23 sunucu ölçütü koda döküldü; yorum kararları da veri görülmeden (28.10.2026).** Haftalar: 02.11 00:00–09.11 00:00 ve 09.11 00:00–13.11 18:00 (13.11 18:30 raporu kararı taşır). (a) "kaybın çoğu PC'den" = PC kaynaklı boşluklar toplam kesintinin yarısından fazla. PC kaynaklı: aynı bot sürecinin kalp atışları arasındaki boşluk (süreç donmuş: uyku/askı) ya da 20 dakikadan uzun her boşluk (PC kapalıydı; botun kendi yeniden başlatmaları 3×5 dakikada biter). İkinci kısım öz-denetim 4'te eklendi: ilk kodda kapanan PC sayılmıyordu, K-23 metni "kapalı/uykuda" diyor. (b) kaçan rapor PC'den = o gün hiç çalışma yok ya da görev 18:45'ten sonra başlamış (PC kapalıydı); zamanında başlayıp Yahoo/Telegram yüzünden kaçan sayılmaz. (c) Healthchecks okunmaz; 20 dakikadan uzun boşluk "bot DOWN" sayılır (Healthchecks ve `/durum` eşiği). Pencere bitmeden hesap yalnız "ara durum" der, "KARAR" demez.

**K-30. Sapma nedenleri tahminle değil sınamayla yazılır (28.10.2026).** Bir görünümün canlı sonucu geçmiş referansın dışına düşünce `/performans` dört nedeni kendisi sınar. Kural: bir neden, onu çıkarınca referans canlı %95 aralığa geri giriyorsa "neden" sayılır; girmiyorsa "sürüyor" yazılır. Sınananlar: en etkili 3 hisse, en uç gün, piyasa koşulu (aynı süredeki XU100 getirisi, yalnız bilgi), ölçülen hisselerin kurumsal işlemleri. Eşik ve sayı (3 hisse, 1 gün) sonuç görülmeden seçildi; değiştirilmez. Alternatif (Kasım sonunda elle inceleme) sonuca bakıp neden aramak olurdu.

**K-29. Güncelleyici depoya alındı; yalnız CI'ı yeşil commit'i kurar ve her sonucu Telegram'a yazar (28.10.2026).** PC'deki `guncelle.py` dalın son halini indiriyordu (CI'a bakmadan), Telegram'a hiçbir şey yazmıyordu (07:40 görevi sessiz kalırdı) ve depoda olmadığı için yedeksiz, testsizdi (SPOF ⚠️). Artık `scripts/guncelle.py`: GitHub API'den dalın son başarılı CI çalışmasının commit'i alınır; sürüm ve zip **o commit'ten** indirilir (arada gelen commit karışamaz); kurulu sürümden yeni değilse hiçbir şey yapılmaz (geri sürüm kurulmaz). Kırmızı ya da süren CI kurulmaz; daha eski yeşil bir commit kurulu sürümden yeniyse o kurulur. "Yeni sürüm yok" dışındaki her sonuç `bildir.py` ile Telegram'a gider. Kurulum kapıları değişmedi. Testler Windows gerektirmeyen kararları sınar (`test_guncelle`). Eski kopya `C:\Projeler\QuantBIST_otomasyon\guncelle.py` silinmez (kullanıcı dosyası); görev depodaki kopyayı çalıştırır.

**K-28. Hipotez onayı Claude'da; a4 iki hipotezle ön kayıtlı (28.10.2026).** Kullanıcı: "ben onay kısmını sana bırakıyorum". Onay yetkisi kuralları gevşetmez: ön kayıt testten önce commit'lenir ve değiştirilmez, bütçe (döngüde ≤3, 6 ayda bir) ve ileri holdout aynen. a4: H4 eşit ağırlıklı BIST 100, H5 düşük işlem hacmi (likidite primi), %97,5 GA; H5'e ek kapı: iki kat maliyetle de geçmeli. Reddedilen türlerin türevleri ve verisi olmayan fikirler (temel analiz, temettü, bedelsiz olayı: olay listesi eksik) alınmadı. Bütçe gereği tarama 27.04.2027'den önce çalışmaz; kod tarih kapısıyla zorlar. Üçüncü hak kullanılmadı: az hipotez, küçük Bonferroni cezası.

**K-27. Yeni sürüm her sabah 07:40'ta kendiliğinden kurulur ("QuantBIST Guncelle" görevi, 28.10.2026).** 28.10'da elle çalıştırılan `guncelle.py` PC'nin v0.59.0'da kaldığını gösterdi: v0.60–v0.65 hiç kurulmamıştı, çünkü güncelleme için zamanlanmış görev yoktu (yalnız bot ve rapor görevleri vardı). 07:40 seçildi: seans öncesi, 18:30 raporuyla çakışmaz, bir sorun akşamdan önce görülür. `-StartWhenAvailable` ile PC kapalıysa açılınca çalışır. Kurulum kapıları (yedek, deneme kopyasında ruff+pytest, bot ayakta değilse eski sürüme dönüş) aynen geçerli; paket kilidi değişirse durur ve sorar. S3'ün "30 gün müdahalesiz" sayacı bu görevle 28.10'dan başlar.

**K-26. Kapanış alarmı yalnız akşam raporunda, gün sonu fiyatıyla (28.10.2026).** Gün içi fiyat için sürekli çalışan bir izleyici ve canlı veri gerekir; Yahoo gecikmeli ve sistem gün sonu verisine kurulu. Alarm, o seansın işlem gördüğü (düzeltilmemiş) kapanışla karşılaştırılır; kullanıcının ekranda gördüğü fiyat budur. Dosya (`data/price_alarms.csv`) defter gibi yalnız ekleme: kurma, silme ve tetiklenme yeni satır; bir alarmın son satırı durumunu belirler. Tetiklenme rapor Telegram'a gittikten **sonra** yazılır: gönderim başarısızsa alarm kaybolmaz, ertesi akşam yine söylenir. Alarm kurulan hisse evren dışındaysa da fiyatı güncellenir. Bir kez bildirilir, sonra kapanır; tekrar isteyen yeniden kurar. Alarm satırı "al/sat önerisi değildir" der.

**K-25. Cuma grafiği metin olarak (▁▂▃▅▇), resim değil (28.10.2026).** Kurulu tek grafik paketi plotly; PNG için ek paket (kaleido) gerekir, Telegram'a fotoğraf göndermek de ayrı bir yol ister. Metin grafiği aynı mesajda gider, bağımlılık ve güvenlik taraması yükü getirmez, testlenir. Her çizgi kendi aralığına ölçeklenir; büyüklüğü yanındaki yüzde söyler. Gerçek grafik gerekirse web paneli (README) ile yapılır.

**K-24. KAP takibi: duyuru gelir, hiçbir şey kendiliğinden uygulanmaz (27.10.2026).** KAP'ın resmî API'si yok; sitenin kendi kullandığı uç noktalar (`disclosure/members/byCriteria`) GitHub'dan çalışıyor (deneme, research-results `kap/probe_*`). Konu filtresi şirket konularını vermediği için bütün özel durum açıklamaları alınıp konu adıyla süzülür: "Sermaye Artırımı - Azaltımı…" (bedelsiz/bedelli/bölünme) ve "Kar Payı Dağıtım…" (temettü). Sermaye işlemi, hissenin `corporate_actions.csv`'de duyurudan 30 gün önce ile 180 gün sonra arasında bir satırı yoksa "kayıtta yok, KAP'ta doğrula" diye listelenir; temettü yalnız bilgi (fiyatı Yahoo düzeltir). Satırı yine bir insan, kaynağıyla ekler: oran ve hak kullanım günü duyurunun metninden okunmalı, otomatik çıkarmak hatalı düzeltme riski taşır (bütünlük). KAP biçimi değişirse `--probe` ham cevabı gösterir.

**K-23. Sunucu kararının ölçütü, veri görülmeden önce (27.10.2026).** Ölçüm penceresi 02.11–13.11 (iki tam hafta); karar 14.11 dönem değerlendirmesinde. **Sunucu önerilir** (kiralama BENİM ADIMLARIM'a) eğer iki haftanın herhangi birinde: (a) "Bot ayakta kalma" < %98 ve kaybın çoğu PC'nin kapalı/uykuda olmasından (heartbeats.csv'deki uyku/askı saatleri), ya da (b) "Rapor teslimi" < %99 ve kaçan rapor PC'den (Yahoo/Telegram değil), ya da (c) haftada ≥ 1 Healthchecks bot DOWN alarmı PC'den. **Aksi halde PC'de kalınır**, aylık yeniden bakılır. Ücretsiz seçenek de yazılır: PC'nin 7/24 açık ve uykusuz kalması (kullanıcı kararı). Hedefler (CHARTER: bot %98, rapor %99) PC'ye uysun diye **gevşetilmez**; Yahoo ya da Telegram kaynaklı kayıplar sunucuyla düzelmeyeceği için sayılmaz. Gerekçe: bot hedefi 7/24 ölçülüyor; gece uyuyan bir PC'de S2'nin "4 hafta SLO" maddesi kapanamaz.

**K-22. Araştırma programı: holdout ileri veridir (02.11.2026'dan), bütçe döngüde 3 hipotez, 6 ayda bir döngü.** 2022–27.10.2026 verisinin tamamı 13 kuralın testinde görüldü; ondan sonradan bir parça "ayrılmış" saymak dürüst olmaz. Holdout'a giren kural en az 250 seans ileri veriyle karara bağlanır; o tarihten önce holdout sonucu hesaplanmaz. Alternatif (geçmişin son 12 ayını holdout saymak) görülmüş veriyi tekrar kullanmak olurdu. Yeni hipotezler kullanıcı onayı ister (Aşama 3 kuralı aynen). Ayrıntı [RESEARCH_PROGRAM](RESEARCH_PROGRAM.md).

**K-21. Yahoo'suz günde ikinci kaynak yalnız bilgi verir, fiyat deposuna yazılmaz.** İş Yatırım açılış fiyatı ve adet hacmi vermiyor; sanal emirler açılıştan dolar (`core/ledger/paper.py`), canlı ölçüm girişi açılıştan alır (`core/reports/forward.py`). Depoya yazmak bunları uydurma açılışla bozardı (bütünlük). Bunun yerine Yahoo o seansı vermediğinde rapor gönderilmez (eskisi gibi), ama sessiz kalınmaz: bir kez kısa mesajla XU100 ve eldeki hisselerin İş Yatırım kapanışları, "yalnız bilgi" etiketiyle. Yahoo dönünce depo 10 günlük örtüşmeyle kendini tamamlıyor. Gün yine "stale" sayılır; Rapor teslimi SLO'su güzelleşmez.

**K-20. Elle/aylık geri yükleme testi de Yedek SLO'suna sayılır.** 3. tatbikatın `/durum` çıktısı, hemen önce başarılı `--test-restore` çalıştığı hâlde "geri yükleme testi henüz kaydedilmedi" diyordu: komut satırı sonucu `restore_tests.csv`'ye yazmıyordu. Artık başarılı ve başarısız sonuç yazılır ("elle" notuyla). Alternatif (yalnız günlük rapordaki haftalık test) yerel otomasyonun aylık testini ve başarısızlıkları görünmez bırakıyordu. İstisna: `pull_backups` sunucudan çekilen kopyaları denetler, bu makinenin yedek zincirini değil; `--no-record` ile sayılmaz (ilk denemede testin alt süreci gerçek `logs/`a yazdı, yazma koruması yakaladı).

**K-19. Kullanıcı kararları devretti ("kontroller sende, ben uygulayıcıyım").** Sorumu sormadan karar verip buraya yazıyorum. Sınırlar değişmedi: hesap, token, ödeme, .env ve sunucu kiralama BENİM ADIMLARIM'da; gerçek para, aracı kurum ve al/sat önerisi asla. Depodaki `fix/windows-dr-setup-and-test-clock` dalına dokunmuyorum: içeriği bu dalda (v0.56.0–v0.56.2) zaten var ve kuralım yalnız kendi dalıma yazmak. Silinmesi zararsız ama gerekmiyor.

**K-18. S1 ÇALIŞIR kanıtla kapatıldı; S2'nin ilk işi Windows'ta felaket kurtarma tatbikatı.** Kanıtlar MATURITY.md'de (PC /durum gözlemleri, testler, CI #130/#131). S2 eksiklerinin puanı (etki×olasılık÷maliyet, bütünlük ×2): felaket kurtarma tatbikatı (kişisel kayıt bütünlüğü, ×2; şimdi yapılabilir; maliyet orta) en yüksek; izleme tatbikatı kullanıcının adreslerini bekliyor; 4 hafta SLO ve temiz öz-denetim zamana bağlı. Tatbikat GitHub'ın temiz Windows makinesinde, yapay kayıtlarla, aylık ve elle (`dr-drill.yml`); gerçek veri ve token kullanılmaz.

**K-17. Dönem = takvim haftası; değerlendirme cumartesi araştırmasından sonra.** Döngü talimatı "koşulu oluşmuş iş kalmayınca dönem değerlendirmesi" diyor. Bir günlük dönemin SLO tablosu anlamsız olur (kayıtlar yeni başladı). İlk değerlendirme 31.10 araştırması bittikten sonra `docs/PERIODS/2026-10-31.md`'ye yazılır. O güne kadar koşulu oluşmuş iş yoksa döngü saatlik aralıklarla yalnız CI'ı ve gözlemleri kontrol eder.

**K-16. Araştırma verisini 2015'e uzatma işi engelli (açık).** Geçmiş BIST 100 üyeliği için kaynaklı, eksiksiz bir liste bulunamadı: Borsa İstanbul duyuru sayfaları numarayla açılmıyor (başlıksız adresler 404; 27.10 sources çalışmaları), 2015 sonrası bileşen dosyaları yalnız ücretli DataStore'da, haber sitelerindeki tablolar çoğunlukla görsel. Kaynaksız ya da tahmine dayalı üyelik satırı eklenmez (survivorship hatası araştırmayı geçersiz kılar). Yeniden açılma koşulu: duyuruların başlıklı adresleri ya da resmî bir bileşen arşivi bulunursa; ücretli DataStore yalnız kullanıcı kararıyla (BENİM ADIMLARIM). Sonuç: G aşamasında şu an koşulu oluşmuş iş yok; mevcut 2022+ veriyle ön kayıtlı üç hipotez zaten reddedildi ve yeni hipotez için istatistiksel güç düşük.

**K-15. SLO'lar kaydın başladığı günden itibaren ölçülür.** PC'deki ilk tablo (27.10 16:19) "Rapor teslimi %25" ve "Yedek %25" gösterdi: 21-23.10 "eksik" sayılmıştı, oysa runs.csv ve tarihli yedekler o günlerde henüz tutulmuyordu. Ölçülmemiş gün başarısızlık değildir; artık her hedef (rapor, tazelik, yedek) kendi ilk kaydından başlar ve metinde "ölçüm GG.AA'da başladı" yazar. Geri yükleme testi sonucu hiç kaydedilmemişse (kayıt v0.51.0'da başladı) "bilinmiyor"; kayıt varken son 7 günde test yoksa "uyarı".

**K-14. Test kapsamı kapısı %91, yalnız yukarı gider.** 27.10'da core+bot kapsamı %91,09 ölçüldü. CHARTER "≥ %90 ve hiçbir sürümde düşmez" diyor; kapı mevcut değerin tabanına (%91) kondu, böylece kapsamı düşüren sürüm CI'da kırmızı olur. Kapsam yalnız CI'da ölçülür (pytest-cov iş akışında kurulur; proje bağımlılığı değil). Kalite SLO'su PC'de GitHub'daki son CI sonucunu okur: yeşil = testler, ruff ve kapsam kapısı geçti. Kapı yükseltilirse `slo.COVERAGE_GATE` ve `ci.yml` birlikte değişir; bir test ikisinin aynı olduğunu denetler.

**K-13. Paket güvenlik taraması yalnız GitHub'da, pip-audit ile.** `security.yml` her pazartesi kilit dosyasındaki paketleri herkese açık açık-veritabanlarına (PyPI/OSV) karşı tarar; bulgu olursa çalışma kırmızı olur ve düzeltme, test edilmiş bir kilit dosyası yükseltmesi olarak yayınlanır. pip-audit projeye bağımlılık olarak eklenmedi (CHARTER I3: gerekçesiz bağımlılık yok); PC'deki kurulum değişmez. 27.10'da yerel tarama: bilinen açık yok. Gizli bilgi denetimi ise bir test (`test_repo_secrets`): CI'da her push'ta git'te izlenen dosyalarda `.env`, kişisel kayıt, fiyat deposu, Telegram token biçimi ya da Healthchecks adresi arar; git olmayan kopyada atlanır.

**K-12. "Veri doğruluğu" SLO'su GitHub'daki haftalık özetten okunur.** İkinci kaynak (İş Yatırım) kontrolü PC'de değil, haftalık araştırmada çalışıyor. Bu yüzden /durum, herkese açık `research-results` dalındaki `crosscheck/latest.json`'u okur. İnternet yoksa ya da özet 8 günden eskiyse sonuç "bilinmiyor" olur. Şüpheli hisseler araştırmadan otomatik dışlanmaz; dışlama ayrı bir seçenek (`--exclude-suspects`). Dışlamak da bir karardır ve deneme sayısına girer; sonuca bakıp hisse çıkarmak veri gözetlemesi olurdu.

**K-11. SLO'lar yerel kayıtlardan ölçülür; ölçülemeyen "bilinmiyor".** Kaynaklar: rapor teslimi `runs.csv` (19:00'dan sonra biten gönderim "geç"); bot ayakta kalma yeni `logs/heartbeats.csv` (5 dakikada bir satır; aynı süreçte iki sinyal arasındaki boşluk "uyku/askı", süreç numarası değişirse "yeniden başlama"; en az 1 günlük kayıt yoksa bilinmiyor); veri tazeliği yeni `logs/freshness.csv` (raporun fiyat güncellemesinden hemen sonra, beklenen seansın kapanışına sahip hisse oranı ve XU100); yedek: o günün tarihli yedeği + son 7 günde başarılı geri yükleme testi (yeni `logs/restore_tests.csv`); kayıt bütünlüğü: signal_log denetimi + kişisel dosya kontrolü. Veri doğruluğu (C1) ve kalite (I) bu bilgisayardan ölçülemediği için şimdilik bilinmiyor. SLO'lar /durum'daki genel hükmü değiştirmez (o, bileşenlerin şu anki durumu); hedef tutmazsa CHARTER §4 gereği önce o düzeltilir. Bu dosyalar kişisel kayıt değildir; adres ya da kişisel veri içermez.

**K-10. Rapor diske yazamazsa da gider.** Disk dolunca (ENOSPC) kayıt yazılmaz, raporda "… yazılamadı: disk dolu" notu çıkar, gönderim yapılır (Telegram'a göndermek diske yazmayı gerektirmez). Kişisel dosyalara hiçbir şey yarım yazılmaz: yazma önce geçici dosyaya yapılır, sonra adı değiştirilir.

**K-9. "Gelecekten" kalan rapor kilidi geçersiz sayılır.** Saat 5 dakikadan fazla geri alındıysa kilit dosyasının zamanı ileride görünür. Önceki kural yalnız 1 saatten eski kilidi kaldırıyordu; saat geri gidince her çalıştırma "başka bir çalıştırma var" diye duracaktı.

**K-8. CHARTER, sürekli yol haritasının yerini aldı.** Aşama harfleri değişti (ör. araştırma artık G, bakım J). DECISIONS'taki önceki kararlar geçerli. K-6'daki "veriyi 2015'e uzatma" G'ye (araştırma) aittir ve G'nin koşulu oluşunca sürer.

**K-7. İzleme kurulmamışsa /durum'da "BİLGİ" görünür, uyarı değil.** Kurulum kullanıcının adımı (hesap ve .env). UYARI olsaydı /durum hep "UYARI" der, 20:00 kontrolü her 3 günde bir mesaj atardı; asıl sorunlar bu gürültüde kaybolurdu. Bir adres eksikse, sinyal ulaşmıyorsa ya da bot sinyali 20 dakikadan eskiyse UYARI. Sinyal sonucu `logs/monitoring.json`'a adres olmadan yazılır.

**K-6. Aşama E'deki "veriyi 2015'e uzatma" işi durduruldu.** Kullanıcı aynı gün bu yönü seçmişti; ardından gelen sürekli yol haritası araştırmayı (E) dayanıklılık ve izleme işleri bittikten sonraya koydu. Yapılan: kaynak sayfa arşivi iş akışı (`sources.yml`) ve ilk kaynak indirmesi; ikisi de durur, iş E sırasında kaldığı yerden sürer. Gerekçe: yol haritası tek kaynak.

**K-5. Dosya kilitliyken (Excel) rapor durmaz.** Kilitli dosyaya yazılmaz, raporun "Veri notları"nda adı geçer, sonraki çalışma yazar. Sanal emir doldurma zaten idempotent (defterdeki "sanal emir #N" etiketi), bu yüzden yarıda kalan dolum ikinci kez yazılmaz. Alternatif (raporu tamamen durdurmak) günün raporunu ve canlı ölçüm satırını kaybettiriyordu.

**K-4. Yarım kalan son satırdan sonra ekleme yeni satırdan başlar.** Ekleme yapan dört yer (defter, uyarı kaydı, sinyal kaydı, runs.csv) dosya satır sonuyla bitmiyorsa önce `\n` yazar. Mevcut baytlar değişmez (kişisel kayıt kuralı). Yarım satır olduğu gibi kalır ve okuma sırasında satır numarasıyla bildirilir. Gerekçe: aksi halde sağlam yeni kayıt yarım satıra yapışıp kayboluyordu; runs.csv'de bu, raporun ikinci kez gönderilmesi demekti.

**K-3. Rapor, hiç fiyat inmezse 1 + 2 + 4 dakika bekler.** Yalnız bütün semboller başarısızsa (ağ yok) beklenir; tek sembolün başarısızlığı ağ sorunu sayılmaz. Toplam 7 dakika, Windows görevinin 30 dakikalık sınırının içinde kalır.

**K-2. Botun günlük işleri 4 saate kadar geç başlayabilir.** python-telegram-bot varsayılanı 1 saniye; PC 20:00'de uykudaysa kontrol sessizce atlanıyordu. 4 saat: 20:00 kontrolü gece yarısına kadar telafi edilir; ertesi günün işine karışmaz. `coalesce=True` ile kaçan çalıştırmalar tek bir çalıştırmaya iner.

**K-1. Açılışta ağ hatası 20 kez denenir, sonsuz değil.** python-telegram-bot sonsuz denemeyi önermiyor. 20 deneme, artan aralıklarla yaklaşık 7 dakika eder. Sonrasında bot kapanır ve "QuantBIST Bot" görevi 5 dakika arayla 3 kez yeniden başlatır; toplam yaklaşık 20 dakikalık bir pencere. Yanlış token denenmez.

**K-0 (daha önce, v0.48.1). Fiyat düzeltme kapısında veritabanı SHA kontrolü alınmadı.** Fiyat deposu her gün değiştiği için ilk güncellemede her şeyi reddederdi. Onay listesinin bütünlüğünü git geçmişi sağlar.
