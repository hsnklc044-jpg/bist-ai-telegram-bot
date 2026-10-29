# Kararlar

Sürekli yol haritası (ROADMAP) gereği Claude'un verdiği teknik kararlar, tarihli ve gerekçeli. En yenisi en üstte.

## 27.10.2026

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
- **Kur önbelleği:** `data/macro/usdtry.csv` yerel ve git dışındadır. Akşam raporu son 14 günden eksik bültenleri ister (en çok 10 istek). Bülteni olmayan gün (tatil, yarım gün; 404) hatırlanır, ağ hatası hatırlanmaz.
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
