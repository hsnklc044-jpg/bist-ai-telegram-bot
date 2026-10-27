# QUANTBIST – ANA YÖNETİM BELGESİ (ONAYSIZ MOD, SÜREKLİ)

Kullanıcı, 27.10.2026. Bu belge bundan sonraki çalışmanın tek kaynağıdır. ROADMAP.md, DECISIONS.md, OPERATIONS.md ve RESEARCH_LOG.md bu belgeye göre güncellenir. Onay sorulmaz: kararlar verilir, gerekçesi DECISIONS.md'ye tarihli yazılır, devam edilir.

## 1. Amaç

QuantBIST'i; kesintiye dayanıklı, kendi sağlığını ölçen, verisi doğrulanmış, araştırması dürüst ve aylarca bakımsız çalışabilen bir sisteme dönüştürmek. Öncelik sırası her zaman: veri ve kayıt bütünlüğü → hesap doğruluğu → kesintiye dayanıklılık → ölçüm dürüstlüğü → kullanım kolaylığı → yeni yetenek.

## 2. Ölçülebilir sağlık hedefleri (SLO)

Bunlar ölçülür, /durum ve haftalık raporda gösterilir; hedef tutmuyorsa onu düzeltmek en öncelikli iş olur:
- Rapor teslimi: iş günlerinin ≥ %99'unda 18:30 raporu 19:00'a kadar gitmiş olmalı (tatiller hariç, tatilde tekrar gönderim = hata).
- Bot ayakta kalma: haftalık ≥ %98 (yaşam sinyalinden hesapla; PC kapalı süreyi ayrı göster).
- Veri tazeliği: seans günü 19:00'da XU100 ve hisselerin ≥ %98'i o günün kapanışına sahip.
- Veri doğruluğu: ikinci kaynakla haftalık karşılaştırmada eşik dışı fark ≤ %1 hisse; aşanlar isimle listelenir.
- Yedek: her gün doğrulanmış yedek; haftalık izole geri yükleme testi başarılı.
- Kayıt bütünlüğü: kişisel kayıtlarda okunamayan satır = 0, tekrar kayıt = 0, kaydı olmayan seans = 0.
- Kalite: CI yeşil, test kapsamı core+bot ≥ %90 ve hiçbir sürümde düşmez.

Ölçülemeyen hedef "bilinmiyor" gösterilir; asla "sağlıklı" sayılmaz.

## 3. Roller

- Claude: geliştirici ve teknik karar verici. Kodu yazar, test eder, sürüm yayınlar.
- Yerel otomasyon (`C:\Projeler\QuantBIST_otomasyon`): sürümü PC'ye kurar, deneme kopyasında ruff+pytest çalıştırır, botu "QuantBIST Bot" görevi üzerinden yeniden başlatır, başarısızlıkta geri alır, akşam ve haftalık kontrol yapar, Telegram'a yazar. Kullanıcıya kurulum komutu verilmez.
- Kullanıcı: yalnız hesap, token, ödeme ve .env işlemleri. Bunlar için beklenmez; "BENİM ADIMLARIM" listesine yazılır ve devam edilir.

## 4. Her turda izlenecek karar algoritması

1. CI ve son araştırma çalışmasını kontrol et. Kırmızıysa önce onu düzelt.
2. SLO'lardan hedefi tutmayan varsa onu düzelt.
3. Açık hata (ROADMAP "açık" + kendi bulduğun) varsa önem sırasıyla düzelt.
4. Aşağıdaki aşamalardan koşulu oluşmuş en öncelikli işi yap.
5. Her 10 sürümde bir bağımsız öz-denetim yap (bölüm 7).
6. Koşulu oluşmuş iş kalmadıysa: bekleyenleri ve neyi beklediklerini listele, dur. Boş iş üretme.

## 5. Aşamalar

**A – Dayanıklılık** (her zaman, öncelikli)
1. Bot açılışta tek ağ hatasında kapanıyor ("getaddrinfo failed", "Failed run number 0 of 0. Aborting."): bootstrap_retries ile düzelt; önce başarısız test.
2. Kesinti senaryolarını testle kapsa: uyku/uyanma, geç gelen internet, DNS hatası, Telegram 429/5xx, kilitli dosya, yarım yazılmış satır, disk dolu, saat değişimi, aynı anda iki çalıştırma.
3. Her senaryo için OPERATIONS.md'de "ne olur / nasıl fark edilir / nasıl toparlanır / kimin işi" satırı.

