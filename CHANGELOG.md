# Sürüm geçmişi

Sade dille: ne değişti, nasıl doğrulandı. Her sürüm CI'da (ruff, tüm testler, v0.54.1'den beri kapsam ≥ %91) geçti; aksi yazılıysa o sürüm kırmızıydı ve bir sonraki düzeltti. Daha eski sürümler: `git log`.

## v0.99.88 – 05.11.2026 (yol planı 2. bölüm tamam: temettü ve şirket olayları takvimi)
- **Yeni `/takvim`:**
  - Varsayılan görünüm: portföydeki ve izleme listesindeki hisselerin önümüzdeki 30 gündeki kayıtları.
  - `/takvim hepsi`: gelecekteki bütün kayıtlar.
  - `/takvim ekle THYAO 05.12.2026 temettü 3,25 TL brüt` kayıt ekler, `/takvim sil 3` bir kaydı siler.
- KAP'a otomatik erişim yok (K-48); kayıtları kullanıcı elle girer. Dosya `data/events.csv` yalnız ekleme yapılarak tutuluyor: silme de yeni bir satır, hiçbir satırın üzerine yazılmıyor. Dosya kişisel kayıt sayılıyor: yedeğe giriyor, depoya girmiyor (`.gitignore`, gizli dosya testi).
- Haftalık `/saglik` raporu, portföydeki hisselerin yaklaşan takvim kayıtlarını da listeliyor.
- Temel analiz kartı zaten vardı: `/temel` (K-57) posta kutusu verisiyle çalışıyor ve yalnız yayımlandıktan sonraki gün bilinen değerleri kullanıyor. Yol planında tamamlandı olarak işaretlendi.
- Doğrulama: yeni `test_events` (6 test). Yazılırken bir test yalıtım hatası bulundu: kişisel dosya yolu `paths` modülünde yamalanınca, yedek listesi bir testte ilk kez yüklenirse geçici yolu alıyordu. Yama artık yalnız `events` modülünde.

## v0.99.87 – 05.11.2026 (yol planı 2. bölüm: yeniden dengeleme yardımcısı ve stres testinde kur şoku)
- **Yeni `/denge THYAO=30 ASELS=20 [bant=5] [sanal]`:** Her hissenin kullanıcının kendi hedef ağırlığından sapmasını ve hedefe dönmek için gereken en az işlemi tam adet olarak hesaplıyor. Kurallar:
  - bant içindeki sapmaya dokunulmuyor (varsayılan ±5 puan);
  - hedefi yazılmamış hisse olduğu gibi kalıyor;
  - adet sıfıra doğru yuvarlanıyor, böylece hedef aşılmıyor;
  - satış eldeki adedi geçmiyor.
  Nakit etkisi ve tahmini maliyet (işlem başına %0,15) de yazıyor. Hesap sonucudur; öneri değil, emir verilmez. Geçersiz hisse kodu çökme yerine açıklamayla reddediliyor.
- **`/stres` kur şoku bölümü:** TCMB kurlarının kayıtlı geçmişindeki en büyük dolar/TL sıçramaları veriden bulunuyor (1, 5 ve 20 gün). Her pozisyonun aynı günlerdeki TL ve dolar bazındaki değişimi gösteriliyor. Kur dosyası yoksa bunu söylüyor.
- `/start` yardım metnine, komut menüsüne ve HANDBOOK'a `/saglik` ile `/denge` eklendi.
- Doğrulama: yeni `test_rebalance` (9 test) ve `test_stress_fx` (4 test). Yazılırken iki gerçek hata yakalandı: kayan nokta yüzünden 19,999… adet 19'a kesiliyordu; geçersiz kod çöküyordu.

## v0.99.86 – 05.11.2026 (yol planı 2. bölüm, ilk iş: haftalık portföy sağlık raporu)
- Yeni `/saglik` komutu. Bot raporu ayrıca her cumartesi saat 10:00'da kendiliğinden gönderiyor. İçeriği:
  - **Dağılım:** her hissenin ağırlığı.
  - **Yoğunlaşma:** en büyük pozisyon ve etkin pozisyon sayısı (1/Σw²). Dört eşit hisse 4 eder; bir büyük ve üç küçük hisse 1'e yakın.
  - **Birlikte hareket:** son 60 seansta hisseler arası ortalama korelasyon.
  - **Getiri:** son 4 hafta ve ilk kayıttan beri. Para giriş çıkışı ayıklanıyor; komisyon sonrası, vergi hariç. Nominal, reel (TÜİK TÜFE), dolar bazında (TCMB kuru) ve BIST 100 ile farkı.
- Ölçülemeyen bir değer tahminle doldurulmuyor; nedeniyle "ölçülemedi" yazıyor (K-70). Örnekler: dönemi kapsayan TÜFE ayı henüz yayımlanmamışsa ya da iki günlük değer kaydı yoksa.
- Öneri vermiyor; yalnız ölçüm. Sanal hesap da ayrı bir bölüm olarak raporlanıyor.
- Ayrıca: v0.99.78'in bilgisayarda kurulmamasının nedeni burada yeniden üretilemedi. Git'siz bir deneme kopyası ve uyarı bayrakları olmadan 1303 test geçti. Neden bilgisayara özgü ve henüz bilinmiyor.
- Doğrulama: yeni `test_portfolio_health` (11 test). Kapsadıkları: elle hesaplanmış ağırlık ve etkin sayı; aynı ve bağımsız hareket eden hisselerde korelasyon; para girişinin getiri sayılmaması; dolar ve BIST 100 farkı; TÜFE yokken "ölçülemedi"; komut ve cumartesi işi.

## v0.99.85 – 05.11.2026 (M30 yeniden doğrulaması ve bulguların düzeltilmesi)
- Faz C sonrası M30 (ML filtresi) bağımsız olarak yeniden doğrulandı. Karar: **kullanılamaz**. Model kapalı ve kapalı kalıyor. Önceki 10 bulgudan 7'si tamamen giderilmiş bulundu. Rapor `docs/validation/M30.md`'de; inceleyicinin metni değiştirilmedi, sonuna geliştirici eki kondu.
- **YÜKSEK:** Canlı ML modeli, ölçümün dışladığı 2022 öncesi veriyle (yalnız bugün hayatta kalan hisseler) eğitiliyordu. Artık ölçümle aynı veriyle eğitiliyor: 01.04.2022'den başlıyor ve holdout'u görmüyor.
- **ORTA:** Aralığın blok uzunluğu 20 seans oldu; /tara karnesindeki kuralla aynı. 10 seanslık blokla kapsama %87–88'de kalıyordu. Uzun rejim bağımlılığı bir yöntem sınırı olarak kayda geçti.
- **DÜŞÜK:**
  - ML filtresi yalnız "BIST 30" evreninin raporuyla açılabiliyor; "BIST 300" gibi bir ad artık geçmiyor.
  - `goreli20` etiketinde tabanda kilitli çıkış ilk kilitsiz açılıştan.
  - HANDBOOK altı koşulu yazıyor.
- Doğrulama: `test_faz_c_m30` içinde 4 yeni test, önce kırmızı sonra yeşil. Eski canlı model testinin sentetik verisi 2022 sonrasına taşındı.

## v0.99.84 – 05.11.2026 (güncelleyici başarısız testin adını yazıyor)
- 05.11 08:26: v0.99.78 bilgisayardaki deneme kopyasında "1 failed" ile kurulmadı. CI'ın dört işi (Windows dahil) yeşildi. Deneme kopyası bilgisayarın gerçek `data` klasörüyle çalıştığı için fark oradan gelebilir; neden henüz bilinmiyor.
- Telegram mesajı artık başarısız testlerin adını da yazıyor (en çok 3 tane, fazlası sayıyla).
- Bu düzeltme ancak bir sürüm kurulduktan sonra çalışır. O zamana kadar ayrıntı `C:\Projeler\QuantBIST_otomasyon\logs\guncelle_*.log` dosyasında.
- Doğrulama: `test_guncelle` (FailedTestNamesTest, 3 test), önce kırmızı sonra yeşil.

## v0.99.83 – 05.11.2026 (Faz C, 5. parti: teknik görünüm skorunun çevresi, M1; Faz C'nin temiz maddeleri tamam)
- Skorun kendisi değişmedi. M1-4 bilerek bırakıldı, çünkü skoru değiştirmek canlı ölçümü sıfırlar.
- **M1-3:** `/analyze`, son 60 seansta tavan/taban sınırını aşan bir kapanış değişimi görürse kaydı eksik bir şirket işlemine karşı uyarıyor. Böyle bir durumda görünüm, hacim ve oynaklık yanıltıcı olabilir.
- **M1-5:** Günlük skor kaydı, `/analyze` ile aynı 60 mumluk alt sınırı uyguluyor. Önceden 50–59 mumlu hissede kayıt "güçlü negatif" yazarken `/analyze` "analiz yapılamadı" diyordu.
- **M1-8:** `/performans`, canlı ve referans ortalamaların maliyet öncesi olduğunu yazıyor.
- **M1-9:** `/analyze`'daki trend satırı, skordan ayrı bir tanım (EMA20/50/200) kullandığını söylüyor.
- **Faz C durumu:** İleri testi etkilemeyen bütün maddeler v0.99.79–83'te kapandı. K-64 değerlendirme kodunu değiştiren maddeler 03.02.2027 ileri testinden sonraya kaldı: M31-2 (etiket = kartın işlemi), M31-3 (kalibrasyon), M31-8 (K-64 test etiketi), M31-10/12 ve M31 yeniden doğrulamasının D3, D4, D6, D7 maddeleri.
- Doğrulama: yeni `test_faz_c_m1` (5 test), önce kırmızı sonra yeşil.

## v0.99.82 – 05.11.2026 (Faz C, 4. parti: sanal defterde aynı kural, seviyelerde K-49'a uyum; M32-3, M8)
- **M32-3:** Saatlik takip artık günlük kuralı uyguluyor. Bir günün zirvesi iz süren stopu ancak ertesi seanstan itibaren yükseltiyor; saatlik ve günlük yol aynı sonucu veriyor. Önceden gün içindeki zirve stopu aynı gün yükseltiyordu; saatlik yol, ölçülen kuraldan daha sık ve daha erken stop yazıyordu. Günlük çerçevede sonuç birebir aynı.
- **M8-3:** Bir seviye kümesinin fiyat aralığı küme genişliğini (0,5 ATR) aşamıyor. Önceden zincirleme birleşme vardı: 0,45 arayla dizilmiş 10 tepe 4 fiyat birimine yayılan tek bir seviye oluyor, dokunma sayısı ve güç puanı şişiyordu.
- **M8-6:** Pivot olarak yalnız kilitli gün (bütün gün tek fiyat ve limit kadar hareket) dışlanıyor; K-49'un yazdığı kural bu. Önceden gün içinde işlem görmüş her %9,5'lik hareket de dışlanıyordu.
- **M8-5:** Son 252 seansta tavan/taban sınırını aşan bir kapanış değişimi varsa `/seviye` metni kaydı eksik bir şirket işlemine karşı uyarıyor.
- K-49 sabitleri değişmedi. Seviye ölçümü yeniden çalıştırılmadı; kararı ("rastgele seviyeden ayırt edilemedi") aynı.
- Doğrulama: yeni `test_faz_c_m32` (2 test) ve `test_faz_c_m8` (7 test), önce kırmızı sonra yeşil. Davranışı bilerek değişen iki eski seviye testi güncellendi.

## v0.99.81 – 05.11.2026 (Faz C, 3. parti: senaryo karnesi, M27)
- **M27-4:** Karnenin %95 aralığı artık gösterilen ortalamanın aralığı. Olaylar eşit ağırlıklı; tam günler bloklar halinde yeniden örnekleniyor. Önceden aralık gün ortalamalarından hesaplanıyordu. Kalabalık günlerde ortalama aralığın dışında kalabiliyordu; testte ortalama −0,24 iken aralık 0,85'ten başlıyordu.
- **M27-8:** Tam 20 seanslık ufku dönem içinde olmayan sinyaller sayılmıyor. Önceden son 20 seansta yalnız erken biten olaylar giriyordu; bu, sonucu bir yöne kaydırıyordu.
- Doğrulama: yeni `test_faz_c_m27` (3 test), önce kırmızı sonra yeşil. Senaryo testleri geçti.

## v0.99.80 – 05.11.2026 (Faz C, 2. parti: /tara geçmiş karnesinin yöntemi, M5)
- **M5-2:** Karnenin hisse evreni (en az 300 mum ve çözülmemiş sıçrama denetimi) yalnız holdout öncesi veriyle seçiliyor. 02.11 sonrası bir sıçrama, 2023–2026 karnesinden hisseyi düşürmüyor. Araştırmanın varsayılan yolu değişmedi.
- **M5-5:** Verisi dönem bitmeden kesilen bir hissenin (kotasyondan çıkış) son olayları kaybolmuyor; son kapanıştan çıkılmış sayılıyor. Önceden −%40'lık bir düşüş karneye hiç girmiyordu.
- **M5-7:** Bootstrap bloğu tutma süresinin en az iki katı: 20 seansta 40. Önceden kapsama %95 yerine yaklaşık %90'dı.
- **M5-8:** Karne, hisseler arası bağımlılığı da gösteriyor. "Bağımsız tarih" en az h seans aralıklı giriş tarihlerinin sayısı; bütün hisseler birlikte sayılıyor.
- **M5-9:** Üyelik tablosu bittiyse son değer ileri taşınmıyor.
- Karne istatistikleri değiştiği için `CARD_FORMAT` 5 oldu; önbellekteki eski karneler yeniden hesaplanacak.
- Doğrulama: yeni `test_faz_c_m5` (9 test), önce kırmızı sonra yeşil. Bir sınır durumu da yakalandı: fiyat deposunda verisi olmayan hisse için boş tablo artık hata vermiyor.

## v0.99.79 – 05.11.2026 (Faz C, 1. parti: ML filtresinin ölçüm yöntemi; K-77)
- M30 (ML filtresi, kapalı) için bağımsız doğrulamanın beş bulgusu kapatıldı. Model yeniden ölçülmedi.
  - `stop_hedef` aralığı 10 seanslık tarih blok bootstrap ile hesaplanıyor (M30-1). Örtüşen etiketlerde Wilson aralığı 3 kattan fazla dar çıkıyordu.
  - Ölçüm 01.04.2022'den, ilk test yılı 2023'ten başlıyor; öncesinde üyelik zaman noktasında değil (M30-2).
  - Etiketi holdout'ta biten test satırı test edilmiyor (M30-3).
  - Geçme kuralına maliyet sonrası pozitif ortalama, tüm girişlerden yüksek ortalama ve kayıp kuyruğu koşulları eklendi (M30-5).
  - 10. seansı tabanda kilitli etiket ilk kilitsiz açılıştan kapanıyor (M30-5).
  - `/tara`'da ML değeri "ml_skor" adını taşıyor ve "kalibre değil, olasılık değildir" notuyla gösteriliyor (M30-9).
- K-64 kodu ve 03.02.2027 ileri testi etkilenmedi; K-59 ve K-62 KAPALI kaldı.
- Doğrulama: yeni `test_faz_c_m30` (13 test), önce kırmızı sonra yeşil. `test_ml_filter` (15) ve `test_signal_book` geçti.

## v0.99.78 – 04.11.2026 (M31 ve M32 yeniden doğrulaması ve bulguların düzeltilmesi)
- Faz A ve B sonrasında iki bağımsız inceleyici M31 ve M32'yi yeniden doğruladı. Kararlar: M31 **kullanılamaz** (K-64 ve K-68 kendi ölçütlerini geçmiyor), M32 **kısıtlı**. Raporlar `docs/validation/M31.md` ve `M32.md`'de; inceleyicinin metni değiştirilmedi, sonuna ayrı bir geliştirici eki kondu.
- **M32 YÜKSEK – kilitli gün saatlik takipte işlemiyordu.** Tabanda kilitli bir günün yalnız ilk saati kilitli sayılıyordu, sonraki saatlerde stop kilit fiyatından doluyordu. Artık kilit seans günü düzeyinde belirleniyor: o günün bütün mumları tek fiyatsa ve günün kapanışı bir önceki güne göre limitse, bütün saatler kilitli. Günlük çerçevede sonuç aynı.
- **M32 ORTA:**
  - Son seansı kilitli pozisyon, süre dolumunda ilk kilitsiz açılıştan kapanıyor.
  - /panik, girişten önceki günün kapanışıyla kapatmıyor; o pozisyon açık kalıyor.
- **M31:**
  - Doğrulanmamış kartta skor "Model skoru (kalibre değil, olasılık değildir)" olarak yazılıyor. Lot satırı "yalnız sanal defter, işlem önerisi değil" diyor.
  - Kart, giriş seansının tarihini yazıyor.
  - Canlı model 02.11.2026 öncesiyle sınırlı; holdout görmüyor.
  - Yeniden eğitilemeyen eski model tarihiyle bildiriliyor.
  - Aynı günün kartları boş nakdi paylaşıyor.
- **Ölçüm damgası:**
  - Sonuç dosyaları (`logs/*.json`) veri ve kod damgası taşıyor.
  - Damgaya Python ve kütüphane sürümleri eklendi.
  - İzlenmeyen bir .py dosyası varken damga "temiz" demiyor.
- **Diğer:**
  - Testler panik kilidini her zaman geçici klasöre yazıyor.
  - /panik açıklaması güncellendi.
  - Model kapısı "Karar: kısıtlı" biçimini de okuyor; önceden M32 raporu kapıdan düşüyordu.
- **Ertelenenler:** K-63, K-64 ya da K-68 değerlendirme kodunu ya da üretim kuralını değiştiren bulgular (M31 D3, D4, D6, D7; ML etiketlerinde süre dolumu kilidi). Bunlar Faz C'de ya da 03.02.2027 ileri testinden sonra ele alınacak. Eşik, kural ve ileri test ölçütü değişmedi.
- Doğrulama: `test_m31_revalidation` (12 test) ve `test_m32_revalidation` (11 test), önce kırmızı sonra yeşil. Davranışı bilerek değişen iki eski test (`test_control`) yeni beklentiye göre güncellendi.

## v0.99.77 – 04.11.2026 (ölçüm kontrolü bilgisayarda tek komutla; K-76)
- Yeni `scripts\olcum.ps1` (`python -m core.analytics.provenance pc`):
  - Saatlik veriyi indirir ve holdout öncesini yedek klasörüne (`BACKUP_DIR`, ör. OneDrive) dondurur.
  - K-63 ve K-64'ü bu veride ayrı süreçlerde iki kez çalıştırıp karşılaştırır.
  - Günlük fiyat deposunu da dondurur.
  - Kısa raporu `logs\olcum_report.txt`'ye yazar.
  - Rutin kontrol için sohbet oturumu ya da GitHub artifact'ı gerekmez (kullanıcı isteği, 04.11).
