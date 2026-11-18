# Çok yıllı strateji çerçevesi: QuantBIST 2029–2031

- **Belge no:** QB-STR-2031
- **Sürüm:** 1.0 (18.11.2026)
- **Sahibi:** kullanıcı
- **Uygulayıcı:** koordinatör

**Öncelik sırası:** [CHARTER](CHARTER.md) > kalıcı çerçeve ([OTONOM_KURALLAR](OTONOM_KURALLAR.md)) > [CHARTER_2028](CHARTER_2028.md) > bu belge.

**Yürürlük:** bu belge 2028 sonundaki değerlendirmeden önce yürürlüğe girmez. O zamana kadar yalnız yön gösterir.

> **Not (18.11.2026, Anayasa yürürlüğü, K-98):** Bu belgenin üstünde [ANAYASA](ANAYASA.md) vardır. Sıra: ANAYASA > CHARTER > kalıcı çerçeve > tüzük ve stratejiler > görev metinleri. Çelişen kısım geçersizdir.

## 0. Yönetici özeti
2031'in hedefi daha fazla özellik değildir. Hedef üç şeydir:
- kanıtlanmış bilginin korunması;
- sistemin en az bakımla yaşaması;
- sahibinin zamanının korunması.

Her yıl şu üç soruyla ölçülür:
- Bildiklerimiz kanıtlı mı?
- Sistem kullanıcı olmadan da ayakta kalır mı?
- Kullanıcıya maliyeti, sağladığı değere değer mi?

## 1. Senaryo planlaması
2028 sonu değerlendirmesine göre bir yol seçilir. Seçimi kullanıcı yapar.

**Senaryo A: doğrulandı.** S5 kâğıt sonuçları ön kayıtla uyumlu.
- **2029:** doğrulanmış kural farklı piyasa rejimlerinde izlenmeye devam eder. Yükselen, düşen, yatay ve yüksek oynaklık dönemleri ayrı ayrı raporlanır.
- **2030:** kuralın "yarı ömrü" ölçülür: etki zamanla azalıyor mu? Azalma eşiği ön kayıtlıdır; eşik aşılırsa kural emekliye ayrılır.
- Gerçek para kapsam dışı kalır. Bu konu açılacaksa, yalnız kullanıcı, lisanslı bir profesyonelle görüştükten sonra, ayrı bir projede açar.

**Senaryo B: olumsuz sonuç.** Anlamlı kural yok ya da kâğıt sonucu tutmadı.
- Proje "araştırma tamamlandı" raporuyla kapanır ve salt izleme moduna geçer.
- Bilgi korunur: neyin denendiği ve neden tutmadığı ayrıntılı bir "öğrenilen dersler" arşivine yazılır.
- Yeni bir hipotez ancak tamamen yeni bir ön kayıtla açılır. Eski verinin yeniden kazılması yasaktır.

**Senaryo C: kısmi.** Bazı kurallar belirli rejimlerde tutuyor.
- Yalnız ön kayıtta tanımlanmış rejim ayrımlarıyla devam edilir. Rejim tanımı sonradan uydurulmaz (çoklu test yanılgısı).
- 2029 sonunda C ya A'ya ya da B'ye dönüşür. Sonsuza kadar "kısmi" kalınmaz.

## 2. Stratejik sütunlar

**S-1. Model riski yönetimi** (bankacılıktaki model riski standartlarından uyarlanmıştır)
- Her kuralın bir model kartı vardır: amaç, veri, varsayımlar, bilinen zayıflıklar, doğrulama tarihi, emeklilik ölçütü.
- Kurallar yılda bir yeniden doğrulanır. Doğrulamayı kuralı geliştiren oturum değil, bağımsız bir oturum yapar.
- Model envanteri: hangi kuralın hangi aşamada olduğu (araştırma, kâğıt, emekli) tek bir tabloda görünür.

**S-2. Veri yönetişimi**
- Her veri kaynağının sahiplik ve lisans kaydı vardır. Lisansı belirsiz veri kullanılmaz.
- Veri kalitesi SLO'su yıl boyunca ölçülür. Kaynak kapanırsa yedek plan önceden yazılıdır.
- Veri saklama politikası yazılır: neyi, ne kadar süre, nerede saklıyoruz?

**S-3. İş sürekliliği ve bilgi koruma**
Sistem tek bir kişiye ve tek bir bilgisayara bağlıdır. 2029 sonuna kadar şunlar hazır olur:
- (a) bilgisayar arızasında sistemin başka bir makinede ayağa kalkması için bir kılavuz, süresi ölçülmüş;
- (b) "kullanıcı 3 ay ilgilenemezse" modu: sistem kendini güvenli izleme moduna alır, kimseye zarar vermez, kullanıcı dönünce kaldığı yerden devam eder;
- (c) sistemi teknik olmayan biri için anlatan tek sayfalık özet.

Yapay zekâ bağımlılığı: Claude modeli, kota ya da araçlar değişirse sistem çalışmaya devam etmeli. Kritik işler (veri, rapor, izleme) yapay zekâ olmadan da çalışır. Yapay zekâ geliştirme ve analiz içindir; çalışma anı için şart değildir.

**S-4. Teknoloji yaşam döngüsü**
- Bağımlılık envanteri tutulur: Python sürümü, kütüphaneler, servisler. Her birinin destek bitiş tarihi izlenir.
- Yılda bir planlı yükseltme penceresi açılır. Pencere sayaç dönemleriyle çakışmaz.
- Mimari sadelik bütçesi: yeni bir bileşen ancak bir başkası kaldırılırsa ya da açık bir gerekçesi yazılırsa eklenir.

**S-5. Etik ve uyum**
- Sistem hiçbir zaman başkasına yatırım tavsiyesi vermez, paylaşmaz, satmaz.
- Raporlar ölçülü bir dille yazılır: "kanıt şunu gösteriyor", "%95 güven aralığı şu". "Kesin kazanç" gibi ifadeler yasaktır.
- Mevzuat izlenir: SPK ve KVKK değişiklikleri yılda bir gözden geçirilir.

## 3. Aşama kapıları (her yılın sonunda)
| Kapı | Tarih | Geçme ölçütü | Geçmezse |
|---|---|---|---|
| G-2029 | 31.12.2029 | Senaryo netleşti; süreklilik kılavuzu tatbik edildi; model kartları tam | Kapsam daraltılır, bakım moduna geçilir |
| G-2030 | 31.12.2030 | Bağımsız yeniden doğrulamada KRİTİK bulgu yok; haftalık zaman ≤15 dk tutuyor | Sadeleştirme çeyreği zorunlu |
| G-2031 | 31.12.2031 | Strateji değerlendirmesi: devam, dönüştür ya da emekliye ayır | Karar kullanıcıya sunulur |

## 4. Performans göstergeleri (yıllık karne)
- **Kanıt:** ön kayıtlı sonuçların toplam sonuca oranı %100; yeniden üretim testi başarısı %100.
- **Güvenilirlik:** yıllık SLO uyumu; kök neden analizinin kapanma süresi.
- **Verimlilik:** kullanıcının haftalık süresi, robot kotası, açık bulgu sayısı.
- **Dürüstlük:** terk edilen hipotezlerin gerekçeli kayıt oranı %100.

## 5. Gözden geçirme
- Yıllık: strateji gözden geçirmesi, kapı kararı, risk kaydı ve tüzük güncellemesi.
- Bu belge her yıl yeniden yazılır, eskisi arşivlenir. Önceki belgede verilen sözlerin tutulup tutulmadığı bir tabloyla gösterilir.
