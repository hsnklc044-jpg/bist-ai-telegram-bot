# Kararlar

Sürekli yol haritası (ROADMAP) gereği Claude'un verdiği teknik kararlar, tarihli ve gerekçeli. En yenisi en üstte.

## 27.10.2026

**K-6. Aşama E'deki "veriyi 2015'e uzatma" işi durduruldu.** Kullanıcı aynı gün bu yönü seçmişti; ardından gelen sürekli yol haritası araştırmayı (E) dayanıklılık ve izleme işleri bittikten sonraya koydu. Yapılan: kaynak sayfa arşivi iş akışı (`sources.yml`) ve ilk kaynak indirmesi; ikisi de durur, iş E sırasında kaldığı yerden sürer. Gerekçe: yol haritası tek kaynak.

**K-5. Dosya kilitliyken (Excel) rapor durmaz.** Kilitli dosyaya yazılmaz, raporun "Veri notları"nda adı geçer, sonraki çalışma yazar. Sanal emir doldurma zaten idempotent (defterdeki "sanal emir #N" etiketi), bu yüzden yarıda kalan dolum ikinci kez yazılmaz. Alternatif (raporu tamamen durdurmak) günün raporunu ve canlı ölçüm satırını kaybettiriyordu.

**K-4. Yarım kalan son satırdan sonra ekleme yeni satırdan başlar.** Ekleme yapan dört yer (defter, uyarı kaydı, sinyal kaydı, runs.csv) dosya satır sonuyla bitmiyorsa önce `\n` yazar. Mevcut baytlar değişmez (kişisel kayıt kuralı). Yarım satır olduğu gibi kalır ve okuma sırasında satır numarasıyla bildirilir. Gerekçe: aksi halde sağlam yeni kayıt yarım satıra yapışıp kayboluyordu; runs.csv'de bu, raporun ikinci kez gönderilmesi demekti.

**K-3. Rapor, hiç fiyat inmezse 1 + 2 + 4 dakika bekler.** Yalnız bütün semboller başarısızsa (ağ yok) beklenir; tek sembolün başarısızlığı ağ sorunu sayılmaz. Toplam 7 dakika, Windows görevinin 30 dakikalık sınırının içinde kalır.

**K-2. Botun günlük işleri 4 saate kadar geç başlayabilir.** python-telegram-bot varsayılanı 1 saniye; PC 20:00'de uykudaysa kontrol sessizce atlanıyordu. 4 saat: 20:00 kontrolü gece yarısına kadar telafi edilir; ertesi günün işine karışmaz. `coalesce=True` ile kaçan çalıştırmalar tek bir çalıştırmaya iner.

**K-1. Açılışta ağ hatası 20 kez denenir, sonsuz değil.** python-telegram-bot sonsuz denemeyi önermiyor. 20 deneme, artan aralıklarla yaklaşık 7 dakika eder. Sonrasında bot kapanır ve "QuantBIST Bot" görevi 5 dakika arayla 3 kez yeniden başlatır; toplam yaklaşık 20 dakikalık bir pencere. Yanlış token denenmez.

**K-0 (daha önce, v0.48.1). Fiyat düzeltme kapısında veritabanı SHA kontrolü alınmadı.** Fiyat deposu her gün değiştiği için ilk güncellemede her şeyi reddederdi. Onay listesinin bütünlüğünü git geçmişi sağlar.
