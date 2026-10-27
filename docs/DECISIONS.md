# Kararlar

Sürekli yol haritası (ROADMAP) gereği Claude'un verdiği teknik kararlar, tarihli ve gerekçeli. En yenisi en üstte.

## 27.10.2026

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