**B – Gözlemlenebilirlik**
1. Tek yerde sağlık puanı: SLO'ların haftalık değeri /durum ve cumartesi raporunda.
2. Dışarıdan izleme: ayarlar OPERATIONS.md §7 ile aynı ("QuantBIST rapor" Cron 35 18 * * 1-5, Europe/Istanbul, grace 1 saat; "QuantBIST bot" 5 dk / grace 20 dk). /durum'a "izleme: tanımlı mı, son ping başarılı mı" satırı; adres asla gösterilmez ya da loglanmaz. Adresler .env'e girilince doğrulandı yap.
3. Log'larda her çalıştırmanın kimliği, süresi ve sonucu tek satırda; hata satırları aranabilir.

**C – Veri bütünlüğü**
1. İkinci kaynak karşılaştırmasını SLO'ya bağla; eşik aşan hisse için otomatik "şüpheli" etiketi, araştırmada dışlama seçeneği.
2. Kurumsal işlem (bedelsiz, bedelli, temettü) şüphesi için haftalık tarama; bulgular DATA_CORRECTIONS.md'ye kaynağıyla.
3. Geleceği görme (lookahead) ve hayatta kalma yanlılığı (survivorship) korumaları için kalıcı testler; yeni her araştırma kodu bunlardan geçer.

**D – Gerçek ortam gözlemleri** (olay gerçekleştiğinde)
Yarım gün, tam gün tatil, haftalık canlı ölçüm, zamanlanmış araştırma, kaçırılan rapor, PC kapanması. Kanıt GitHub'dan (CI, Actions, research-results) toplanır; PC kanıtı için yerel otomasyonun haftalık raporuna güvenilir ya da BENİM ADIMLARIM'a eklenir. Her gözlem "doğrulandı / sorunlu" işaretlenir; sorunlu düzeltilir.

**E – Felaket kurtarma**
1. "PC tamamen bozuldu" senaryosu: sıfır bir Windows makinede yedekten tam kurulum adımları; adımları otomatik doğrulayan bir test/betik.
2. Aylık geri yükleme tatbikatı (yerel otomasyon yapar), sonucu raporda.
3. Token sızarsa ne yapılır: iptal, yenileme, .env güncelleme adımları.

**F – Altyapı kararları** (en az bir haftalık çalışma kaydı oluşunca ya da SLO tutmayınca)
PC'de kalmanın riski SLO verisiyle hesaplanır. Sunucu gerekiyorsa kod, belge, maliyet ve PC ile paralel deneme planı hazırlanır, karar DECISIONS.md'ye yazılır; kiralama/ödeme BENİM ADIMLARIM'a.

**G – Araştırma** (yazılım, dayanıklılık ve veri işleri bitince)
1. Ön kayıt zorunlu: hipotez, kural, başarı ölçütü, test dönemi ve kaç deneme yapılacağı RESEARCH_LOG'a sonuçtan önce yazılır.
2. Deneme bütçesi: yapılan tüm denemeler sayılır; çoklu test düzeltmesi bu toplam sayıyla yapılır.
3. Dokunulmamış son dönem (holdout) ayrılır ve yalnız bir kez, son değerlendirmede kullanılır.
4. Her sonuçta gerçekçi maliyet (komisyon, kayma, vergi, tavan/taban, düşük hacim) ve en kötü senaryo (en büyük düşüş, en uzun zarar süresi, en kötü ay).
5. Sonuç olduğu gibi kaydedilir; sonuca bakıp kural ayarlanmaz. "İşe yarıyor" için: XU100'e karşı istatistiksel anlamlı fark + maliyet sonrası pozitif getiri + holdout'ta tutarlılık.
6. Üst üste reddedilen fikirlerden ders çıkarılır: hangi tür fikirlerin denenmeye değmediği RESEARCH_LOG'da özetlenir.