- Dondurulmuş veriyle (`--veri`) çalışan K-63 ve K-64 artık `logs/` içindeki sonuç dosyalarına yazmıyor. Bir kontrol, kayıtlı ölçümün yerine geçmesin diye.
- Bot, kural ve eşik değişmedi. Saatlik veri, botun K-65 için zaten kullandığı Yahoo verisi; yeni bir kaynak açılmadı.
- Doğrulama: `test_provenance` testleri 20'ye çıktı:
  - iki aynı çalıştırma "tekrarlanabilir" çıkıyor;
  - farklı çalıştırma "SORUN VAR" çıkıyor;
  - `--veri` çalıştırması sonuç dosyası yazmıyor.
  - Ayrıca gerçek alt süreçlerle uçtan uca sınandı.

## v0.99.76 – 04.11.2026 (CI kırmızısı: iki test sorunu ve Windows'ta çöken uyarı satırı)
- 0c8408a (yalnız belge değişikliği) ve c30c81f CI'da kırmızıydı. PC güncelleyicisi yalnız tamamen yeşil commit'e geçtiği için bu commit'ler PC'ye kurulmadı.
- **Linux:** `test_the_updater_backup_is_not_the_days_backup` başarısızdı. `create_backup`'ın `files` varsayılanı fonksiyon tanımlanırken bağlanıyordu, bu yüzden testteki `PERSONAL_FILES` yaması etkisizdi. Fonksiyon gerçek kişisel dosya listesine bakıyordu; CI'da bu dosyalar olmadığı için yedek oluşmuyordu. Yerelde geçmesinin nedeni bulut kapsayıcısında boş bir `data/watchlist.json` dosyasının bulunmasıydı. Artık varsayılan, çağrı anında okunuyor. Davranış aynı; yalnız yamalanabilir hale geldi.
- **Windows:** `test_control.LiveModelTest` eski bir model veriyordu. `/tara ai` modeli 10 günden eski bulup yeniden eğitiyor ve gerçek `logs/signal_model.joblib`'e yazıyordu. Koruyucu bunu yakaladı, ama uyarı satırı Türkçe karakter yüzünden Windows konsolunda (cp1252) çöktü. Artık her testte model dosyası geçici klasöre yönlendiriliyor (`conftest`) ve uyarı satırı yalnız ASCII basılıyor.
- Doğrulama: Önce `data/watchlist.json` geçici olarak kaldırıldı. Yedek testi düzeltmeden önce kırmızı, sonra yeşil oldu. Tam paket koruyucuyla çalıştırıldı: önce `logs/signal_model.joblib` uyarısı çıktı, düzeltmeden sonra çıkmadı.