**H – Canlı ölçüm kararı** (/performans yeterli bağımsız veriye ulaşınca)
Tam rapor (gün sayısı, XU100'e göre fark, güven aralığı, sanal hesap), önceden belirlenen ölçüte göre karar (anlamlı / anlamlı değil / yetersiz veri), backtest beklentisiyle karşılaştırma ve sapma nedenleri, sonraki ölçüm dönemi planı.

**I – Güvenlik ve bağımlılıklar**
1. Haftalık paket güvenlik taraması (pip-audit veya eşdeğeri); açık varsa test edilmiş yükseltme.
2. Depoda gizli bilgi taraması; .env, token ya da kişisel kayıt asla commit edilmez (CI kontrolü).
3. Yeni bağımlılık ancak gerekçesi DECISIONS.md'de yazılıysa eklenir.

**J – Bakım ve devir**
1. "Aylar sonra hiç hatırlamadan açan biri" için tek belge: mimari şema, kurulum, günlük işleyiş, yerel otomasyon, sorun giderme, geri yükleme, sık sorulanlar.
2. Bakım takvimi: haftalık, aylık, yıllık (yeni yıl tatil takvimi, BIST 100 listesi, paket sürümleri).
3. Süresi dolacak her şey için önceden /durum uyarısı.
4. CHANGELOG.md: her sürüm için sade dille ne değişti, nasıl doğrulandı.

## 6. Kalite kapıları (her sürümde)

- Önce hatayı gösteren başarısız test, sonra düzeltme.
- CI yeşil, ruff temiz, kapsam düşmemiş; küçük sürümler halinde yayın.
- Kullanıcıya görünen her sayının (değer, getiri, risk, etkin pozisyon, VaR) elle hesaplanabilen küçük örnekle testi var.
- Testler ağa çıkmaz; gerçek data/, logs/ ve yerel çalışma klasörlerine (backups\, qb\, research_workspace\) bağımlı değildir ve yazmaz.
- Kişisel kayıt şeması değişecekse: geçiş testi + değişiklikten önce otomatik yedek + belgelenmiş geri dönüş. Üçü yoksa değiştirilmez.
- Kişisel kayıtlar asla silinmez ya da üzerine yazılmaz; düzeltme yeni satır/yeni dosya olarak yapılır.
- İki denemede çözülemeyen hata: değişiklik geri alınır, ROADMAP'e "açık" yazılır, başka işe geçilir.

## 7. Öz-denetim (her 10 sürümde bir)

Kod başkası yazmış gibi baştan okunur: hesap hatası, sessiz yutulan hata, saat dilimi, tekrarlanan mantık, ölü kod, belge ile kod çelişkisi, SLO'ya yansımayan risk. Bulgular önem sırasıyla ROADMAP'e yazılır, kritik ve yüksekler hemen düzeltilir.

## 8. Kaynak kullanımı

Kullanıcının kullanım limiti sınırlı. İşler toplu yapılır, gereksiz araştırma çalıştırmaları tekrarlanmaz, uzun bekleyişlerde döngü uyutulur. Koşulu oluşmuş iş yoksa durulur.

## 9. Kesinlikle yapılmaz (sorulmaz, atlanır)

- Gerçek parayla emir, aracı kurum bağlantısı, gerçek hesaba işlem.
- Ödeme, hesap açma, şifre/token girme veya isteme.
- Herhangi bir strateji için "al/sat" önerisi; sonuç olumlu olsa da yalnız bulgu ve belirsizlik raporlanır.

## 10. Raporlama

Her sürümden sonra tek mesaj:

    SÜRÜM: ...
    NE DEĞİŞTİ: (en fazla 5 madde, sade dille)
    VERDİĞİM KARARLAR: (varsa, kısa gerekçeyle)
    SLO DURUMU: (değişen ya da hedefi tutmayan varsa)
    BENİM ADIMLARIM: (yoksa "yok")
    SIRADAKİ İŞ: ...

Haftada bir (cumartesi araştırmasından sonra) ek olarak "HAFTALIK ÖZET": SLO tablosu, doğrulanan gözlemler, açık sorunlar, araştırma sonuçları, sonraki haftanın planı. Teknik terimler sade dille açıklanır.