## v0.99.75 – 04.11.2026 (ölçüm altyapısı: veri ve kod kimliği, dondurulmuş görüntü; K-76)
- Yeni `core/analytics/provenance.py`. Ölçümün gördüğü veriyi tanımlar: hisse ve mum sayısı, ilk ve son zaman, holdout sınırı, SHA-256 özeti. Çalışan kodu da tanımlar: sürüm, commit, kaydedilmemiş değişiklik olup olmadığı, `core` klasörü. Veriyi dondurur (`snapshot.csv.gz` + `manifest.json`, yalnız 02.11.2026 öncesi) ve geri okurken özeti denetler. İki indirmeyi hisse hisse karşılaştırır.
- K-63 (`dip_study`), K-64 (`signal_filter`) ve K-68 (`card_study`) rapordan önce veri ve kod satırını, rapordan sonra raporun özetini yazıyor. K-63 ve K-64 saatlik `--veri KLASÖR` ile dondurulmuş görüntüyü okuyabiliyor.
- `hourly.yml`: Saatlik veri bir kez indirilip donduruluyor; K-63 ve K-64 aynı görüntüyü okuyor. Önceden her adım ayrı indiriyordu. Görüntü 90 gün artifact olarak saklanıyor.
- card-study, screens ve scenarios iş akışları günlük fiyat deposunun tanımını yazıyor.
- Yeni `snapshot.yml`: saatlik ve günlük veriyi donduruyor; saatlik veriyi iki kez indirip karşılaştırıyor; K-63 ve K-64'ü aynı görüntüde iki kez çalıştırıyor. Raporlar farklıysa kırmızı oluyor.
- Kural, eşik, geçme koşulu ve 03.02.2027 ölçütü değişmedi.
- Doğrulama: yeni `test_provenance` (17 test). Kapsadıkları: özetin sıraya bağlı olmaması; tek değer ya da tek mum değişince özetin değişmesi; dondur ve geri oku sonrası aynı veri; aynı veriden aynı dosya; bozulmuş dosyanın ve manifestin reddi; saat dilimsiz günlük veri; günlük deponun holdout öncesi dondurulması; iki indirmenin hisse hisse farkı; `core`'un yüklendiği klasör; K-63 ve K-64'ün iki kez aynı rapor vermesi (K-64'te model gerçekten eğitiliyor); komutların ilk iki satırı. Yerelde ayrı süreçlerde farklı `PYTHONHASHSEED` ile iki çalıştırma birebir aynı çıktı.

## v0.99.74 – 04.11.2026 (Faz B, 2. adım: kilitli günde dolum yok; K-75)
- `core/market/limits.py`'ye `locked_down` ve `locked_up` eklendi. Kilitli gün, bütün gün tek fiyatın görüldüğü (en yüksek = en düşük) limit günüdür.
- **Tabanda kilitli gün, satış dolmaz.** Stop ya da geçersizlik ilk kilitsiz günün açılışından gerçekleşiyor. Doğrulamadaki iyimser varsayım kalktı. Örnek: 89'da kilitli bir günden sonra 88'den açılışta çıkış; eskiden 98'deki stoptan çıkılmış sayılıyordu.
  - sanal sinyal defterinin takibi (M32-9);
  - ML etiketleri (M30-5);
  - senaryo sonuçları (M27-6).
- **Tavanda kilitli giriş günü, alış dolmaz:** `/tara` karnesi o olayı saymıyor (M5-3).
- Tek fiyatlı −%30'luk bir mumu "boşluklu stop" örneği olarak kullanan üç test, işlem gören bir boşluk mumuyla güncellendi. Beklenen sonuçları aynı kaldı.
- Sırada Faz B'nin son adımı: etkilenen ölçümlerin GitHub Actions'ta yeniden çalıştırılması ve RESEARCH_LOG'a eski ve yeni sonucun yan yana yazılması.
- Doğrulama: `test_limits` (LockedDaysTest, 5 test): maske; defter, ML etiketi ve senaryo ilk kilitsiz açılıştan çıkıyor; karne kilitli tavanda dolum saymıyor. Önce kırmızı, sonra yeşil.

## v0.99.73 – 04.11.2026 (Faz B, 1. adım: tavan ve taban kuralı tek yerde; K-75)
- Yeni `core/market/limits.py`: `limit_up`, `limit_down` ve `limit_move` fonksiyonları. Hareket %9,5 ya da daha fazlaysa limit sayılıyor; karşılaştırma kayan nokta payı taşıyor. 100 → 109,5 artık her yerde limit (0,0949999… < 0,095 sorunu kalktı).
- Bu fonksiyonları kullanan 10 modül: backtest motoru, sanal emirler, sinyal defteri, tarama elemesi, sinyal onay katmanı, ML etiketleri (iki yer), strateji filtresi, pozisyon uyarıları, senaryolar (iki yer), seviyeler (iki yer). `>` ile `>=` farkı kalktı.
- Yeni bir test hiçbir modülün sınırı kendi başına karşılaştırmadığını denetliyor. Kural tekrar dağılırsa CI kırmızı olur.
- `/tara`'nın veri sıçraması eşiği (%10,5) ayrı bir kavram; karışmasın diye adı `JUMP_MOVE` oldu.
- Etki: Yalnız tam %9,5 sınırındaki hareketler değişiyor; bunlar çok seyrek. Kilitli gün dolum kuralı ve ölçümlerin yeniden çalıştırılması sonraki adımlarda.
- Doğrulama: yeni `test_limits` (3 test): sınır çizgisi limit sayılıyor; modüller kendi başına karşılaştırmıyor; defter, ML etiketleri ve senaryolar 109,5 açılışında aynı sonucu veriyor. Tam test geçti.

## v0.99.72 – 04.11.2026 (güncelleyici paket listesini satır sonundan bağımsız karşılaştırıyor)
- Her kurulum "paketler güncellendi" diyor ve 5–7 dakikalık geçici sanal ortam kuruyordu. `requirements.lock` değişmemişti: Windows'taki git kopyası CRLF, GitHub zip'i LF satır sonu taşıyor ve dosyalar bayt bayt karşılaştırılıyordu.
- Artık satır sonları ve boş satırlar hesaba katılmıyor; yalnız paket satırları karşılaştırılıyor. Paket listesi gerçekten değişmedikçe kurulum hızlı gidiyor.
- Doğrulama: `test_guncelle` (LockCompareTest): CRLF ve LF aynı sayılıyor, gerçek bir sürüm farkı fark sayılıyor. Önce kırmızı, sonra yeşil.

## v0.99.71 – 04.11.2026 (Faz A tamam: işlem görmeyen hisse ve bozuk son mum)
- **M1-2:** 60 gün işlem görmeyen hisse (sıfır hacim, tek fiyat) donmuş göstergelerle 90 puan ve "Güçlü pozitif" alıyordu. Artık son 20 seansta hiç hacim yoksa ya da fiyat hiç oynamadıysa teknik görünüm verilmiyor; kısa geçmişteki "görünüm yok" ile aynı.
- **M1-6:** Son mumun kapanışı NaN ise canlı yol sessizce önceki günün değerlerini gösteriyordu. Artık "son mum bozuk (kapanış …, tarih); görünüm hesaplanmadı" hatası veriyor.
- **Faz A'nın 17 bulgusunun hepsi giderildi.** Sıradaki Faz B: tavan ve taban kilidi kuralının bütün modüllerde tek ortak fonksiyonla uygulanması ve etkilenen ölçümlerin yeniden çalıştırılması.
- Doğrulama: `test_phase_a` (Batch4Test, 2 test). Düzeltme olmadan kırmızı, düzeltmeyle yeşil.

## v0.99.70 – 04.11.2026 (Faz A, 3. grup: beş bulgu)
- **M30-7:** Ufuk sonunda kapanış NaN ise satır etiket 0 ve r NaN ile kalıyordu. Artık etiket yazılmıyor. Yalnız sonu verisiz olan satırları etkiliyor.
- **M1-7:** `/analyze`'daki ATR seviyeleri, ATR çarpılmadan önce 2 haneye yuvarlanıyordu. Doğrulamadaki örnek: 1,50 TL ve ATR 0,034 için stop 1,44 çıkıyordu, doğrusu 1,43. Artık önce hesaplanıp sonra yuvarlanıyor.
- **M5-6:** XU100 verisi yoksa karne "yetersiz örnek" diyordu. Artık "XU100 verisi yok; karne hesaplanamadı" diyor.
- **M8-7:** `/tara`'daki seviye alanlarının açıklaması "rastgeleden ayırt edilemedi" notunu, güç puanı ise "ölçülmemiş puan" notunu taşıyor.
- **M31-14:** Yanıltıcı test adı ve `ai.live`'ın dönüş tipi düzeltildi.
- Doğrulama: `test_phase_a` (Batch3Test, 4 test). Düzeltme olmadan kırmızı, düzeltmeyle yeşil.

## v0.99.69 – 04.11.2026 (Faz A, 2. grup: dört bulgu)
- **M30-4:** Canlı ML filtresi, "passed" yazan herhangi bir rapor dosyasıyla açılabiliyordu. Artık yalnız kendi ölçümüyle açılıyor: BIST 30 evreni, stop/hedef kuralı ve holdout kullanılmamış olmalı. BIST 100 ölçümü artık BIST 30 dosyasının üzerine yazılmıyor; ayrı dosyaya gidiyor.
- **M30-10:** `/tara ml=evet` model kapısını okumuyordu. Artık M30'un kapısı kapalıysa liste boş kalıyor ve nedeni yazılıyor.
- **M31-13:** Cuma yeniden eğitimi atlanırsa eski canlı model uyarısız kullanılıyordu. Artık 10 günden eski model `/tara ai`'de yeniden eğitiliyor.
- **M32-10:** `risk_tl` kart fiyatıyla yazılıyordu. Artık giriş gerçekleşince gerçek giriş fiyatıyla güncelleniyor. Doğrulamadaki örnek: boşluklu açılışta kayıtlı risk 200 TL yerine 180 TL.
- Doğrulama: `test_phase_a` (Batch2Test, 4 test). Önce kırmızı, sonra yeşil. Eski gevşek davranışı bekleyen iki test (`test_ml_filter`, `test_signal_book`) yeni kurala göre güncellendi.

## v0.99.68 – 04.11.2026 (Faz A, 1. grup: yedi küçük hata)
- Eksiksiz iş planı ROADMAP'e yazıldı. Bağımsız doğrulama raporlarının her bulgusu bir yerde duruyor: yapıldı, Faz A, Faz B, Faz C ya da gerekçesiyle bırakıldı.
- Faz A, ölçüm kuralını değiştirmeyen düz hatalar. Bu grupta yedisi giderildi:
  - **M27-5:** `/senaryo` risk sınırı mesajda "%0,1 ile %5" diyordu ama kod her pozitif değeri alıyordu. Artık mesajdaki sınır uygulanıyor.
  - **M27-7:** Adet satırı "maliyet ve boşluk hariç" diyor.
  - **M8-4:** Son kapanış NaN ya da 0 iken psikolojik seviye hesabı istisna veriyordu. Artık seviye vermiyor.
  - **M30-8:** `goreli20` kuralı XU100 kapanışları olmadan çağrılınca anlaşılmaz bir `AttributeError` veriyordu. Artık açık bir mesaj veriyor.
  - **M31-9:** Rapor dosyası `null`, `[]` gibi bozuk içerikteyse `validated` ve `track_record` çöküyordu. Artık "doğrulanmadı" ve kayıtlı ölçüm dönüyor.
  - **M5-10:** Karne açıklaması "21 günlük blok" diyordu, sabit 20. Açıklama düzeltildi.
  - **M32-8:** Şalter tablosunun açıklaması "sonraki seansı kilitler" diyordu, kod aynı günü kilitliyor. Açıklama düzeltildi.
- Doğrulama: yeni `tests/test_phase_a.py` (her bulguya bir test). Önce kırmızı, sonra yeşil. İlgili 105 test geçti.

## v0.99.67 – 04.11.2026 (şirket işleminden sonra senaryo kayıtları kaybolmuyor; M27 ORTA 1)
- Canlı senaryo kaydı seviyeleri kayıt gününün fiyatıyla tutuyor. Puanlama ise geriye doğru düzeltilmiş mumlarla yapılıyor. 2:1 bedelsizden sonra geçmiş fiyatlar yarıya iniyor, seviyeler artık girişe uymuyordu. Kayıt "dolmadı" sayılıp sessizce kayboluyordu; doğrulamada 31 kaydın hepsi "0/30 sonuçlanan, 0 süren" oldu.
- Artık geçersizlik ve hedef aynı düzeltme katsayısıyla ölçekleniyor: kayıt günündeki düzeltilmiş kapanış ÷ kayıtlı kapanış. Katsayı yoksa ya da 1 ise hiçbir şey değişmiyor. Temettü düzeltmesi de aynı yolla hesaba giriyor.
- Kayıt dosyası değiştirilmiyor; düzeltme okurken yapılıyor.
- Doğrulama: `test_validation_fixes` (ScenarioCorporateActionTest): bedelsiz sonrası kayıt hedefte sonuçlanıyor. Önce kırmızı, sonra yeşil. Senaryo testleri geçti.

## v0.99.66 – 04.11.2026 (/durum'da kendiliğinden kapanmayan iki uyarı; K-74)
- **Model doğrulama:** M30 ve M31 "kullanılamaz" olduğu için satır kalıcı ⚠️ olmuştu. Model kapısı ikisini zaten kapalı tutuyor. Artık bu durum ℹ️ olarak gösteriliyor ve metin bunu söylüyor. ⚠️ yalnız süresi geçmiş doğrulamada çıkıyor (K-74).
- **Güncelleme öncesi yedek:** Güncelleyicinin kurulumdan önce aldığı yedek (`quantbist_2026-11-04.zip`, 15:40) günün yedeğiyle aynı adı taşıyordu. Gün, 18:30 raporundan önce "yedekli" sayılıyordu; rapor çalışmasa 21:00 telafisi de atlanırdı. Artık bu yedek `quantbist_guncelleme_<tarih_saat>.zip` adıyla alınıyor, günün yedeği sayılmıyor ve son 5'i tutuluyor.
- Doğrulama: `test_validation_fixes` (StandingWarningsTest, 2 test); `test_model_validation`'daki eski beklenti K-74'e göre güncellendi. Önce kırmızı, sonra yeşil.

## v0.99.65 – 04.11.2026 (/tara karnesi "olumlu" demek için tüm hisseleri de geçmeli; M5 ORTA)
- Karne etiketi yalnız XU100'e bakıyordu. Bu yüzden hiçbir şey seçmeyen `kapanis>0` taraması (bütün hisseler) da "geçmişte olumlu" çıkıyordu.
- Artık "olumlu" için iki koşul gerekiyor: aralığın alt ucu hem sıfırın, yani XU100'ün, hem de aynı günlerde "tüm hisseler" tabanının üstünde olmalı. Yalnız XU100'ü geçen tarama "XU100'ün önünde ama tüm hisselerden ayırt edilemiyor; tarama bir şey seçmedi" diyor.
- Etiket hesaplanan bir alan; önbellekteki eski karneler de yeni kuralla okunuyor. Sayılar değişmedi.
- Doğrulama: `test_validation_fixes` (CardLabelTest): tabana eşit tarama "olumlu" olmuyor, tabanı geçen oluyor. Önce kırmızı, sonra yeşil. Karne ve tarama testleri geçti.

## v0.99.64 – 04.11.2026 (/durum kısa özet; tam liste /durum tum; K-70 madde 7)
- `/durum` 30'dan fazla satırdı ve sorunlar sağlıklı satırların arasında kayboluyordu. Artık kısa özet veriyor:
  - sağlıklı bileşenler tek satırda sayılıyor ("✅ 14 bileşen sağlıklı");
  - uyarı, kritik, bilinmeyen ve bilgi satırları tek tek yazılıyor;
  - SLO'lar tek satırda geliyor: kaçı hedefte, kaçı ölçülemiyor, hangileri hedef dışı (değeriyle);
  - güvenilirlik satırı ve sanal kasa olduğu gibi duruyor.
- Eski tam rapor `/durum tum` ile alınıyor. Cuma raporu ve `verify` tam raporu kullanmaya devam ediyor.
- Hiçbir sorun gizlenmiyor: sağlıklı olmayan her satır kısa özette de var.
- Doğrulama: `test_durum_compact` (3 test): kısa özet her sorunu tutuyor, sağlıklıları sayıyor, daha kısa; tam liste eskisi gibi; komut argümanı. Önce kırmızı, sonra yeşil.

## v0.99.63 – 04.11.2026 (karnede sonsuz ortalama ve eski haftalık pivot; M5 ve M8 ORTA)
- **M5:** Tek bir sıfır açılış `/tara` karnesinin ortalamasını +%∞ yapıyor, etiketi "geçmişte olumlu" çıkarıyordu. `~isnan` sonsuzu elemiyordu. Artık yalnız sonlu sonuçlar sayılıyor; hem tarama sonucu hem "tüm hisseler" tabanı için.
- **M8:** Haftalık pivot Cuma kapanışından Pazartesi kapanışına kadar bir hafta eskiydi (doğrulamada P 104,44 yerine 105,75). Artık son mum haftanın son seansıysa (Cuma ya da tatilden önceki gün) biten hafta kullanılıyor.
- Doğrulama: `test_validation_fixes` (MediumFindings2Test, 2 test). İkisi de düzeltme olmadan kırmızı, düzeltmeyle yeşil. Seviye, karne ve senaryo testleri geçti.

## v0.99.62 – 04.11.2026 (ölçülmemiş güç artık güç gibi gösterilmiyor; M1 ve M8 YÜKSEK, K-73)
- **M1:** `/top` başlığı "Teknik görünümü en güçlü hisseler" yerine "Teknik skoru en yüksek hisseler (sıralama, öneri değil)" oldu. "Tahmin gücü bulunmadı" uyarısı listenin başına alındı. Komut açıklaması ve BotFather listesi de güncellendi.
  - "Güçlü pozitif" etiketleri korundu; canlı ölçümde anahtar olarak kullanılıyorlar.
- **M8:** Seviye satırlarında ve rapordaki en yakın destek satırında "güç N"nin yanında "ölçülmemiş puan" yazıyor.
- Doğrulama: `test_validation_fixes` (HonestLabelsTest, 2 test). Önce kırmızı, sonra yeşil. Bot, seviye ve senaryo testleri geçti.
- Telegram menüsü bot açılırken kendiliğinden güncelleniyor (`set_my_commands`); BotFather'da elle bir şey yapmak gerekmiyor.

## v0.99.61 – 04.11.2026 (M1, M5, M8 bağımsız doğrulandı: 14/14 model raporlu)
- Ayrı inceleyici son üç yüksek riskli modeli doğruladı. Raporlar olduğu gibi eklendi: `docs/validation/M1.md`, `M5.md`, `M8.md`. Üçü de **kısıtlı kullanılabilir**.
- **M1 (teknik skor):** Hesaplar ve ileriye bakma denetimi tuttu.
  - YÜKSEK: Kodun kendisi skorun tahmin gücü olmadığını söylüyor, ama skor yine "Güçlü" etiketi veriyor ve /top'u sıralıyor. Rastgele yürüyüşte günlerin %60'ı "Güçlü" çıkıyor.
  - ORTA: 60 gün işlem görmeyen hisse 90 puan alıyor. Eksik şirket işlemi kaydı görünümü tersine çeviriyor. Kural simetrik değil.
- **M5 (/tara karnesi):** Giriş, maliyet, holdout kesimi ve aralıklar elle tuttu. YÜKSEK bulgu yok.
  - ORTA: Etiket "tüm hisseler" yerine XU100 ile kıyaslıyor. Evren bugünkü tam veriyle seçiliyor. Tavan kilitli girişte dolum varsayılıyor. Sıfır açılış ortalamayı sonsuz yapıyor.
- **M8 (destek/direnç):** Zamanlama, ileriye bakma ve formüller tuttu.
  - YÜKSEK: Kodun kendi çalışması küme seviyelerini rastgele seviyelerden ayırt edemiyor. "Güç" puanı ve diğer yedi yöntem hiç ölçülmemiş, ama her yerde gösteriliyor.
  - ORTA: Haftalık pivot Cuma akşamı ve Pazartesi seansında bir hafta eski. Kümeleme zincirleme genişliyor.
- **Model doğrulama 14/14 raporlu.** Hiçbir model "kullanılabilir" değil: M30 ve M31 kullanılamaz, diğer 12'si kısıtlı. Model kapısı otomatik eylemleri kapalı tutuyor.
- YÜKSEK bulguların düzeltmesi sonraki sürümlerde.

## v0.99.60 – 04.11.2026 (güncelleyici botu yeni klasörde görüyor)
- **Olay (04.11, kullanıcının PC'si):** Güncelleyici v0.99.59'u kurdu, botu başlattı ama "açılmadı" sanıp geri aldı. Sonra "BOT KAPALI — müdahale gerekiyor" bildirdi.
- **Neden:** Bot, süreç listesinde sabit `QuantBIST\.venv` yolu aranarak bulunuyordu; bu eski klasörün yolu. `QuantBIST-yeni`'den çalışan bot hiç bulunamıyordu, bot çalışsa bile ölü görünüyordu. v0.99.44'te klasör betiğin kendi yerine çevrilirken bu satır gözden kaçmıştı. PC'deki otomasyon notu bu riski önceden yazmıştı.
- **Düzeltme:** Bot, güncelleyicinin kendi klasöründeki `.venv` ile `main.py` çalıştıran süreç olarak aranıyor. Başka bir klasördeki bot bu klasörün botu sayılmıyor.
- **PC'de bir kez elle güncelleme gerekiyor:** Geri alma, PC'yi hatalı güncelleyiciyi içeren v0.99.44'e döndürdü. Bu yüzden düzeltme kendiliğinden kurulamaz. Kullanıcı bir kez `git pull` yapıp botu yeniden başlatmalı; sonrası saatlik görevle gider.
- Doğrulama: `test_guncelle` (BotDetectionTest): yeni klasörün botu bulunuyor, eski klasörün botu bulunmuyor. Önce kırmızı, sonra yeşil.

## v0.99.59 – 04.11.2026 (CI testleri Windows'ta da çalıştırıyor)
- v0.99.48–57 CI'da geçip kullanıcının Windows PC'sinde düştü; güncelleyici hiçbirini kuramadı. Bilgisayar Windows olduğu için CI'a `windows-latest` üzerinde tam test işi eklendi.
- Güncelleyici yalnız bütün CI işleri yeşil olan commit'i kuruyor. Böylece Windows'ta düşecek bir sürüm PC'ye hiç gönderilmiyor; sorun CI'da görünüyor.
- Doğrulama: ilk sonuç bu sürümün CI çalışmasında görülecek. Kırmızı çıkarsa bu sürüm PC'ye kurulmaz; v0.99.58 kurulur.

## v0.99.58 – 04.11.2026 (Windows'ta düşen iki test düzeltildi: v0.99.48'den beri PC'ye kurulum yoktu)
- **Kanıt (kullanıcının PC'si):** Güncelleyici v0.99.48, v0.99.50, v0.99.54 ve v0.99.57'yi deneme kopyasında "2 failed" diyerek kurmadı; bot v0.99.44'te kaldı. PC'deki otomasyon notu: bir testte SQLite bağlantısı açık kalıyor; ürün hatası değil.
- **Neden:** İki test sinyal defteri bağlantısını kapatmıyordu: `AiTest.test_run_writes_the_book_only_when_validated` ve `ApprovalTest.test_daily_step_and_new_scan_sweep_old_cards`. Linux açık dosyayı silebiliyor, Windows silemiyor; bu yüzden CI'da ve bu ortamda görünmedi. Güncelleyicinin güvenlik kapısı doğru çalıştı: testi geçmeyen sürüm kurulmadı.
- **Düzeltme:** İki test bağlantıyı kapatıyor.
- **Kalıcı koruma:** `tests/conftest.py`'ye her testin sonunda açık kalan sinyal defteri bağlantısını arayan bir denetim eklendi. Açık bağlantı bırakan test artık Linux'ta da düşüyor; denetim iki testi de yakaladı.
- Bir sonraki saatlik çalışmada PC bu sürümü kurabilmeli.

## v0.99.57 – 04.11.2026 (/senaryo: sıfır seviye ve binlik ayırıcı; M27 ORTA 2 ve 3)
- `/senaryo X giris 0 gecersiz -5 hedef 10` sıfıra bölmeyle çöküyordu; negatif geçersizlik de kabul ediliyordu. Artık "giriş, geçersizlik ve hedef sıfırdan büyük olmalı" diyor.
- "1.250" gibi Türkçe binlik ayırıcı 1,25 okunuyor, adet 4.000 çıkıyordu. Artık noktadan sonra üçlü basamak grupları varsa nokta binlik ayırıcı sayılıyor: "1.250" = 1250, "1.250,5" = 1250,5. "240.5" gibi bir ya da iki ondalıklı yazım eskisi gibi ondalık okunuyor.
- Kalan M27 ORTA bulguları: şirket işleminden sonra canlı kaydın puanlanması ve karne ağırlığı. Bu ikisi ölçüm kurallarını etkiliyor; ayrı iş olarak sırada.
- Doğrulama: `test_validation_fixes` (ScenarioInputTest, 2 yeni test). Önce kırmızı, sonra yeşil. Senaryo testlerinin hepsi geçti.

## v0.99.56 – 04.11.2026 (M30 ve M27 bağımsız doğrulandı: kullanılamaz ve kısıtlı)
- Geliştirici notlarını okumayan ayrı bir inceleyici iki modeli daha doğruladı. Raporlar olduğu gibi eklendi: `docs/validation/M30.md`, `M27.md`.
- **M30 (ML filtresi): Kullanılamaz.**
  - YÜKSEK 1: Geçme kuralındaki Wilson aralığı örtüşen ve aynı günde birlikte hareket eden sinyalleri bağımsız sayıyor; aralık olduğundan dar çıkıyor.
  - YÜKSEK 2: 2022 öncesinde endeks üyeliği zaman noktasında değil; hayatta kalanlar yanlılığı var.
  - ORTA: 2026 test etiketleri holdout fiyatlarına uzanıyor; `enabled()` evren, kural ve tarihi denetlemiyor; geçme kuralı getiri şartı koymuyor; taban kilitte çıkış iyimser.
  - Model kapısı M30'u zaten kapalı tutuyor; filtre kendiliğinden hiçbir şey yazamıyor.
- **M27 (senaryo şablonları): Kısıtlı kullanılabilir.** YÜKSEK bulgu yok. ORTA: şirket işleminden sonra canlı kayıt yanlış puanlanıyor; sıfır girişte komut çöküyor; "1.250" gibi binlik ayırıcı 1,25 okunuyor; karnede ortalama R ile aralığı farklı ağırlıklı.
- Model doğrulama: 14 modelden 11'i raporlu. Kalan: M1, M5, M8. Bulguların düzeltmesi sonraki sürümlerde.

## v0.99.55 – 04.11.2026 (güncelleyici ağı bekliyor)
- **Kanıt (kullanıcının PC'si, 04.11):** Saatlik "QuantBIST Guncelle" görevi 09:40, 10:40 ve 11:40'ta `URLError: getaddrinfo failed` ile durdu. Aynı dakikalarda DNS çalışıyordu, Python elle GitHub'a bağlanıyordu (200) ve bot yaşıyordu. Hata yalnız görevin başladığı anda oluşuyor. Bu yüzden PC v0.99.44'te kaldı.
- Aynı hata 28.10 18:30 raporunu da düşürmüştü. 31.10 01:36 telafisinin 30.10 fiyatlarını indirememesinin de en olası nedeni bu (`daily_2026-10-31.log` 28.10 verisiyle rapor üretti). Bu bulgu AUDIT 5'e eklendi.
- **Düzeltme:** Güncelleyici ilk GitHub isteğinde ağ hatası alırsa 30 saniye, 1 dakika ve 2 dakika bekleyip yeniden deniyor. Ağ yine gelmezse "BAĞLANTI YOK" yazıp duruyor; o durumda Telegram'a da ulaşılamayacağı için mesaj denemiyor. Bir saat sonra yeniden çalışıyor.
- Doğrulama: `test_guncelle` (2 yeni test): geç gelen ağ bekleniyor; ağ hiç yoksa bekleme süreleri ve sessiz sonuç doğru.

## v0.99.54 – 04.11.2026 (eski veriyle kart yazılmıyor; yol planı ROADMAP'te)
- **M31-ORTA-3:** Fiyat güncellenmediyse `/tara ai` aylar önceki muma bakıp bugünün tarihli kartını yazıyordu (doğrulamada: son mum 14.07, kart 04.11). Artık tetiğin geldiği mum son kesinleşmiş seanstan eskiyse kart yazılmıyor ve düğme konmuyor. Mesaj "veri eski (son mum …, beklenen …)" diyor ve `/durum`'a yönlendiriyor.
- **M31-ORTA-6 ve M32-4, bilinçli bırakıldı:** Kart, üretildiği günden sonraki ilk açılışta giriyor. Seans içinde üretilen kartın o günün geçmiş açılışından girmesi geleceği görmek olurdu. Tek istisna seans açılmadan önce üretilen kart; o durumda bir seans geç girer, sonuç ihtiyatlı tarafta kalır.
- **ROADMAP:** Kullanıcının "sen kursan neler katardın" sorusuna verilen yol planı yazıldı: güvenilirlik, uzun vade için karar desteği, dürüst araştırma programı, işletme kalitesi ve eklenmeyecekler.
- Doğrulama: `test_validation_fixes` (StaleDataTest, 2 yeni test): eski mumda kart ve düğme yok; güncel mumda kart var. Önce kırmızı, sonra yeşil.

## v0.99.53 – 04.11.2026 (doğrulamanın ORTA ve DÜŞÜK bulgularından üçü düzeltildi)
- **M32-5:** Fiyatı 0 olan bir mum pozisyonu 0'dan kapatıyordu: r = −%100,15, şalter açılırdı. Eksik ya da sıfır/negatif fiyatlı mum artık bozuk veri sayılıp takipte atlanıyor.
- **M32-6:** Süre dolumunda kapanış NaN ise işlem sonuçsuz (NULL) kapanıyor, kasaya girmiyordu. Aynı kural bunu da önlüyor; son geçerli kapanış kullanılıyor.
- **M31-ORTA-4:** Kart kuralı çalışmasında olay sayısı 0 ise kart satırı çöküyordu. Artık "olay yok, ölçülemedi" yazıyor.
- **Düzeltilmedi, belgelendi (M32-7):** %9,5 tavan sınırı kayan noktayla 100 → 109,5'i tavan saymıyor. Aynı karşılaştırma araştırma etiketlerinde, backtest'te ve tarama elemesinde de var (yaklaşık 10 modül). Yalnız defteri değiştirmek, defteri modelin ölçüldüğü kurallardan ayırırdı. Ya hepsi birlikte değiştirilecek ya hiçbiri; AUDIT'e iş olarak eklendi.
- Doğrulama: `test_validation_fixes` (3 yeni test). Önce kırmızı, sonra yeşil.

## v0.99.52 – 04.11.2026 (bağımsız doğrulamanın üç YÜKSEK bulgusu düzeltildi)
- **M32-1, kasa aşımı:** Aynı gün birden çok kart aynı boş nakitle lotlanıyordu; dört kart 100.000 TL'lik kasada 199.673 TL'ye ulaştı. Artık ✅ düğmesi o anki boş nakdi yeniden kontrol ediyor. Nakit yetmezse lot küçülüyor; hiç kalmadıysa "💰 boş nakit yok" deniyor ve kart gün içinde geçerli kalıyor.
- **M32-2, panik zararı siliyor:** Panik açık pozisyonları iptal edip sonucunu siliyordu; 7.000 TL'lik açık zarar kayboluyordu. Artık açık pozisyonlar son kapanıştan "panik" durumuyla kapatılıyor ve sonuç kasaya yazılıyor. Fiyatı olmayan pozisyon açık kalıyor; ne siliniyor ne uyduruluyor. Onay bekleyen ve girişi bekleyen sinyaller eskisi gibi iptal ediliyor.
- **M31-1, geçmeyen model "onay" diyordu:** Kart başlığı "✅ AI onayı" yerine "🧪 Doğrulanmamış model sinyali (M31 bağımsız doğrulamada kullanılamaz)" oldu. Model doğrulanırsa eski başlık dönüyor. `ai.py`'nin açıklaması da gerçeğe uygun hâle getirildi: kart deftere yalnız kullanıcının düğmesi için yazılıyor.
- Bu davranışı doğru sayan dört eski test yeni davranışa göre güncellendi.
- Raporların kararı değişmedi. M31 kullanılamaz, M32 kısıtlı kalıyor; bunu yeniden doğrulama belirler. ORTA bulgular sıradaki işler arasında.
- Doğrulama: `test_validation_fixes` (5 test): kasa aşılmıyor; lot boş nakde iniyor; panik zararı sayıyor; fiyat yoksa pozisyon açık kalıyor; geçmeyen model "onay" demiyor. Önce kırmızı, sonra yeşil.

## v0.99.51 – 04.11.2026 (M31 ve M32 bağımsız doğrulandı: kullanılamaz ve kısıtlı)
- Geliştirici notlarını okumayan ayrı bir inceleyici iki modeli doğruladı. Raporlar olduğu gibi eklendi: `docs/validation/M31.md`, `M32.md`.
- **M31 (sinyal onay katmanı ve kart kuralı): Kullanılamaz.**
  - Modelin kendi örneklem dışı ölçümü geçmedi: onaylananların isabeti %26,2, tabanınki %33,6. Kart kuralı rastgele girişten ayırt edilemedi.
  - İleriye bakma ve sızıntı denetimleri geçti.
  - YÜKSEK bulgu: Geçmeyen model yine "✅ AI onayı" başlıklı, lotlu ve girilebilir kart üretiyor.
- **M32 (sanal sinyal defteri): Kısıtlı kullanılabilir.**
  - 18 elle hesaplanmış senaryonun hepsi tuttu: hedef, boşluk, iz süren stop, süre, şalter, panik reddi, BIST 100 karşılaştırması.
  - YÜKSEK bulgu 1: Aynı gün birden çok kart aynı boş nakitle lotlanıyor; kasa aşılabiliyor.
  - YÜKSEK bulgu 2: Panik, zarardaki açık pozisyonun sonucunu siliyor.
- Model doğrulama: 14 modelden 9'u raporlu. M31 "kullanılamaz" olduğu için `/durum`'daki Model doğrulama satırı uyarıya döndü. Model kapısı zaten kapalıydı.
- Yüksek bulgular sonraki sürümlerde düzeltilecek; raporların kararı değiştirilmeyecek. Yeniden doğrulama ayrı yapılır.

## v0.99.50 – 04.11.2026 (temel veri posta kutusu; K-70 madde 6)
- Yeni `core/fundamentals/inbox.py`: Kullanıcı KAP'tan elle indirip CSV'ye çevirdiği dosyayı `data/inbox/temel/` klasörüne bırakıyor; bot 5 dakikada bir bakıyor.
  - 60 saniyeden yeni dosyaya dokunulmuyor; kopyalama sürüyor olabilir.
  - Mevcut denetimli içe aktarma kullanılıyor: yalnız ekleme, aynı satır iki kez eklenmiyor.
  - Okunan dosya `islendi/`, hiç okunamayan dosya `reddedildi/` klasörüne taşınıyor; reddedilenin yanına nedenleri `.hata.txt` olarak yazılıyor. Aynı adlı eski dosyanın üzerine yazılmıyor.
  - Her dosyanın sonucu Telegram'a bildiriliyor: kaç satır eklendi, kaçı neden reddedildi.
- KAP'a otomatik erişim yok, ağ kodu yok (K-48). Kullanıcının istediği "dosya izleyici ETL", Windows'ta daha sağlam olan bu biçimde yapıldı (K-70 mimari notu).
- `data/inbox/` git dışında.
- Doğrulama: `test_fundamentals_inbox` (6 test): iyi dosya ekleniyor ve taşınıyor; karışık dosyada satırlar sayılıyor; bozuk dosya reddediliyor ve nedeni yazılıyor; kopyalanmakta olan dosya bekliyor; aynı ad üzerine yazılmıyor ve satır iki kez eklenmiyor; bot işi kayıtlı ve her dosyayı bildiriyor. Önce kırmızı, sonra yeşil.

## v0.99.49 – 04.11.2026 (tekrar deneme ve kritik uyarı; kullanıcının "auto-healing" isteği)
- Yeni `core/infrastructure/retry.py`: Geçici hatalar 2, 4, 8 ve 16 saniye sonra yeniden deneniyor; toplam 5 deneme, yaklaşık 30 saniye. Geçici hata: ağ, zaman aşımı, kilitli SQLite. Diğer hatalar programlama hatası sayılıyor ve yeniden denenmiyor, izleriyle log'a yazılıyor.
- Bütün denemeler başarısız olursa Telegram'a "🚨 KRİTİK" mesajı ve JSON yük gidiyor: seviye, iş, deneme sayısı, hata, zaman. Aynı iş ve hata türü 6 saatte bir kez bildiriliyor; uzun bir kesinti tek mesaj olarak geliyor. Bu durum bot yeniden başlasa da korunuyor (`logs/critical_alerts.json`).
- Bağlanan işler: seans içi saatlik sinyal takibi ve 21:00 yedek kontrolü. Saatlik kur tazeleme zaten her saat kendini yeniden deniyor, aynı kalıyor. Fiyat indirmedeki 1, 2 ve 4 dakikalık bekleme de aynı kalıyor.
- Bot hiçbir durumda bu yüzden durmuyor.
- Doğrulama: `test_retry` (6 test): geçici hata yeniden deneniyor ve başarılı oluyor; 5 denemenin bekleme süreleri; programlama hatası yeniden denenmiyor; JSON yük; 6 saatlik tekilleştirme; saatlik takip 5 deneme sonra tek uyarı veriyor. `test_scheduler`: yedek 5 kez deneniyor. Önce kırmızı, sonra yeşil.

## v0.99.48 – 04.11.2026 (K-70 ilerlemesi /durum'da ve cuma raporunda hesaplanıyor)
- Kullanıcı "yüzde kaç olduk" diye sormak zorunda kalmasın, kota da harcanmasın diye ilerleme betikle hesaplanıyor. `/durum`'un ve cuma raporunun SLO bölümünün altında yeni satır var: "🎯 Güvenilirlik (K-70): gözlem x/20 seans · SLO a/b · model doğrulama c/14". Altında "tam güvenilir: hayır (eksik: …)" yazıyor.
- Gözlem: 03.11'den beri gönderilmiş her veri günü bir kez sayılıyor.
- "Tam güvenilir: evet" yalnız bütün ölçütler aynı anda tuttuğunda yazılıyor: en az 20 seans gözlem, bütün SLO'lar hedefte, 14/14 model doğrulama raporu ve ölçülmüş veri doğruluğu.
- Doğrulama: `test_progress` (4 test): aynı gün bir kez sayılıyor; eksik ölçüt "hayır" diyor ve nedenini yazıyor; her şey tamamsa "evet"; `/durum` satırı. Önce kırmızı, sonra yeşil.

## v0.99.47 – 04.11.2026 (model kapısı: doğrulanmamış model kendiliğinden işlem yapamaz; K-72)
- Yeni `core/reports/model_gate.py`: Yüksek riskli bir model yalnız güncel ve "kullanılabilir" kararlı bir bağımsız doğrulamayla kendiliğinden bir şey değiştirebiliyor. Kısıtlı, kullanılamaz, süresi geçmiş ya da raporsuz model yalnız bilgi veriyor. Karar doğrulama raporundan okunuyor, modelin kendi sonucundan değil.
- Günlük sinyal adımı artık iki koşul arıyor: ML filtresinin örneklem dışı geçişi ve M30'un açık kapısı. Bugün M30 kapalı (bağımsız doğrulanmadı).
- `/durum`'a "Model kapısı" satırı eklendi: her otomatik eylem, açık ya da kapalı olduğu ve nedeni.
- Kullanıcının "%90'ın altını karantinaya al" isteğinin uygulanabilir karşılığı bu; doğrulama yüzde değil karar üretiyor (DECISIONS K-72).
- Doğrulama: `test_model_gate` (5 test): yalnız güncel "kullanılabilir" kapıyı açıyor; kısıtlı, kullanılamaz, süresi geçmiş ve raporsuz kapalı; yüksek riskli olmayan model kapıya takılmıyor; `/durum` metni; günlük adım kapalı kapıda kayıt yazmıyor. Önce kırmızı, sonra yeşil.

## v0.99.46 – 04.11.2026 (sinyal kaydı: gerekçe, risk, geçerlilik, BIST 100 karşılaştırması; K-70 madde 4)
- **Defterde yeni alanlar** (eski defterler kendiliğinden yükseltiliyor):
  - `reason`: tetik, göstergeler ve ML olasılığı. Örnek: "dip dönüşü; RSI 31,2; Stoch %K 14,0; …; ML %70".
  - `risk_tl`: stop kart fiyatında gelirse kayıp (lot × fiyat × %2).
  - `valid_until`: girilebilecek son gün; kartta kartın kendi günü.
  - `horizon`: işlemde en çok kaç seans kalınacağı (10).
  - `bench_r`: BIST 100'ün aynı günlerdeki getirisi, giriş açılışından çıkış kapanışına. Bir kez yazılıyor, sonra yeniden hesaplanmıyor.
- **Performans:** Kapanmış sinyaller sayılıyor; kazananlar ve kaybedenler ayrı ortalamayla veriliyor; BIST 100 ortalaması ve fark hesaplanıyor. `/durum`'da "📏 Sinyal performansı" satırı olarak görünüyor.
  - Endeks verisi olmayan işlem varsa karşılaştırma yapılmıyor ve "karşılaştırma yok" yazılıyor; eksik değer sıfır sayılmıyor.
  - Satır küçük örneklem uyarısı taşıyor.
- Doğrulama: `test_signal_record` (7 test): alanlar ve risk elle; eski defter yükseltmesi; iki işlemde kazanan, kaybeden ve BIST 100 elle (%+3,85, %-2,15, endeks %+1,49); `/durum` satırı; boş defter; endeks yoksa sıfır sayılmıyor; `/tara ai` kartı gerekçeyi yazıyor. Önce kırmızı, sonra yeşil.

## v0.99.45 – 04.11.2026 (30.10 eksiğinin nedeni bulundu; eksik kapanış "hafta sonu" diye gizlenmiyor)
- **Kanıt (kullanıcının PC'si, eski klasörün `runs.csv`'si):** 30.10 Cuma 18:30'da PC kapalıydı. 31.10 Cumartesi 01:36'daki gecikmeli çalışma, depoda 30.10 kapanışı yokken `holiday, hafta sonu` yazıp çıktı.
- **Hata:** Rapor "bugün seans var mı" kontrolünü eksik veri kontrolünden önce yapıyordu. Kaçırılan Cuma, Cumartesi günü "hafta sonu" görünüyordu ve dışarıdan izleme alarm vermiyordu.
- **Düzeltme:** Önce beklenen kapanış kontrol ediliyor. Eksikse sonuç "stale" oluyor: "beklenen 30.10.2026 kapanışı, veri 28.10.2026". Bu durumda Healthchecks alarm veriyor. Hafta sonu ya da tatil ancak veri tamsa yazılıyor.
- 30.10 kaydı geri doldurulmadı (K-70). AUDIT bulgu 5 ve 7, kanıtlarıyla güncellendi: Windows görevleri doğrulandı.
- Doğrulama: `test_calendar` (1 yeni test): 31.10 01:36'da 28.10 verisiyle "stale"; 30.10 verisiyle "hafta sonu". Önce kırmızı, sonra yeşil. Rapor, tarama aboneliği ve ikinci kaynak testleri de geçti.

## v0.99.44 – 04.11.2026 (güncelleme kendiliğinden: yeni klasör, git, saatte bir; K-71)
- **Sorun:** Kullanıcı her sürümden sonra elle `git pull` yapıp botu yeniden başlatıyordu. Otomatik güncelleyici `C:\Projeler\QuantBIST` eski klasörüne sabitti ve zip kopyalıyordu; yeni git klasöründe çalışmazdı.
- **Düzeltme (`scripts/guncelle.py`):**
  - Proje, betiğin kendi klasörü.
  - Git deposunda yalnız CI'ı yeşil commit'e ileri sarma yapılıyor. Başka dal ya da yerel değişiklik varsa durup bildiriyor, hiçbir şeyin üzerine yazmıyor.
  - Bot açılmazsa eski commit'e dönülüyor.
  - 18:00–20:00 rapor saatinde beklenip sessiz kalınıyor.
  - Yedek, deneme kopyasında ruff ve testler, paket kilidi kontrolü aynen duruyor.
- **Yeni `scripts/register_update_task.ps1`:** "QuantBIST Guncelle" görevi her gün 07:40'tan itibaren saatte bir, 16 saat çalışıyor. Kullanıcı bunu bir kez kuruyor.
- Doğrulama: `test_guncelle` (8 yeni test): proje klasörü; temiz depo ileri sarılıyor; yerel değişiklik ve başka dal durduruyor; başarısız ileri sarma bildiriliyor; geri alma; rapor saati; görev betiği. Önce kırmızı, sonra yeşil. Windows'a özgü adımlar (görev, robocopy) burada çalıştırılamaz; ilk gerçek kurulum PC'de Telegram mesajıyla görülecek.

## v0.99.43 – 04.11.2026 (yedek hatası ve telafisi Telegram'a bildiriliyor; K-70 madde 2)
- 21:00 yedek kontrolü yedek alamazsa Telegram'a "⚠️ Yedek alınamadı" mesajı gidiyor; mesajda hata ve ne yapılacağı yazıyor. Eskiden yalnız log'a yazılıyordu.
- 18:30 raporu yedeği almamışsa ve bot 21:00'de aldıysa bu da bildiriliyor (dosya adı ve sayısı). Raporun neden çalışmadığına bakmak gerekiyor.
- Yapılacak bir şey yoksa mesaj gitmiyor: rapor yedeği almıştır ya da seans yoktur.
- Raporun kendi yedek hatası zaten rapor mesajında "⚠️ Yedek alınamadı" satırıyla gidiyordu; değişmedi.
- Doğrulama: `test_scheduler` (BackupCatchUpTest, 3 yeni test): hata bildiriliyor, telafi bildiriliyor, yapılacak iş yoksa sessiz. Önce kırmızı, sonra yeşil.

## v0.99.42 – 04.11.2026 (bağımsız ikinci kaynak: elle indirilen dosya; K-70)
- **Talimat:** Kullanıcının 04.11 güvenilirlik talimatı DECISIONS K-70 olarak kaydedildi: yedi madde, kabul ölçütleri ve tamamlanma koşulu. Kullanıcının istediği üç modülün kurallara uygun biçimi de oraya yazıldı.
- **Yeni modül `core/market/second_source.py`:**
  - Kökeni birincil kaynak (Yahoo) olan kaynak reddediliyor; Yahoo'yu Yahoo'yla karşılaştırmak her zaman "%100 doğru" gösterirdi.
  - Onayı ve koşul belgesi olmayan ağ kaynağı hiç çalışmıyor; robots.txt aşılmıyor.
  - Hata olursa yalnız sıradaki bağımsız kaynağa geçiliyor. Hiçbiri yoksa sonuç "ölçülemiyor".
  - İlk kaynak, kullanıcının indirdiği fiyat dosyası: `python -m core.market.second_source --dosya DOSYA.csv --kaynak "…"`. Virgül ya da noktalı virgül ayraç, ondalık virgül ve gün.ay.yıl tarih okunuyor.
  - Karşılaştırma kuralları ve toleransı mevcut `crosscheck.compare` ile aynı, değişmedi.
- **SLO:** "Veri doğruluğu", dosya özetiyle haftalık araştırma özetinden hangisi yeniyse onu kullanıyor ve kaynağı yazıyor. Kapalı ya da eksik özet gerçek bir ölçümün yerine geçmiyor.
- Doğrulama: `test_independent_source` (10 test): birincil kaynak reddi; onaysız ağ kaynağı çalışmıyor; geri düşüş yalnız bağımsız kaynağa; iki dosya biçimi; bozuk dosya reddi; dosyaya konmuş %5'lik fark yakalanıyor; SLO yeni özeti seçiyor; komut özeti yazıyor, Yahoo kökenli dosyayı reddediyor, bozuk hisse kontrolü durdurmuyor. Not: modülün ilk taslağı testten önce yazıldı; SLO bağlantısı önce kırmızı test, sonra kod sırasıyla yapıldı.

## v0.99.41 – 04.11.2026 (güvenilirlik denetimi; model doğrulama sayımı düzeltildi)
- **Denetim:** Kullanıcının 04.11 güvenilirlik talimatına göre `docs/AUDIT.md` "EVRE 1" yazıldı. Her tamamlanma ölçütünün bugünkü durumu kanıtıyla birlikte yazıldı, bulgular önem sırasına kondu, iş sırası belirlendi. Sistem "tam güvenilir" değil; ölçütlerin çoğunda örneklem yetersiz ya da ölçüm yok.
- **Hata 1:** `/durum` "6/11 doğrulandı" diyordu. M15'in raporundaki "## 5. Karar: **kısıtlı kullanılabilir**" satırı okunmuyordu.
- **Hata 2:** MODELS.md'de YÜKSEK olan M30 (ML filtresi) sayıma girmiyordu. Sinyal onay katmanı ve kart kuralı (M31) ile sanal sinyal defteri (M32) envanterde hiç yoktu.
- **Doğru durum:** 14 yüksek riskli modelden 7'si doğrulandı; hepsi "kısıtlı kullanılabilir". Sayı küçüldü, çünkü doğrulanmayan modeller artık gizlenmiyor.
- Doğrulama: `test_model_validation` (3 yeni test): MODELS.md'deki her YÜKSEK satır sayılıyor; depodaki her doğrulama raporu okunuyor; başlık satırındaki karar okunuyor. Önce kırmızı, sonra yeşil.

## v0.99.40 – 04.11.2026 (geri doldurulamayan eski eksik kalıcı uyarı vermiyor)
- **Hata (kendi denetimimden):** `/durum`'daki "Canlı ölçüm kaydı" kontrolü ilk kayıttan bugüne bütün geçmişe bakıyordu. 30.10'un eksik kaydı geri doldurulamadığı için bu satır sonsuza kadar ⚠️ kalacaktı. Böyle bir uyarı yeni sorunları gizler. 03.11'de "7 gün sonra kalkar" demiştim; bu yalnız SLO satırı için doğruydu, bu kontrol için değil.
- **Düzeltme:** SLO'daki gibi yalnız son 7 gündeki kaydı olmayan ya da geç kaydedilen seans ⚠️ veriyor. Daha eski eksik metinde "7 günden eski; geri doldurulamaz, uyarı değil" notuyla görünmeye devam ediyor. Bozuk satır, tekrar kayıt ve boş dosya her zaman uyarıyor.
- Doğrulama: `test_health` (1 yeni test): pencere içindeki eksik uyarıyor, pencere dışındaki uyarmıyor ama yazılıyor. Önce kırmızı, sonra yeşil.

## v0.99.39 – 03.11.2026 (basılmayan kart ertesi gün düşüyor)
- **Hata:** Düğmesine hiç basılmayan `/tara ai` kartı defterde sonsuza kadar "onay bekliyor" kalıyordu ve `/durum`'daki "onay bekleyen kart" sayısı günler geçtikçe büyüyordu. Bu kartlar zaten girilemiyordu, çünkü düğme yalnız kartın günü geçerli (K-67).
- **Düzeltme:** Kartın günü geçince kart "zaman aşımı" oluyor. Bu, ertesi gün düğmeye basılmasıyla aynı sonuç. Defter iki yerde temizleniyor: 18:30 günlük adımında ve yeni bir `/tara ai` kart yazmadan önce. `/durum` yalnız bugünün bekleyen kartlarını sayıyor.
- Doğrulama: `test_control` (2 yeni test): dünkü kart düşüyor, bugünkü kalıyor, sayı 1; ikinci temizlik bir şey yapmıyor; günlük adım eski kartı düşürüyor. Önce kırmızı, sonra yeşil.

## v0.99.38 – 03.11.2026 (belgeler eksiksiz: K-68 sonucu, K-69, yol haritası)
- Bugünkü işlerin belge denetimi yapıldı; bulunan altı eksik kapatıldı.
  - DECISIONS: K-68'e sonuç eklendi (GEÇMEDİ, Actions 41716706686).
  - DECISIONS: Yeni karar K-69: sürekli açık bot raporun kaçırdığı işleri telafi ediyor (arka plan `/tara ai`, saatlik kur, 21:00 yedek, süreç başına geçici dosya).
  - DECISIONS: Kur önbelleği notu güncellendi.
  - ROADMAP: "Kaldığım yer" 03.11 durumuna getirildi; tarihli açık işler yazıldı: 03.02.2027 ileri test, Kasım sonu K-36 kararı, Aralık'ta tatil teyidi. Ö29'un durumu güncellendi.
  - HANDBOOK: "Card rule study" iş akışı zaman çizelgesine eklendi.
- Kod değişmedi.

## v0.99.37 – 03.11.2026 (K-68 sonucu: kartın kuralı geçmedi, kart bunu söylüyor)
- **Ölçüm (Actions 41716706686):** 207 tetik, 30 hisse. Ortalama net %+0,10, rastgele seanslarda %-0,09; fark %+0,19, %95 aralık %-0,25 – %+0,61. Hedef %26, stop %74, süre dolumu %0. GEÇMEDİ: tetik günleri rastgele girişten ayırt edilemiyor. Ayrıntı RESEARCH_LOG'da.
- `/tara ai` kartına yeni satır eklendi: "Kartın kuralı geçmişte (K-68): 207 tetikte hedef %26, stop %74; ortalama net %+0,10, rastgele seanslar %-0,09 (…; rastgele girişten ayırt edilemedi)". Bilgisayarda daha yeni bir `logs/card_study.json` varsa satır onu gösteriyor.
- Kural, stop, hedef ve eşik değiştirilmedi (K-68).
- Doğrulama: `test_control` (1 yeni test) kayıtlı sonucun kartta göründüğünü sınıyor. Önce kırmızı, sonra yeşil.

## v0.99.36 – 03.11.2026 (kartın kendi kuralı ölçülüyor, K-68)
- Kartın önerdiği kural hiç ölçülmemişti: dip dönüşü tetiği, ertesi açılışta giriş, %2 iz süren stop, %4 kâr al, en çok 10 seans. Ölçüm kuralı ölçümden önce DECISIONS K-68'e yazıldı.
- Modül `core/analytics/card_study.py`: sanal defterin takip fonksiyonunu birebir kullanıyor. Tetik olaylarını aynı hisselerin bütün seanslarından girilen aynı kuralla karşılaştırıyor; aralık gün blok bootstrap ile hesaplanıyor. Holdout okunmuyor.
- GitHub Actions'ta yeni iş akışı: "Card rule study" (`card-study.yml`, elle başlatılıyor).
- Doğrulama: `test_card_study` (6 test): elle hesaplanmış bir iz süren stop işlemi; açık kalan son satırlar dışarıda kalıyor; olaylar arası 10 seans boşluk; rastgele yürüyüş geçmiyor; holdout okunmuyor; az olayda doğru gerekçe.

## v0.99.35 – 03.11.2026 (kart, modelin gerçek geçmiş isabetini yazıyor)
- `/tara ai` kartı eskiden yalnız "model geçmedi" diyordu. Artık ✅'e basmadan önce ölçülen rakamı da gösteriyor. Örnek: "Geçmiş ölçüm: onaylanan 42 sinyalde isabet %26,2, tüm tetiklerde %33,6 (onay isabeti artırmadı; isabet: 10 seans sonra kapanış ≥ +%3; BIST 100, örneklem dışı, K-64, Actions 41645852277)".
- Kaynak: Bilgisayarda daha yeni bir örneklem dışı rapor (`logs/signal_filter_gunluk.json`) varsa o kullanılıyor. Yoksa RESEARCH_LOG'a yazılmış K-64 sonucu kullanılıyor; ölçüm GitHub Actions'ta yapıldığı için bilgisayarda genelde rapor yok. Rakam ya da eşik değiştirilmedi.
- Not: Ölçümdeki isabet tanımı (10 seans sonra ≥ +%3) kartın %2 stop / %4 hedef kuralıyla aynı değil; kart bunu açıkça yazıyor.
- Doğrulama: `test_control` (2 yeni test): kayıtlı rakamlar kartta görünüyor; daha yeni bir rapor varsa onun yerine geçiyor ve "artırmadı" ifadesi kalkıyor. Önce kırmızı, sonra yeşil.

## v0.99.34 – 03.11.2026 (iki süreç aynı geçici dosyayı paylaşmıyor)
- Bulgu (kendi incelememden): v0.99.32–33 ile bot da kur önbelleğine ve yedeğe yazıyor. Bot ile 18:30 raporu iki ayrı süreç ve ikisi aynı `….tmp` dosyasını kullanıyordu. Aynı anda yazarlarsa biri ötekinin yarım dosyasını yerine koyabilir, Windows'ta da yazma hata verebilirdi.
- Düzeltme: Altı atomik kayıt noktası artık süreç numarasıyla ayrı bir geçici dosya kullanıyor (`usdtry.<pid>.tmp`): kur önbelleği, yedek, sanal emirler, tarama abonelikleri, kart önbelleği ve rapor durumu. `.gitignore` her `*.tmp` dosyasını dışarıda tutuyor.
- Doğrulama: `test_macro` (TwoWritersTest): geçici dosya süreç numarasını taşıyor, kayıttan sonra geride kalmıyor. Önce kırmızı, sonra yeşil. İlgili 259 test yeniden geçti.

## v0.99.33 – 03.11.2026 (yedeği rapor almazsa bot alıyor)
- 02.11'de yedek yoktu, çünkü o gün 18:30 raporu çalışmamıştı. Artık sürekli açık olan bot her seans günü 21:00'de bakıyor: günün yedeği (`quantbist_YYYY-AA-GG.zip`) yoksa kendisi alıyor. Rapor yedeği zaten aldıysa hiçbir şey yapmıyor. Tatil günlerinde de bir şey yapmıyor.
- Hata botu durdurmuyor, log'a yazılıyor. Eksik gün `/durum`'un Yedek SLO'sunda görünmeye devam ediyor.
- Doğrulama: `test_scheduler` (BackupCatchUpTest): eksik yedek alınıyor; var olana dokunulmuyor; 29.10 (bayram) atlanıyor; iş kaydediliyor ve hatada sessiz kalıyor. Önce kırmızı, sonra yeşil.

## v0.99.32 – 03.11.2026 (kuru bot saatlik tazeliyor)
- Kur artık yalnız 18:30 raporuna bağlı değil. Sürekli açık olan bot saatte bir, önbellekte eksik olan son iki haftanın TCMB bültenlerini soruyor (en çok 10 istek, 30 sn). Önbellek tamsa hiç istek atmıyor. Rapor bir akşam kuru alamazsa bir saat içinde telafi ediliyor (03.11: kur 23.10'da kalmıştı).
- Günün bülteni 16:00'dan önce sorulmuyor. TCMB bülteni ~15:30'da yayımlıyor; daha önce gelen 404 "o gün bülten yok" diye kalıcı kaydedilirdi.
- Hata botu durdurmuyor, yalnız log'a ve `logs/usd_fetch.json`'a yazılıyor.
- Doğrulama: `test_macro` (RefreshTest): 14:00'te bitiş dün, 16:00'da bugün; hata 0 döndürüyor. `test_scheduler` (MacroRefreshTest): iş saatlik kaydediliyor ve tazelemeyi çağırıyor. Önce kırmızı, sonra yeşil.

## v0.99.31 – 03.11.2026 (kur neden eski kaldı, /durum söylüyor)
- **Sorun:** `/durum` kuru 23.10.2026'da takılı gösterdi ama nedenini söylemedi. TCMB bülteni çekilirken bağlantı hatası, HTTP hatası ve okunamayan dosya sessizce atlanıyordu.
- **Teşhis:** Her bülten çekişi `logs/usd_fetch.json`'a yazılıyor: kaç bülten soruldu, kaçı eklendi, kalanı neden olmadı (bağlantı hatası, HTTP kodu, bülten okunamadı, bülten tarihi farklı). Sorun olursa log'a da uyarı düşüyor.
  - Kur 5 günden eskiyse `/durum`'un Makro veri satırı son denemeyi ve son 14 günde boş kaydedilen günleri gösteriyor. Kur güncelse bu ayrıntı yazılmıyor.
- **Onarım komutu:** `python -m core.market.macro --usd 2026-10-20 --yeniden`. Boş kaydedilmiş günleri unutup yeniden soruyor, sonra durumu yazıyor.
- Doğrulama: `test_macro` (FetchReasonTest, 5 yeni test): dört ayrı hata türü sayılıyor; hafta sonu istek yoksa dosya yazılmıyor; eski kurda neden yazılıyor, güncel kurda yazılmıyor; `--yeniden` yalnız boş günleri siliyor. Önce kırmızı, sonra yeşil.

## v0.99.30 – 03.11.2026 (/panik artık /tara ai'yi beklemiyor)
- **Hata:** 03.11.2026 22:48'de `/tara ai` modelini eğitirken gönderilen `/panik` ve `/devam` iki dakika cevapsız kaldı. Bot komutları sırayla işliyor; uzun tarama acil durdurmayı arkasında bekletiyordu.
- **Düzeltme:** `/tara ai` artık arka planda çalışıyor; komut hemen dönüyor, sonuç bitince geliyor. Bu arada `/panik`, `/durum` ve diğer komutlar anında cevaplanıyor.
  - Panik tarama sürerken basılırsa, tarama sonunda kart deftere yazılmıyor (kilit `add`'i reddediyor), düğmeler de "kilitli" diyor.
  - İkinci bir `/tara ai` ilki bitmeden gelirse model iki kez eğitilmiyor: "önceki hâlâ çalışıyor" cevabı veriliyor.
- `/durum`'daki boş defter satırı güncellendi: sistem kendiliğinden sinyal yazmıyor, `/tara ai` kartındaki ✅ ile kullanıcı giriyor.
- Doğrulama: `test_control` (ResponsivenessTest): tarama bitmeden `/panik` cevaplanıyor; ikinci `/tara ai` bekletiliyor, model bir kez çağrılıyor. Önce kırmızı, sonra yeşil.

## v0.99.29 – 03.11.2026 (v3.0: butonla onay, %1 risk lotu, iz süren stop)
- **Manuel onay odası (K-67):** `/tara ai`'nin %60 üstü kartlarının altında [✅ İşleme Gir] ve [❌ İptal Et] düğmeleri var.
  - Basılana kadar pozisyon açılmaz; kart defterde "onay bekliyor" olarak durur.
  - İşleme Gir: ertesi seans açılışında sanal giriş, takip başlar; düğmeler kalkar ve sonuç yazılır.
  - İptal Et: kart atılır. Ertesi gün basılırsa "süresi doldu".
  - Düğmeler kullanıcı kimliği listesinden geçer; panik ya da şalter açıkken işlem açmaz.
- **%1 risk kalkanı:** Kartta lot sayısı ve toplam maliyet var. Lot = kasa × %1 ÷ (fiyat × %2), boş nakitle sınırlı. Kart, pozisyonun kasadaki payını ve boşluklu açılış riskini yazıyor.
- **İz süren stop:** Stop, zirvenin %2 altını yalnız yukarı yönde izliyor; bir mumun kendi yükseği o mumun stopunu yükseltmiyor.
  - `/durum` zirveyi, güncel stopu, stop gelirse sonucu ve toplam dinamik riski gösteriyor.
- **Panik:** Onay bekleyen kartları da iptal ediyor.
- Eski defter dosyaları yeni sütunlarla (lot, zirve) otomatik yükseltiliyor.
- Doğrulama: `test_control` (ApprovalTest, 7 yeni test):
  - elle lot: 105.430 TL, 250 TL → 210 lot;
  - nakit sınırı;
  - giriş, iptal, süre dolumu, kilit ve tek seferlik karar;
  - iz süren stop elle (zirve 103,9 → stop 101,82, kâr kilitlendi);
  - eski defter yükseltmesi;
  - başka kullanıcının düğmesi yok sayılıyor.

## v0.99.28 – 03.11.2026 (çift yönlü yönetim)
- **Kullanıcı kimliği listesi:** Komutlar ve `/tara` düğmeleri yalnız `.env`'deki CHAT_ID sohbetinden ve USER_ID kullanıcısından gelirse işleniyor. USER_ID boşsa CHAT_ID kullanılıyor; özel sohbette ikisi aynı.
- **`/panik`:** Açık ve bekleyen sanal sinyalleri iptal ediyor ve sistemi kilitliyor: saatlik takip, günlük sinyal adımı, tarama abonelikleri, yeni sinyal ve `/tara` duruyor. Kilit dosyada, yeniden başlatmada sürüyor. **`/devam`** kilidi kaldırıyor.
- **`/durum`:** Sanal kasa (gerçekleşmiş + açık pozisyonlar), her açık sinyalin anlık kâr/zararı, stop ve hedefi, panik ve şalter durumu.
- **`/tara ai`:** BIST 30'da teknik tetik → AI onay katmanı.
  - Olasılık ≥ %60: zengin mesaj (teknik durum, güven skoru, giriş bölgesi, %2 stop, %4 kâr al).
  - Altı: "AI Reddi: olasılık %X".
  - Katman doğrulanmadığı için (K-64) mesajlar "bilgi amaçlı" etiketli; deftere sinyal yazılmıyor.
  - Model ilk kullanımda eğitiliyor, her Cuma yeniden eğitiliyor.
- Doğrulama: `test_control` (8 test) ve kullanıcı kimliği testleri:
  - başka kullanıcının düğmesi yok sayılıyor;
  - panik iptal ediyor, kilitliyor, `/devam` açıyor;
  - kasa elle hesapla aynı: giriş 100 → 102,50 = +250 TL;
  - onay ve ret mesajları; doğrulanmamışken deftere yazılmıyor.

## v0.99.27 – 03.11.2026 (sinyal onay katmanı ölçüldü: geçmedi)
- **Günlük BIST 100:** accuracy %62,4 (her şeye "hayır" diyen model %66,4).
  - Onaylanan 42 sinyalin isabeti %26,2, taban %33,6; tabandan kötü.
- **Saatlik BIST 30:** accuracy %74,5 ("hep hayır" %76,4).
  - Onaylanan 39 sinyalin isabeti %41,0, taban %23,6.
  - Umut verici ama örnek, önceden yazılan 50'nin altında.
- Katman bota bağlanmadı; eşikler değiştirilmedi. Saatlik kural 02.11.2026 sonrası yeni veride ileri test olarak yeniden ölçülecek (en erken 03.02.2027). Ayrıntı: RESEARCH_LOG.

## v0.99.26 – 03.11.2026 (sinyal defteri: seans içi takip ve kilitlenen şalter)
- **Seans içi takip** (`core/signals/live.py`): Bot işlem günlerinde 10:00–19:00 arası her saat açık sinyallerin hisselerini saatlik mumlarla denetliyor. Giriş, hedef ve stop olunca Telegram'a yazıyor. Seans sonunda günlük mumlarla tekrar denetleniyor; süre dolumu orada kapanıyor.
- **Şalterin yeni tanımı (K-65):** O gün kapanan sanal işlemlerin net zararı defterin %6'sına ulaşırsa bot o gün kendini kilitliyor; `/tara`, tarama abonelikleri ve yeni sinyal reddediliyor. Ertesi gün kilit kalkıyor.
  - Önceki tanım (açık pozisyonlar dahil defter değerindeki düşüş) kaldırıldı.
  - Şalter açıldığında Telegram'a bir kez haber veriliyor.
- **Hata dayanımı:** Bir hissenin bozuk verisi diğerlerinin takibini durdurmuyor; ağ hatası loglanıp bir sonraki saatte yeniden deneniyor. Defter dosyası yoksa hiçbir şey oluşturulmuyor.
- Doğrulama: `test_signal_book` (18 test, elle hesaplanmış):
  - iki pozisyonun %70'e boşlukla düşmesi −%6,03 ile kilidi açıyor; tek normal stop (−%0,215) açmıyor; açık zarar sayılmıyor;
  - seans içinde hedef saat saat bulunuyor; saatlik veri süre dolumu yapmıyor;
  - şalter mesajı bir kez geliyor; kilit ertesi gün kalkıyor;
  - `/tara` kilitliyken reddediliyor.

## v0.99.25 – 03.11.2026 (sinyal onay katmanı: meta-etiketleme)
- **Yeni: `core/ml/signal_filter.py`** (K-64; kural ölçümden önce yazıldı).
  - Teknik tetik ("dip dönüşü") bir aday sinyal üretiyor; RandomForest bu sinyalin başarı olasılığını veriyor.
  - Olasılık ≥ 0,60 ise "onaylandı", altındaysa "yalancı sinyal".
- **Öznitelikler:** RSI, ADX, Stochastic, MACD histogramı, Bollinger %b, ATR oranı, CMF, EMA 50/200'e yüzde uzaklık ve hacim anomalisi (o mumun hacmi ÷ önceki 5 mumun ortalaması).
- **Sızıntı yok:**
  - öznitelikler yalnız o mum ve öncesinden;
  - eğitim satırının etiketi, test edildiği ilk olaydan önce bilinmiş olmalı (dış değerlendirmede de ayar aramasında da);
  - 02.11.2026 sonrası kullanılmıyor.
- **Ezberleme denetimi:** `max_depth` {3, 4, 5} ve `min_samples_leaf` {10, 25, 50} yalnız eğitim verisi içinde, zaman sıralı çapraz doğrulamayla (log-loss) seçiliyor.
- **Rapor:** `python -m core.ml.signal_filter --zaman gunluk|saatlik` doğruluğu (accuracy) yazıyor; yanında taban oran ve onaylanan sinyallerin isabeti de var.
- Gerçek veriyle ölçüm iki iş akışında: günlük BIST 100 ("Screen templates explain") ve saatlik BIST 30 ("Hourly data check").
- Doğrulama: `test_signal_filter` (7 test):
  - elle hesaplanmış etiket ve hacim anomalisi;
  - geleceğe bakmama;
  - temizlenmiş katlar ve holdout;
  - ayarların ızgaradan seçilmesi;
  - 0,60 karar sınırı;
  - rastgele veride geçmeme ve doğruluğun ekrana basılması.

## v0.99.24 – 03.11.2026 (dip dönüşü ölçüldü: geçmedi)
- **Gerçek veride ölçüm** (BIST 30, 1 yıl saatlik, 30/30 hisse): 576 olay.
  - 16 mum sonra ortalama −%0,22; rastgele saatlerde −%0,19.
  - Fark −%0,02 (%95 aralık −%0,61 … +%0,55); kazançlı olay %48.
- Tetik bota bağlanmadı (K-63); eşikler değiştirilmedi. Ayrıntı: RESEARCH_LOG.

## v0.99.23 – 03.11.2026 (dip dönüşü tetiğinin ölçümü)
- **Yeni: `core/analytics/dip_study.py`.** Kural ölçümden önce yazıldı (K-63).
  - Olay: tetiğin oluştuğu saatin kapanışı; aynı hissede 16 mum içinde gelen yeni tetik ayrı olay sayılmıyor.
  - Sonuç: ertesi saat açılışında giriş, 16 mum sonra çıkış, maliyet düşülü.
  - Karşılaştırma: aynı hisselerin tüm saatlerinden aynı kuralla girişler.
  - %95 aralığı gün blok bootstrap ile. 02.11.2026 sonrası kullanılmıyor.
- "Hourly data check" iş akışı ölçümü de çalıştırıyor.
- Doğrulama: `test_dip_study` (7 test):
  - elle hesaplanmış getiri;
  - olay ayıklama kuralı;
  - rastgele veride geçmiyor; gömülü gerçek etkiyi buluyor;
  - holdout kesiliyor.

## v0.99.22 – 03.11.2026 (BIST 30 kodları düzeltildi, saatlik veride tek tek yeniden deneme)
- **Listede iki kod düzeltildi** (gerçek Yahoo verisiyle denendi, Actions 41637982348):
  - EKOY.IS → **EKGYO.IS** (Emlak Konut): EKOY Yahoo'da yok.
  - KOZAL.IS → **TRALT.IS** (Koza Altın'ın güncel kodu, verisi 24.11.2025'te başlıyor): KOZAL artık veri döndürmüyor.
- **Saatlik indirici:** Toplu istekte boş dönen hisseyi bir kez tek başına yeniden istiyor. ISCTR.IS 30'luk istekte boş dönmüş, tek başına istenince tam gelmişti.
- Doğrulama: `test_a_ticker_empty_in_the_batch_is_asked_alone` (önce kırmızıydı).

## v0.99.21 – 03.11.2026 (iki gerçek veri sonucu)
- **ML ikinci kural (goreli20) ölçüldü: filtre kapalı.**
  - Yaklaşık BIST 30: isabet %45,9, taban %44,6.
  - BIST 100: isabet %45,0, taban %41,7.
  - BIST 100'de model her yıl tabanın biraz üstünde, ama fark güven aralığı içinde. Eşik değiştirilmedi. Ayrıntı: RESEARCH_LOG.
- **Saatlik veri gerçek Yahoo'da denendi.**
  - 27/30 hisse geldi (57.023 mum).
  - EKOY.IS ve KOZAL.IS için Yahoo "veri yok" diyor; ISCTR.IS'den kullanılabilir mum gelmedi.
  - "Hourly data check" iş akışına hisse girişi ve verisi gelmeyen hisse için ham veri tanısı eklendi.

## v0.99.20 – 03.11.2026 (BIST 30 listesi, saatlik veri, genişletilmiş göstergeler)
- **BIST 30 listesi** `core/config/bist30.py` ve `data/bist30.csv` dosyalarında (kullanıcının verdiği 30 hisse). `/tara evren=bist30` artık çalışıyor. EKOY.IS Yahoo'da bulunmayabilir (EKGYO kastedilmiş olabilir); indirici verisi gelmeyen hisseyi adıyla raporluyor.
- **Saatlik veri: `core/market/hourly.py`.**
  - 30 hissenin son 1 yılı tek toplu yfinance isteğiyle indiriliyor; ağ hatasında 3 kez yeniden deneniyor.
  - Temizlik: NaN, sıfır ya da eksi fiyat, yüksek < düşük ve tekrar eden saatler atılıyor. Saat İstanbul'a çevriliyor. Henüz kapanmamış son saat atılıyor.
- **Genişletilmiş göstergeler: `core/market/extended.py`.** Her zaman dilimindeki fiyat tablosuna uygulanabiliyor; `ta` kütüphanesiyle vektörel.
  - EMA 50/200 ve fiyata uzaklıkları, ADX(14), RSI(14), yavaş Stochastic (14, 3, 3), MACD, Bollinger (20, 2) ve %b, ATR(14), CMF(20), OBV.
- **"Dip dönüşü" tetiği:** (RSI < 35 veya Stoch %K < 20) ve Bollinger %b ≤ 0,10 ve MACD histogramı sıfırın altında yükseliyor. Kural çıktısıdır; henüz ölçülmedi.
- **"Hourly data check" iş akışı:** gerçek Yahoo verisiyle indirme ve tarama.
- Doğrulama: `tests/test_data.py` (10 test, ağsız):
  - liste ve CSV aynı;
  - temizlik kuralları ve İstanbul saati;
  - tek toplu istek, yeniden deneme, verisi gelmeyen hissenin raporlanması;
  - göstergeler elle hesap ve kütüphaneyle aynı; geleceğe bakmıyor;
  - tetiğin doğruluk tablosu.

## v0.99.19 – 03.11.2026 (ML filtresi, ikinci kural: goreli20)
- **Yeni kural, ölçümden önce yazıldı (K-62).** Soru: "Hisse, ertesi açılıştan 20. seans kapanışına kadar, maliyetten sonra XU100'ü geçer mi?"
  - Öznitelikler ve model ilk kuralla aynı.
- **Daha dürüst ölçüm.**
  - Test günleri 20 seans arayla seçiliyor; aynı hissenin test etiketleri üst üste binmiyor.
  - İsabetin %95 aralığı, test tarihleri yeniden örneklenerek hesaplanıyor (aynı gün birlikte hareket eden hisseler bağımsız sayılmıyor).
- `python -m core.ml.ml_filter --rule goreli20`; sonuç `logs/ml_report_goreli20.json`. Canlı filtre ve sanal defter ilk kurala bağlı kalıyor; bu kural geçerse bağlama ayrı adım.
- Doğrulama:
  - elle hesaplanmış etiket: +%10'a karşı XU100 +%8 → 1; XU100 +%10 → maliyet yüzünden 0;
  - tavan açılış;
  - 20 seans aralıklı test günleri;
  - bootstrap aralığı Wilson aralığından dar değil;
  - rastgele veride filtre kapalı.

## v0.99.18 – 03.11.2026 (PC kurulumunda bulunan üç hata)
- **Testler gerçek `data\signals.db` dosyasını oluşturuyordu.** PC'deki kurulumun yazma denetimi yakaladı. Günlük defter adımı, ML filtresi kapalıyken ve defter henüz yokken artık dosya oluşturmuyor.
- **`cloudpickle` kilit dosyasına eklendi.** joblib'in bağımlılığı; kurulum "paketler farklı" diyordu.
- **Sürüm numarası düzeltildi.** v0.99.4'ten beri v0.99.3'te kalmıştı. `/durum` artık gerçek sürümü gösteriyor.
- Doğrulama: `test_no_book_is_created_while_the_filter_is_off` (önce kırmızıydı); tüm testlerden sonra `data/` içinde veritabanı yok.

## v0.99.17 – 03.11.2026 (temiz kurulum betiği)
- **Yeni: `scripts/yeni_kurulum.ps1`.** Güncel sürümü eski klasörün yanına, yeni bir klasöre kurar.
  - `.env` dosyasını ve `data\` içindeki kişisel dosyaları (izleme listesi, defter, sanal emirler, `market.db`) kopyalar; sürümdeki dosyaların üzerine eski kopya yazmaz.
  - `setup.ps1` ile ortamı kurar ve testleri çalıştırır.
  - Eski klasörü yalnız okur: hiçbir şeyi silmez, durdurmaz, değiştirmez. Hedef klasör varsa durur.
- Doğrulama: `test_install_script`. Silme/durdurma komutu yok; yalnız eksik dosyalar kopyalanıyor; gizli bilgi yok; Windows PowerShell 5.1 için yalnız ASCII.

## v0.99.16 – 03.11.2026 (ML filtresinin ilk gerçek ölçümü)
- **Sonuç: ML filtresi kapalı.** Gerçek veride, eğitimde görülmemiş 2023–2026 yıllarında ölçüldü:
  - yaklaşık BIST 30: isabet %34,0, tüm girişlerde hedefe ulaşma %33,8;
  - BIST 100: isabet %34,2, taban %33,4.
  - Model rastgele girişten ayırt edilemiyor; %60 eşiğinin çok uzağında. Ayrıntı: docs/RESEARCH_LOG.md.
- Kapalı filtrenin neden metni Türkçe ondalıkla yazılıyor (%34,0).

## v0.99.15 – 03.11.2026 (BIST 30 hedefi, adım 4: Telegram bağlantısı)
- **`/tara ... ml=evet`.** Eşleşmelerden yalnız ML filtresinin geçirdiklerini listeler; her satıra olasılığı ekler.
  - Filtre örneklem dışı testi geçmediyse liste boş kalır ve nedeni yazılır. Örnek: "ML filtresi kapalı (isabet %52,0 < eşik %60)".
  - `ml=` yazılmazsa `/tara` eskisi gibi çalışır.
- **`/durum`a sanal sinyal defteri ve ML filtresinin durumu eklendi.** Defter değeri, açık ve kapanan sinyaller, hedefe ulaşma oranı ve şalter görünüyor.
- **Günlük çalışma, rapordan sonra:**
  - açık sinyalleri kesin mumlarla izliyor;
  - %6 şalteri denetliyor;
  - filtre açıksa yaklaşık BIST 30'un o günkü sinyallerini deftere yazıyor;
  - modeli Cuma günleri (ya da model dosyası yoksa) bilinen tüm etiketlerle yeniden eğitiyor.
- Doğrulama: `ml=evet` ayrıştırması, kapalı filtrede boş liste ve neden, açık filtrede eleme, üç günlük defter akışı, `/durum` satırları, canlı modelin yalnız bilinen etiketlerle eğitilmesi.

## v0.99.14 – 03.11.2026 (BIST 30 hedefi, adım 3: sanal sinyal defteri)
- **Yeni: `core/signals/store.py`.** Sinyaller SQLite'a (`data/signals.db`) yazılıyor ve fiyatlarla izleniyor.
  - Durumlar: bekliyor → açık → hedef / stop / süre doldu; tavan açılışta "dolmadı".
  - Kurallar ML etiketleriyle aynı (K-60). Sanal bakiye 100.000 TL, sinyal başına 10.000 TL.
- **Şalter:** Defter bir seansta %6 veya daha fazla düşerse o kapanışın sinyalleri kaydedilmiyor.
- **Defter değeri:** Her kapanışta kapanan sonuçlar ve açık pozisyonların o günkü değeri.
- Defter dosyası kişisel: depoya girmiyor, günlük yedeğe giriyor.
- Doğrulama: `test_signal_book` (6 test, elle hesaplanmış):
  - hedef;
  - boşlukla stop;
  - süre dolumu;
  - tavan açılış;
  - iki pozisyonun %30 düşüşünde defterin tam −%6 düşmesi ve şalterin o günü kapatıp ertesi günü açması.

## v0.99.13 – 03.11.2026 (BIST 30 hedefi, adım 2: ML filtresi)
- **Yeni: `core/ml/`.** RandomForest filtresi, şu kuralın hedefe önce ulaşıp ulaşmayacağını tahmin ediyor: "ertesi açılışta giriş, %2 stop, %4 hedef, en çok 10 seans".
  - Öznitelikler: EMA 50/200 mesafeleri, hacim anomalisi (önceki 20 seansa göre z-puanı), RSI, ADX, ATR, Bollinger %b, CMF, Stochastic, OBV eğimi, oynaklık, 5 ve 20 günlük getiri.
  - Ölçüm yalnız eğitimde görülmemiş yıllarda yapılıyor. Eğitim etiketi test yılından önce bilinmiş olmalı; 02.11.2026 sonrası hiç kullanılmıyor.
  - Filtre ancak şu üç koşulla açılıyor: en az 100 sinyal, isabet ≥ %60 ve isabet "zaten hedefe ulaşanlar" oranından anlamlı yüksek (K-59). Aksi halde kapalı kalıyor ve nedeni yazılıyor.
- Gerçek veriyle ölçüm GitHub Actions'taki "Screen templates explain" iş akışında. Sonuç `logs/ml_report.json` dosyasına yazılıyor.
- scikit-learn bağımlılığı eklendi (requirements.lock'ta sabit sürüm).
- Doğrulama: `test_ml_filter` (10 test):
  - elle hesaplanmış etiketler: hedef, stop, aynı gün ikisi, boşlukla stop, süre dolumu, tavan açılış;
  - gelecek değişince geçmiş öznitelikler değişmiyor;
  - eğitimde test yılına ait etiket yok; holdout'a dokunulmuyor;
  - rastgele veride filtre kapalı kalıyor; gömülü gerçek örüntüyü buluyor.

## v0.99.12 – 03.11.2026 (BIST 30 hedefi, adım 1: göstergeler)
- **`/tara` için yeni alan: `cmf`.** Chaikin para akışı (20 gün), −100 ile +100 arası. Örnek: `/tara cmf>10 adx>25 evren=bist30`.
- İstenen diğer göstergeler zaten vardı ve testliydi: EMA 50/200 (`ema50`, `ema200`), ADX(14) (`adx`), Stochastic (`stok_k`, `stok_d`), Bollinger (`bb_ust`, `bb_alt`, `bb_yuzde`, `bb_genislik`), ATR (`atr`, `atr_yuzde`), OBV (`obv_egim`).
- pandas-ta eklenmedi: numpy 2 ile açılmıyor. Proje zaten bakımı süren `ta` kütüphanesini kullanıyor.
- Doğrulama: `test_cmf_by_hand`. Elle hesap ve `ta` kütüphanesiyle aynı; düz mum akış eklemiyor.

## v0.99.11 – 29.10.2026 (bağımsız doğrulama M24: TÜFE penceresi)
- **M24 (dört bazlı sonuç) değişti; yeniden doğrulama gerekir.**
- **Reel getirinin başlangıcı düzeltildi** (ORTA). Başlangıç artık başlangıç ayından önceki ayın sonu. Önceden başlangıç gününde açıklanmış son ay alınıyordu. Örnek: 03.01.2022'de başlayan pencereye Aralık 2021'in %13,58'i giriyordu, reel 10,8 puan düşük çıkıyordu. Bitiş eskisi gibi; açıklanmamış ay tahmin edilmez.
- **Pencerede yeni TÜFE yoksa artık "dönemde yeni TÜFE yayımlanmadı" yazıyor** (ORTA). Önceden reel = nominal bir sayı olarak gösteriliyordu.
- Eski davranışı sabitleyen iki test yeni davranışa göre güncellendi.

## v0.99.10 – 29.10.2026 (bağımsız doğrulama M12: stres testi; M24 raporu)
- **M12 (portföy riski) değişti; yeniden doğrulama gerekir.**
- **Stres pencereleri artık seans sayıyor, satır değil** (ORTA).
  - XU100 verisinde boşluk varsa daha uzun bir düşüş "1 seans" gibi görünüyordu. Doğrulamadaki örnek: 19.01 → 29.01, −%20.
  - Eksik veriye denk gelen pencere atlanıyor, sıradaki en kötü tam pencere alınıyor.
  - Tatiller sayılmıyor. Tatil dosyasının kapsadığı yıllarda (2026–2027) seans sayısı tam tutmalı; daha eski yıllarda bir bayram uzunluğu (5 iş günü) pay var.
- **Fiyatı olmayan pozisyon artık stres testinde adıyla yazılıyor** (ORTA). Önceden sessizce düşüyordu.
- **M24 (dört bazlı sonuç) bağımsız doğrulaması:** kısıtlı kullanılabilir (docs/validation/M24.md).
  - 11 elle hesaplanmış durum kodla aynı.
  - TÜFE dosyası kendi içinde tutarlı: 57 ayda 12 aylık zincir ile yıllık arasındaki en büyük fark 0,03 puan.
  - YÜKSEK bulgu yok. ORTA: TÜFE penceresi gerçek pencereden yaklaşık bir ay geride; kısa pencerede reel = nominal bir sayı gibi gösteriliyor.
- Doğrulama: `test_stress_validation` (3 test, önce kırmızıydı).

## v0.99.9 – 29.10.2026 (bağımsız doğrulama M16: ±%10 içindeki hatalar)
- **M16 (veri kalitesi) değişti; yeniden doğrulama gerekir.**
- **Mumun kendi içinden üç yeni kontrol** (YÜKSEK bulgu: ikinci kaynak kapalıyken ±%10 içindeki hatalar görünmüyordu).
  - Açılış artık yüksek–düşük aralığında mı diye denetleniyor; dışındaysa "hatalı OHLC".
  - Düz mum (açılış = yüksek = düşük = kapanış, işlem var; BERA 27.06.2022 türü) listeleniyor.
  - Ertesi gün açılışı önceki kapanışa geri dönen tek günlük mum listeleniyor. Kural: girişte ve çıkışta en az %3 boşluk, ters yönde, geri dönüş %1,5 içinde. ×1,05 tek günlük hata bu türden.
  - Liste bilgi amaçlı; hisse dışlanmıyor, çünkü gerçek hareketi hatalı olandan ayırmak ikinci kaynak ister. Backtest dışlaması değişmedi (yalnız ±%20 sıçramalar).
- Test yardımcısı `make_ohlcv` artık açılışı aralık içinde üretiyor. Önceki hali gerçekte olamayacak mumlar üretiyordu; rastgele çekiliş sırası korundu, bütün testler aynı sonucu veriyor.
- Doğrulama: `test_candle_integrity` (6 test, önce kırmızıydı). Temiz seride liste boş; kalıcı +%5 hareket listelenmiyor.

## v0.99.8 – 29.10.2026 (bağımsız doğrulama M28: /risk denge; M16 raporu)
- **M28 (risk bütçesi) değişti; yeniden doğrulama gerekir.**
- **`/risk denge` gerçek hesapta artık sınıra gerçekten döndürüyor** (YÜKSEK).
  - Gerçek hesabın değeri yalnız hisselerden oluşuyor, satış toplamı da küçültüyor. Hesap artık küçülen toplama göre çözülüyor ve her ağırlık sınıra inene kadar tekrarlanıyor. Doğrulamadaki örnek: %46,3 eskiden %42,7'ye iniyordu, artık %40'ın altına iniyor.
  - Her azaltmadan sonra hesap yeniden ölçülüyor ve "azaltma sonrası" satırı yazılıyor.
  - Satışla ulaşılamayan sınır hesaplanmıyor, nedeniyle söyleniyor:
    - gerçek hesapta oynaklık ve 1 günlük kayıp (nakit yok, eşit azaltma oranı değiştirmez);
    - hisse sayısı yetmediğinde tek hisse sınırı (2 hisseyle en büyük pay en az %50);
    - zirveden düşüş (gerçekleşmiş kayıp).
- **Ölçülemeyen sınır artık "sınırlar içinde" sayılmıyor** (ORTA); günlük satır "ölçülemedi" diyor.
- **data/risk_limits.csv sorunları artık görünüyor** (ORTA): /risk tablosunda ve günlük satırda.
  - nan ve inf değerleri reddediliyor.
  - Noktalı virgüllü dosya (Türkçe Excel) okunuyor.
  - İki kez yazılmış sınır söyleniyor; satır sırası yerine sıkı olan geçerli.
- **M16 (veri kalitesi) bağımsız doğrulaması:** kısıtlı kullanılabilir (docs/validation/M16.md).
  - Temiz seride yanlış eleme yok (74.900 getiride 0).
  - %30 ve üstü kayıtsız bedelsiz ile bölünmeler %93–100 yakalanıyor.
  - YÜKSEK bulgu: ikinci kaynak kapalı olduğu için ±%10 içindeki hatalar görünmüyor (tek günlük ×1,05 hatalı kapanış, düz mum).
- Doğrulama: `test_risk_budget_validation` (12 test, önce kırmızıydı).

## v0.99.7 – 29.10.2026 (M15 D-7; M12 doğrulama raporu)
- **data/corporate_actions.csv silinirse artık söyleniyor** (doğrulama M15 D-7). Önceden bütün geçmişler sessizce düzeltmesiz kalıyordu; artık günlük raporun sorun listesinde görünüyor.
- **M12 (portföy riski) bağımsız doğrulaması:** kısıtlı kullanılabilir (docs/validation/M12.md).
  - Hesaplar doğru: 11 elle hesaplanmış durumda VaR ve etkin pozisyon sayısı kodla aynı çıktı.
  - Stres pencereleri, kaba kuvvet aramasıyla 300 seride aynı.
  - Sentetik veride VaR aşımı yaklaşık %5 (Kupiec p = 0,19).
  - YÜKSEK bulgu yok. İki ORTA bulgu stres raporunda: fiyatsız pozisyon sessizce düşüyor; pencere seans değil satır sayıyor.
- **M28 (risk bütçesi) bağımsız doğrulaması:** kısıtlı kullanılabilir (docs/validation/M28.md).
  - Ölçüler elle hesapla aynı: Euler katkısı, oynaklık, beta, likidite, düşüş, %80 sarı eşiği.
  - YÜKSEK bulgu: `/risk denge` gerçek hesapta sınıra geri götürmüyor (v0.99.8'de düzeltildi).

## v0.99.6 – 29.10.2026 (bağımsız doğrulama M15: erken düzeltme ve etiketler)
- **M15 değişti; yeniden doğrulama gerekir.**
- **İşlem tarihi gelmemiş satır artık bugünkü fiyatları değiştirmiyor** (D-3).
  - Önceden satır önceden girildiğinde bütün geçmiş, son gün dahil, erken yeni ölçeğe geçiyordu. Doğrulamadaki örnekte kapanış 11,0 iken 6,0 görünüyordu; /tara seviyeleri ve stoplar da kayıyordu.
  - Artık satır, işlem gününün ilk mumu gelince uygulanıyor.
- **"Ham" fiyatın tanımı düzeltildi** (O-3). `raw_bars` belgesi artık doğruyu söylüyor: eski günlerde Yahoo'nun kendi temettü ve bölünme düzeltmesi var; yalnız bizim düzeltmelerimiz yok. Bugünkü kapanış işlem fiyatı. Bedelli katsayısındaki etkisi küçük; doğrulamanın örneğinde 0,5500 yerine 0,5526.
- docs/DATA_CORRECTIONS.md'deki seanssız gün satırı koda uyduruldu (D-7). Fiyatlardan yalnız 08.02.2023 çıkarılıyor; tatil dosyası takvim için.
- Doğrulama: `test_double_adjustment::test_a_future_dated_row_waits_for_its_session` (önce kırmızıydı).

## v0.99.5 – 29.10.2026 (bağımsız doğrulama M15: çift düzeltme)
- **M15 (fiyat düzeltmeleri) değişti; yeniden doğrulama gerekir.**
- **Yahoo bir bölünmeyi sonradan kendisi düzeltirse katsayımız artık ikinci kez uygulanmıyor** (doğrulamanın ORTA bulgusu).
  - Önceden aynı düzeltme iki kez yapılıyordu ve sahte bir sıçrama çıkıyordu. Örnek: %100 bedelsiz sonrası 10 → 10,2 olağan bir gün, +%104 görünürdü.
  - Kural: ham açılış ±%10 limit içindeyse ama katsayıyla limit dışına çıkacaksa, veri zaten düzeltilmiş sayılıyor. Satır uygulanmıyor ve günlük rapordaki sorun listesinde adıyla yazılıyor.
  - Ham verideki sıçraması zaten limit dışında olan satırlar (ör. AYGAZ veri hatası, bedelsizler) eskisi gibi uygulanıyor.
- Önbellek testinin fikstürü, ham veride izi olmayan bir katsayı kullanıyordu (imkânsız +%25 sıçrama). Gerçekçi hale getirildi.
- Doğrulama: `test_double_adjustment`. Düzeltilmemiş veri düzeltiliyor; zaten düzeltilmiş veri olduğu gibi kalıyor ve raporda adı geçiyor; küçük katsayılı gerçek hareket yine düzeltiliyor.

## v0.99.4 – 29.10.2026 (bağımsız doğrulama M15: kurumsal işlem satırları)
- **M15 (fiyat düzeltmeleri) değişti; yeniden doğrulama gerekir.**
- **data/corporate_actions.csv'deki bozuk satırlar artık reddediliyor** (doğrulamanın ORTA bulgusu). Önceden bu satırlar fiyat geçmişini sessizce bozabiliyordu. Reddedilen satırın gerekçesi günlük rapordaki sorun listesine yazılıyor. Reddedilen satırlar:
  - kaynağı boş satır;
  - hafta sonu tarihi;
  - aynı hisse, tarih ve tür ikinci kez (iki kez uygulanırdı);
  - sıfır ya da eksi oran;
  - 0–20 dışındaki katsayı;
  - fiyatı yazılmamış bedelli (eskiden 1 TL varsayılıyordu).
- Otomatik öneriler (`--apply-suggestions`) kaynak olarak "otomatik öneri" yazıyor. Kaynak sütunu olmayan eski biçimli dosyalar okunmaya devam ediyor.
- Doğrulama: `test_corporate_rows`, her red nedeni için bir test. Depodaki dosyanın 29 satırının hepsi temiz yükleniyor.

## v0.99.3 – 29.10.2026 (bağımsız doğrulama M11: iz süren stop)
- **M11 (pozisyon uyarıları) değişti; yeniden doğrulama gerekir.**
- **İz süren stop artık yalnız yukarı gidiyor** (doğrulamanın YÜKSEK bulgusu).
  - Önce her gün "alıştan beri en yüksek kapanış − 2 × ATR" yeniden hesaplanıyordu. ATR büyüyünce stop aşağı kayıyordu (günlerin %38'inde), uyarı neredeyse her gün açılıp kapanıyordu.
  - Artık stop, o güne kadarki en yüksek seviye. Fiyat altına inince uyarı açık kalıyor, gidip gelmiyor.
- **Stop hesaplanamazsa artık söyleniyor.** ATR için mum yetmezse ya da alıştan sonra mum yoksa düşük önemli "stop hesaplanamadı" uyarısı çıkıyor; önceden stop sessizce kayboluyordu.
- **Teyitsiz kurumsal işlem kontrolü sağlamlaştı** (ORTA). Türkçe büyük harfi tanıyor ("TEYİT BEKLİYOR"); "teyit edildi" artık teyitsiz sayılmıyor.
- Doğrulama: `test_stop_ratchet`. ATR büyürken stop düşmüyor; elle hesaplanan en yüksek seviyeye eşit; uyarı açık kalıyor; az mum ve teyit ifadeleri denetleniyor.

## v0.99.2 – 29.10.2026 (bağımsız doğrulama M14'ün iki YÜKSEK bulgusu)
- **M14 (hesap ve defter) değişti; yeniden doğrulama gerekir.**
- **Gerçek hesabın getirisi alım günlerinde yanlıştı.** Yeni alınan paranın kazancı yalnız eski değere bölünüyordu. Örnek: 10.000 TL'ye 10.000 TL eklenip fiyat %5 artınca +%9,9 yazıyordu; büyük bir alımda +%293'e kadar çıkıyordu.
  - Artık Modified Dietz kullanılıyor: konan para dönemin başından, çekilen para sonundan sayılıyor. Aynı örnek +%5,0.
  - Bu endeksi kullanan "bu yana" satırı, risk bütçesindeki düşüş ve hesap düşüşü uyarısı da düzeldi.
  - Eski bir testin beklentisi eski formüle göre yazılmıştı. Elle yeniden hesaplanıp güncellendi: 5 TL komisyon, 10.005 TL'ye göre −%0,05.
- **Sanal hesaba bedelsiz/bedelli girilemiyordu.** %100 bedelsiz, sanal pozisyonu yarıya düşmüş gösteriyordu.
  - Artık `/trade bedelsiz THYAO 900 sanal` (bedelli ve temettü için de) sanal hesaba yazıyor.
  - Sanal alım ve satış yine yalnız `/paper` emriyle.
- Doğrulama: `test_performance_index` (doğrulayıcının örnekleri, büyük alım, satış ve temettü günü, sanal hesap) ve `test_paper_corporate`.

## v0.99.1 – 29.10.2026 (Talimat F: bağımsız doğrulama başladı)
- F'nin kapısı açıldı (K-58).
- Yüksek riskli 11 model için bağımsız doğrulama başladı. Her rapor modeli geliştirmemiş ayrı bir alt ajandan geliyor: geliştirme notlarını görmüyor, yalnız kod, test, belge ve veriyle çalışıyor.
- `/durum`'a "Model doğrulama" satırı geldi: kaç yüksek riskli modelin geçerli raporu var. Süresi geçen ya da "kullanılamaz" çıkan model UYARI veriyor.
- Doğrulama takvimi MAINTENANCE.md'de: yüksek risk yılda bir, orta risk iki yılda bir.
- Doğrulama: `test_model_validation` (kayıt MODELS.md ile aynı; durumlar; süre; `/durum` satırı).

## v0.99.0 – 29.10.2026 (profesyonel filtreler Aşama 4 ve 5)
- **Aşama 4 – temel puanlar** (`core/fundamentals/scores.py`). Formüller K-57'de veri görülmeden sabitlendi (1d5f434): Piotroski F, Altman Z'' (gelişen piyasalar), Beneish M, Greenblatt (kazanç getirisi, sermaye getirisi), Novy-Marx (brüt kârlılık, defter/piyasa).
  - Yayın tarihli depodan okunuyor; değer yayımın ertesi gününden itibaren kullanılıyor.
  - En son dönem bir yıl önceki aynı dönemle karşılaştırılıyor.
  - Eksik kalem "veri yok"; banka benzeri bilançoda "uygulanamaz"; TMS 29 geçişinde değişim ölçüleri hesaplanmıyor.
- Yeni `/temel THYAO`. Depo şu an boş, bu yüzden "veri yok" diyor.
- **Aşama 5 – a5 ön kayıt taslağı** ("kârlılık + değer", H6). RESEARCH_LOG ve RESEARCH_PROGRAM'da; durumu "taslak, onaylanmadı". Onay koşulları: yayın tarihli temel veri, kaynağın kullanım koşulu ve 6 ay kuralı (en erken 27.10.2027). Test yok.
- Doğrulama: `test_fundamental_scores` (10 test).
  - Dört puan elle hesaplanıyor; kısmi Piotroski tam sayılmıyor.
  - Banka benzeri bilanço ve yayından önce görünmeme denetleniyor.
  - TMS 29 geçişi, metin ve komut denetleniyor.

## v0.98.1 – 29.10.2026 (ileri hedef 3: kayıtlı taramaların haftalık özeti)
- Cuma raporunda yeni "📌 Kayıtlı taramalar" bölümü. Her kayıtlı taramanın canlı sonucu gösteriliyor: aynı kriterin `/tara` kayıtlarında 20 seans (yoksa 5) sonra XU100'e göre fark, aralıkla. 30 kayıttan önce "veri birikiyor".
- Kayıtlı taramalar PC'de kişisel dosyada olduğu için özet cumartesi araştırmasında değil, cuma raporunda.
- Doğrulama: `test_weekly_screens` (bölüm, eşik, kayıtsız durum, cuma satırı).

## v0.98.0 – 29.10.2026 (Talimat E: risk bütçesi)
- Tasarım K-56'da sonuç görülmeden yazıldı (575237e) ve aynen uygulandı (`core/alerts/budget.py`).
- **Sınırlar:** kullanıcının `data/risk_limits.csv` dosyası; kişisel, yedekte, şema denetiminde, git dışında.
  - Ölçülen sınırlar: tek hisse, portföy oynaklığı (60 seans), zirveden düşüş, 1 günlük %95 kayıp (250 seans).
  - Tek sektör sınırı "bilinmiyor", çünkü sektör kaynağı yok.
  - Durumlar yeşil / sarı (≥ %80) / kırmızı.
- **Ek ölçüler:** risk katkısı, beta, etkin pozisyon sayısı, kapanma süresi (20 seans hacminin %20'si), birlikte hareket eden çiftler.
- **Komutlar:** `/risk [gercek|sanal]`; `/risk ekle THYAO 100` (ya şöyle olsaydı; emir yok); `/risk denge` (sınırlara dönüş matematiği; "hesap sonucu, öneri değil").
- **Rapor ve uyarılar:** günlük raporda her hesabın altında tek satırlık özet var. Sarı ve kırmızı sınırlar `alerts_log`'a "risk_siniri" kuralıyla giriyor ve tekrar etmiyor.
- **Web:** `/risk/sanal`, `/risk/gercek`.
- HANDBOOK §13 "risk bütçemi nasıl tanımlarım", örnek dosyayla.
- Doğrulama: `test_risk_budget` (15 test).
  - İki hisse, korelasyon 1: oynaklık 1,5σ, risk katkısı ⅓ ve ⅔, beta 1,5; elle hesaplanıyor.
  - Kapanma süresi, düşüş, sınır dosyası okuma ve durum eşikleri denetleniyor.
  - Ya şöyle olsaydı ve denge elle hesaplanıyor.
  - Uyarı önemi, fiyatı olmayan pozisyon, komut ayrıştırma, bot, web, yedek ve şema denetleniyor.

## v0.97.3 – 29.10.2026 (senaryo sonucu: boşluklu açılış)
- İlk gerçek karnede görüldü: ertesi açılış geçersizliğin altına ya da hedefin üstüne boşlukla açılınca R tanımsız kalıyordu ve destek tepkisinin aralığı hesaplanamıyordu.
- Artık böyle bir açılışta girilecek senaryo yok: "dolmadı", tavan/taban açılışı gibi. K-55'e ek olarak yazıldı; şablon parametreleri değişmedi.
- Doğrulama: `test_scenarios` boşluklu açılış testi.

## v0.97.2 – 29.10.2026 (Özellik B: /tara senaryo(...))
- `/tara senaryo(destek_tepkisi)`, `senaryo(direnc_kirilimi)`, `senaryo(trend_geri_cekilme)`: şablonun bugün kurulduğu hisseler. Diğer koşullarla birleşiyor.
- Değer, şablonun kendi gün gün sinyali. Liste ve karne aynı tanımı kullanıyor; geleceği görmüyor.
- Alan adı doğrudan yazılırsa doğru yazımı gösteren bir hata çıkıyor. HANDBOOK alan tablosu güncellendi.
- Doğrulama: `test_scenarios_screen` (yazım, hatalı şablon, değerin şablon sinyaline eşitliği) ve alan tamlığı testi.

## v0.97.1 – 29.10.2026 (Özellik B: karne ve canlı kayıt)
- **Karne** (`core/analytics/scenarios_study.py`). Tarama dönemi; holdout okunmuyor; BIST 100 geçmiş üyeliği; günün varsayılan elemesi. Her şablon için olay sayısı, hedef / geçersizlik / süre doldu oranları, ortalama R ve %95 aralığı (20 seanslık blok bootstrap), en kötü geçersizlik serisi, XU100'e göre fark.
  - PC'de cuma akşamları ya da önbellek yoksa raporla hesaplanıyor, `/senaryo`'da görünüyor.
  - GitHub'da `screens.yml` iş akışında yazdırılıyor.
- **Canlı kayıt:** her akşam tetiklenen senaryolar, sonucu bilinmeden, günde bir kez `logs/scenarios_log.csv`'ye yazılıyor. `/performans`'a "🧭 Senaryolar" bölümü geldi; karneyle aynı kuralla puanlıyor. 30 sonuçlanan kayıttan önce "veri birikiyor".
- Hata olursa rapor etkilenmiyor (log'a yazılıyor).
- Doğrulama: `test_scenarios_study` ve `test_scenarios_live` (10 test).
  - Özet elle hesaplanıyor.
  - Karne ve canlı kayıt aynı sonuç kuralını kullanıyor.
  - Holdout değişince karne değişmiyor.
  - Kayıt günde bir kez yazılıyor.
  - Cuma ve önbellek kuralı denetleniyor.
  - Hatalar raporu durdurmuyor.

## v0.97.0 – 29.10.2026 (Özellik B: senaryo şablonları ve /senaryo)
- Üç şablon sonuç görülmeden K-55'e yazıldı (c7b25ea) ve aynen kodlandı (`core/analytics/scenarios.py`): destek tepkisi, direnç kırılımı, trend içi geri çekilme.
- Her senaryo şunları hesaplıyor:
  - giriş varsayımı (ertesi açılış), geçersizlik, hedef;
  - maliyet sonrası R (her yön %0,10 + %0,05); R < 1,5 "elverişsiz";
  - adet hesabı: risk bütçesi ve likidite sınırı; yalnız hesap, emir değil;
  - tavan/taban riski.
- Sonuç kuralı karne ve canlı kayıt için ortak: hedef, geçersizlik ya da 20 seans. Aynı seans ikisi birden olursa geçersizlik sayılıyor. Tavan ya da taban açılışında dolmuyor.
- Yeni `/senaryo THYAO` ve `/senaryo THYAO giris 240 gecersiz 232 hedef 262 [risk=%0,5]`. Her çıktı "Kural çıktısıdır, öneri değildir…" satırıyla bitiyor. HANDBOOK §12 "senaryo nedir, ne değildir".
- Doğrulama: `test_scenarios` (14 test).
  - R, sonuç, boşluk, aynı seans, süre ve tavan kuralları elle hesaplanıyor.
  - Her tetiklenen günde şablon kuralları sağlanıyor.
  - Gelecek değişince geçmiş değişmiyor.
  - Öneri kelimesi yok.
  - Adet elle hesaplanıyor.
  - Komut ayrıştırma ve bot kaydı denetleniyor.

## v0.96.1 – 29.10.2026 (K-54: devredilen kararlar)
- **İş Yatırım ikinci kaynağı kapatıldı (D13).** Sitenin robots.txt'si kullandığımız yolu bütün otomatik erişime yasaklıyor. Hiçbir istek gitmiyor.
  - Haftalık özet "kapalı" yazıyor.
  - "Veri doğruluğu" SLO'su nedeniyle birlikte "bilinmiyor" diyor.
  - Karşılaştırma kodu kayıtlı veriyle test edilmeye devam ediyor.
- **Yahoo riski belgelendi (yeni bulgu D15, yüksek).** Yahoo'nun şartları da otomatik veri toplamayı yasaklıyor. Ücretsiz ve uyumlu bir BIST kaynağı bulunamadı. Mevcut kişisel, günde bir toplu indirme kabul edilmiş risk olarak sürüyor ve genişletilmeyecek. Uyumlu çözüm lisanslı veri; bu bir ödeme kararı.
- **Sektör ataması yapılmayacak (D14).** Uyumlu bir kaynak yok ve tahmin edilmiyor. C sektör dışında tamam.
- **B (senaryolar) ve E (risk bütçesi) açıldı.**
- Doğrulama: `test_isyatirim_off` (kaynak kapalıyken ağ isteği yok, bekleme yok; özet ve SLO metni) ve `test_second_source` (kapalı durum).

## v0.96.0 – 29.10.2026 (ileri hedef 1: eleme filtresinin canlı ölçümü)
- Her akşam bugünkü BIST 100'e `/tara`'nın varsayılan elemesi uygulanıyor. Elenen ve kalan hisseler canlı ölçüme "eleme" kaynağıyla ayrı ayrı yazılıyor (K-53).
- `/performans`'a "🧹 Eleme filtresi (canlı)" bölümü geldi.
  - İki grubun 5 ve 20 seans sonra XU100'e göre sonucu ve gün gün farkı, %95 aralıkla.
  - Keşif referansı (elenen −%3,07) yanında yazıyor.
  - 30 olgun elenen kaydından önce "veri birikiyor".
- Teknik görünümün canlı ölçümü ve karar ölçütü değişmedi. Bu ölçüm hata verirse rapor gidiyor ve bir uyarı satırı ekleniyor.
- Doğrulama: `test_elimination_live` (6 test). Kayıt günde bir kez yazılıyor; fark elle hesaplanıyor; bölüm "sorulan kayıtlar"a karışmıyor; günlük rapora bağlantı ve hata yolu denetleniyor. Testlerde kayıt dosyası geçici klasörde.

## v0.95.7 – 29.10.2026 (Ö34: eski kur hiçbir zaman kullanılmıyor)
- Gerçek veride ilk araştırma çalışmasında XU100'ün USD getirisi +%383 çıktı; doğrusu yaklaşık +%56. Kur önbelleği yarı doluydu ve bitiş günü için aylarca eski bir kur kullanılmıştı. Bu bir deneme çalışmasıydı; PC'deki rapor etkilenmedi.
- Bir günün kuru artık en çok 10 gün eski olabilir (9 günlük bayram tatili sığar). Daha eskiyse "USD: kur yok" yazar.
- Önbellek önce son iki haftayı ve dönemin başını dolduruyor, sonra aradaki günleri. Araştırmada başlangıç, araştırmanın kendi başlangıcının 10 gün öncesi.
- Nakit serisi dönemin başını kapsamıyorsa artık "nakde göre: faiz serisi dönemin başını kapsamıyor" yazıyor. Politika faizi dosyası 23.06.2023'te başlıyor; öncesi tahmin edilmez.
- Doğrulama: `test_macro`.
  - Eski kur reddediliyor; 9 günlük boşluk kabul ediliyor.
  - Önce iki uç dolduruluyor.
  - Nakit notu denetleniyor.
- Reel sütun gerçek veride elle karşılaştırıldı: 2022–2026'da TÜFE yaklaşık 7,2 kat, XU100 nominal 5,8 kat arttı; reel −%19,9 tutarlı.

## v0.95.6 – 29.10.2026 (Talimat C: ikinci kaynak kur)
- Akşam raporu son iki haftanın Yahoo `USDTRY=X` kapanışını TCMB bülteniyle karşılaştırıyor. Sonuç `logs/usd_second_source.json` dosyasına yazılıyor.
- `/durum` "Makro veri" satırı en büyük farkı gösteriyor. Fark %1'i aşarsa UYARI veriyor; hiçbir değer değiştirilmiyor (K-51). Yahoo'nun günlük kapanışı başka bir saatte alındığı için küçük farklar olağan.
- Yahoo isteği fiyat deposunun kullandığı sağlayıcıyla yapılıyor. Testlerde ağ kapalı.
- Doğrulama: `test_macro.SecondSourceTest`. Fark elle hesaplanıyor; yalnız iki kaynakta da olan günler sayılıyor; kaynak yoksa ya da ağ yoksa sessiz; `/durum` metni ve uyarı denetleniyor.

## v0.95.5 – 29.10.2026 (kur adımına süre sınırı; Ö33)
- Gerçek veride ilk denemede görüldü: TCMB'de bir bülten isteği yaklaşık 1,6 saniye sürüyor. Araştırmanın kur adımı bütün geçmişi bir kerede istediği için 33 dakikayı geçti. Bu, cumartesi araştırmasını 90 dakikalık iş sınırına itebilirdi. Deneme çalışması iptal edildi; kayıtlar etkilenmedi.
- Kur önbelleğini dolduran fonksiyonun artık bir süre sınırı var.
  - Araştırmada 8 dakika; adımın kendi sınırı 10 dakika.
  - Akşam raporunda 30 saniye.
- 50 bültende bir ara kayıt yapılıyor. Duran çalışma aldıklarını kaybetmiyor; bir sonraki kaldığı yerden devam ediyor. Bütün geçmiş birkaç cumartesi içinde doluyor.
- Doğrulama: `test_macro` süre sınırı ve ara kayıt testleri.

## v0.95.4 – 29.10.2026 (öz-denetim 8: iki düzeltme)
- `/tara ... rejim=` canlı listede fiyatı olmayan bir hisse varken çöküyordu (Ö27). Verisiz hisseler artık rejim hesabının dışında kalıyor.
- Rejim filtreli bir abonelik listesi rejim değişince boşalıyor. Mesaj artık bunun nedenini yazıyor: bugünkü rejim ve filtre (Ö28).
- Öz-denetim 8'in bulguları ROADMAP'te; kritik ya da yüksek bulgu yok.

## v0.95.3 – 29.10.2026 (Talimat C: araştırma raporunda dört baz)
- Araştırma raporunda strateji tablosunun altına yeni bir bölüm eklendi: her stratejinin ve XU100'ün toplam getirisi nominal, reel, USD ve nakde göre. Ek bilgidir; birincil ölçüt (XU100'e göre fazla getiri, Bonferroni aralığı) değişmedi.
- Haftalık araştırma iş akışı, TCMB kur bültenlerini 01.12.2021'den bu yana dolduruyor (`python -m core.market.macro --usd`). Her gün bir kez soruluyor ve GitHub önbelleğinde tutuluyor. İlk çalışma yaklaşık 10 dakika uzun sürecek.
- Doğrulama: `test_backtest` araştırma raporunda dört baz bölümünü ve XU100 satırını denetliyor.

## v0.95.2 – 29.10.2026 (Talimat C: /tara rejim= filtresi)
- `/tara ... rejim=dusus` (seçenekler `yukselis`, `dusus`, `karisik`, `yuksek_oynaklik`).
  - Liste yalnız bugünkü rejim seçilen rejimse çıkar. Değilse boş kalır ve "Bugünkü rejim: …" diye nedenini yazar.
  - Karne yalnız kendi rejimi seçilen olan günleri sayar. Her günün etiketi o güne kadarki veriyle hesaplanır.
- Seçenek kriterin parçası; aynı koşulun rejimsiz karnesi ayrı kalır.
- Küçük evrenlerde (`evren=izleme`) rejim yine bugünkü BIST 100'den hesaplanır, çünkü genişlik için en az 20 hisse gerekir.
- Doğrulama: `test_screen_regime` (7 test): ayrıştırma ve hatalı değer, canlı liste iki durumda, küçük evren, karnede yalnız seçilen günler, karnenin rejime doğru veriyi vermesi.

## v0.95.1 – 29.10.2026 (Talimat C: /piyasa, rejim, genişlik, sektörler)
- Yeni `/piyasa` komutu üç şeyi gösteriyor:
  - rejim etiketi (yükseliş / düşüş / karışık / yüksek oynaklık / bilinmiyor) ve üç girdisi;
  - BIST 100'ün EMA50 üstündeki payı;
  - dört ana sektörün (Banka, Sınai, Hizmetler, Holding) son 1, 5 ve 20 seansta XU100'e göre puanı.
- Tanım K-51'de sonuç görülmeden yazıldı ve aynen uygulandı. Eşikler sabit; her gün yalnız kendi kapanışına kadarki veriyi kullanıyor.
- Çıktıda "Rejim bir etikettir, sinyal değildir" ve "Kural çıktısıdır, öneri değildir" yazıyor.
- Sektör endeksleri (XBANK, XUSIN, XUHIZ, XHOLD) akşam fiyat güncellemesine eklendi. Verisi olmayan sektör "veri yok" diyor.
- Doğrulama: `test_regime` (12 test).
  - Etiket kurallarının tablosu.
  - Elle hesaplanmış trend, oynaklık yüzdeliği, genişlik ve göreli güç.
  - Gün üyeliği ve en az 20 hisse kuralı.
  - Gelecek değişince geçmiş etiket değişmiyor.
  - Metinde öneri kelimesi yok.
  - Komut kaydı ve BotFather listesi.

## v0.95.0 – 29.10.2026 (Talimat C başladı: enflasyona, dolara ve nakde göre sonuç)
- Kullanıcının "daha da ötesini yapabilirsin" mesajıyla C'nin kapısı açıldı (K-52).
- Yeni `core/market/macro.py`. Her sonuç dört bazda gösteriliyor: nominal, reel (TÜFE), USD (TCMB gösterge kuru) ve nakde göre (politika faizi, stopaj sonrası).
  - Günlük raporda her hesabın altında ilk kayıttan bu yana dört bazlı satır var.
  - `/performans`'ta sanal hesap ve aynı dönemin XU100'ü için aynı satır var.
  - Ek bilgidir; canlı ölçüm ve araştırma ölçütleri değişmedi.
- Yeni `data/macro/cpi.csv`: 2021'den Eylül 2026'ya 69 ay, her ayın yayım günüyle. Veri TÜİK'in, TCMB'nin "Tüketici Fiyatları" tablosundan; şartları arşivli. Elle hiçbir rakam yazılmadı; dosya arşivlenmiş sayfadan üretildi.
  - Yayım tarihi ayın 3'ü; hafta sonuysa pazartesi. Kaynaklı iki istisna var: 5 Mayıs 2022 ve 5 Haziran 2026.
  - Değer yayımın ertesi gününden itibaren kullanılıyor. Ay içinde tahmin yok.
- Veri kendiliğinden güncelleniyor.
  - Akşam raporu son iki haftanın eksik TCMB kur bültenlerini istiyor (en çok 10 istek). Kurlar yerel önbelleğe, git dışına yazılıyor.
  - Her ayın 3'ünden sonra yeni TÜFE ayı TCMB tablosundan ekleniyor. Yayım tarihi olarak ilk görüldüğü gün yazılıyor; gerçek yayımdan önce olamaz.
- `/durum`'a "Makro veri" satırı eklendi: TÜFE ayı ve son kur günü. Gecikirse UYARI veriyor.
- Doğrulama: `test_macro` (19 test). Elle hesaplanmış örnekler var: bir ay, bir yıl, kur, nakit. TÜFE yayımın ertesi gününden önce görünmüyor. Zincirlenen 12 ay TÜİK'in yıllık rakamıyla ±0,15 puan içinde. Gerçek TCMB sayfasından okunan 260 ay dosyayla bire bir aynı. Rapor ve `/performans` testleri dört bazlı satırı denetliyor.

## v0.94.2 – 28.10.2026 (2027 tatil takvimi)
- `data/bist_holidays.csv` 2027'nin 13 gününü içeriyor: 11 tam tatil ve 2 yarım gün (8 Mart Ramazan Bayramı arifesi, 28 Ekim). Kaynaklar: 2429 sayılı Kanun'daki sabit günler ve Diyanet'in 2027 takvimi. Ramazan Bayramı 9–11 Mart; Kurban Bayramı 16–19 Mayıs, 19 Mayıs'la çakışıyor, arifesi cumartesiye denk geliyor.
- Hafta sonuna düşen günler (1 Mayıs, 15–16 Mayıs) dosyada yok.
- 2027 "geçici" sayılıyor, çünkü Borsa İstanbul'un kendi listesi Aralık'ta çıkacak.
  - `/durum` şimdi "2027 geçici" notu gösteriyor. Aralık'tan itibaren teyit için uyarı veriyor.
  - Ocak 2027'de bot artık "tatil takvimi yok" demeyecek; tatil günlerinde yanlış "rapor gitmedi" alarmı vermeyecek.
- Doğrulama: `test_calendar.Holidays2027Test` (günler, bayram sonrası son seans, seans sayımı) ve güncellenmiş `/durum` testi.

## v0.94.1 – 28.10.2026 (C/D/E/F paketi: yol haritası, kaynaklar, model envanteri; kod yok)
- ROADMAP'e dört başlık eklendi: C piyasa bağlamı, D olay takvimi, E risk bütçesi, F model riski. Her birinde koşul, en erken tarih ve bitti ölçütü var. Kapıların okunuşu DECISIONS K-51'de.
- K-51'de C'nin tasarımı var: reel/USD/nakit formülleri, TÜFE'nin ileri taşınması ve sabit rejim tanımı. Hepsi sonuç görülmeden yazıldı.
- Yeni `docs/DATA_SOURCES.md`: her kaynağın kullanımı ve kullanım koşulu.
  - EVDS şartları ve TCMB kur XML'i Actions ile arşivlendi; ikisi de kaynak gösterilerek kullanılabilir.
  - TÜİK koşulu teyit edilemedi, bu yüzden elle giriş yolu seçildi.
  - Borsa İstanbul'un telif bildirimi, bilginin yazılı izinsiz saklanmasını yasaklıyor. Bu yüzden sektör dosyası kullanılmıyor.
  - Mevcut BIST 100 değişiklik dosyası ve sayfa arşivi bu bildirimle çelişebilir; yeni bulgu D14 olarak kaydedildi ve kullanıcı kararı bekliyor.
- Yeni `docs/MODELS.md` (F1): 23 model; amaç, girdi, varsayım, sınır, doğrulama durumu ve risk. 8'i yüksek risk; bağımsız doğrulama sırası yazılı.
- Kod değişmedi; C ve D'nin kodu kapı açılınca yazılacak.

## v0.94.0 – 28.10.2026 (Özellik A tamam: ölçüm sonucu, not, web)
- Anlamlılık ölçümü gerçek veride çalıştı:
  - gerçek küme seviyelerinde dönüş %31,3, rastgele seviyelerde %31,0;
  - fark +0,3 puan, %95 [−0,5; +1,1];
  - sonuç: rastgele seviyeden ayırt edilemedi (RESEARCH_LOG).
- Her seviye çıktısında artık "tarihsel olarak rastgele seviyeden ayırt edilemedi" notu var: `/seviye`, `/analyze`, rapor satırı, web.
- Web panelinde `/seviye/{kod}` adresi listeyi JSON olarak veriyor.
- Kalan bitti ölçütü: seviye kaydının PC'de her akşam yazıldığının kanıtı (ilk iş günü 30.10).

## v0.93.1 – 28.10.2026 (Özellik A §3.3: anlamlılık ölçümü)
- `core/analytics/levels_study.py`: kapanış bir küme seviyesine 0,25 ATR'den yakınken sonraki 5 seans "dönüş", "kırılma" ya da "belirsiz" olarak sınıflanıyor. Aynı sayıda rastgele seviyeyle (52 hafta aralığı, sabit tohum) karşılaştırılıyor; fark 20 seanslık blok bootstrap ile %95 aralıkla veriliyor.
- Tanımlayıcı ölçümdür; hipotez değildir, bütçeden harcamaz. `screens.yml` iş akışında çalışıyor.
- Seviyeler gün gün `cluster_days` ile tek kaynaktan geliyor; `daily_series` de onu kullanıyor.
- Doğrulama: `test_levels_study` (elle sınıflama, sayım tutarlılığı, geleceği görme yok).

## v0.93.0 – 28.10.2026 (Özellik A: /tara alanları, rapor satırı, seviye kaydı)
- `/tara`'ya beş alan geldi: `destek_uzaklik_atr`, `direnc_uzaklik_atr`, `seviye_gucu`, `kirdi_yukari(direnc)`, `kirdi_asagi(destek)`.
  - Gün gün, geleceği görmeden hesaplanıyor; her gün `levels()`'ın o güne kesilmiş sonucuyla aynı (test).
  - Canlı listede yalnız son 64 gün hesaplanıyor, karne hepsini hesaplıyor.
- Günlük raporda her pozisyonun altında en yakın küme desteği bilgi satırı olarak yazıyor. ATR iz süren stop uyarısı aynı.
- Her akşam rapordan sonra o günün küme seviyeleri `logs/levels_log.csv`'ye yazılıyor (yalnız ekleme, günde bir kez). `/durum`'a "Seviye hesabı: son tarih" satırı eklendi.
- Doğrulama: `test_levels_fields`, `test_levels_report`.

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
