# Araştırma kaydı

Her test: hipotez, yöntem, önceden belirlenmiş başarı ölçütü, sonuç ve karar.
Başarısız sonuçlar da yazılır; silinmez. Ölçüt sonuç görüldükten sonra değiştirilmez.

**Ortak başarı ölçütü (2026-10-26'dan itibaren):** strateji, XU100'e göre günlük fazla
getirisinin blok bootstrap güven aralığı (Bonferroni düzeltmeli) tamamen sıfırın üstündeyse
"XU100'ü geçti" sayılır. Aday kurallar ayrıca üç kapıyı geçmelidir (iki başlangıç tarihi,
en kârlı 5 hisse hariç, walk-forward).

Haftalık otomatik çalışmaların tam metni ve özet tablosu GitHub'da `research-results` dalında
(`runs/<tarih>/`, `history.csv`). Bu dosyaya yalnızca yorum ve kararlar yazılır.

---



## 29.10.2026 – Senaryo şablonlarının karnesi (Özellik B §4.1; K-55; tanımlayıcı, hipotez değil)
`screens.yml`, v0.97.3. Tarama dönemi 2023-08-01 → 2026-10-30; holdout yok; BIST 100 geçmiş üyeliği; varsayılan eleme; maliyet sonrası (her yön %0,15). Şablonlar sonuçtan önce commit edildi (c7b25ea). R aralığı %95, 20 seanslık blok bootstrap.

| Şablon | Olay (hisse) | Hedef | Geçersizlik | Süre doldu | Ortalama R [%95] | En kötü seri | XU100'e göre | Dolmadı |
|---|---|---|---|---|---|---|---|---|
| Destek tepkisi | 1142 (145) | %49 | %48 | %2 | −0,15 [−0,23; 0,01] | 24 | −1,0 puan | 27 |
| Direnç kırılımı | 1742 (157) | %67 | %27 | %6 | +0,01 [−0,07; 0,06] | 8 | −0,1 puan | 184 |
| Trend içi geri çekilme | 5968 (143) | %64 | %29 | %7 | −0,00 [−0,05; 0,08] | 22 | +0,3 puan | 373 |

Okuma:
- Üç şablonun hiçbirinde maliyet sonrası ortalama R'nin sıfırdan farklı olduğu gösterilemedi; aralıkların hepsi sıfırı içeriyor. Destek tepkisi ortalamada en kötüsü.
- Yüksek hedef oranı (%64–67) kazanç anlamına gelmiyor. Hedefler yakın olduğu için hedefe ulaşmanın kazancı, geçersizlik kaybını ancak karşılıyor.
- Bu, K-49'un "seviyeler rastgeleden ayırt edilemedi" sonucuyla tutarlı.
- İlk karne (v0.97.1) ile fark: boşluklu açılışlar artık "dolmadı" (K-55 eki). Rakamların yönü aynı kaldı.
- Şablon parametreleri bu sonuca göre değiştirilmeyecek (K-55). "İşe yarıyor" iddiası yalnız a5 döngüsüyle (ön kayıt, bütçe, holdout; en erken 28.04.2027) sınanabilir.

## 29.10.2026 – Dört baz gerçek veride doğrulandı (Talimat C; ek bilgi, hipotez değil)
Araştırma çalışması `runs/2026-10-29_02-44`, v0.95.7. Dönem 01.08.2023 → 27.10.2026. XU100 al-tut:
- nominal +%55,6;
- reel −%51,9 (TÜFE 09.2026'ya kadar);
- USD −%15,7;
- nakde göre −%53,3.

Elle kontrol:
- TÜFE zinciri (07.2023–09.2026) 3,2315 kat → 1,556 / 3,2315 − 1 = −%51,8.
- Kur yaklaşık 26,9 → 49,70 (TCMB bülteni) → 1,556 / 1,848 − 1 = −%15,8.

İkisi de raporla tutarlı. İlk denemedeki +%383'lük USD hatası (Ö34) kapanmış görünüyor.

Okuma: bu dönemde XU100 TL olarak yükseldi, ama enflasyona, dolara ve politika faiziyle tutulan nakde göre geride kaldı. Stratejilerin hiçbiri reel olarak pozitif değil (en iyisi trend kuralı, reel −%10,9). Birincil ölçüt (XU100'e göre fazla getiri) ve önceki ret kararları değişmez.

## Reddedilen fikir türleri — özet (27.10.2026, MATURITY S4)

Aşağıdaki kayıtların özeti; ayrıntı ve sayılar ilgili bölümlerde. 2023-08 – 2026-10 arasında (yaklaşık 3,2 yıl, geçmiş BIST 100 üyeliği, maliyet dahil) test edilen 13 kuralın (6 ana tablo, 4 aday kural, Aşama 3'ün 3 hipotezi) hiçbiri XU100'ü istatistiksel olarak geçmedi. Aynı veride bu türlerin yeni varyantlarını denemek veri gözetlemesi olur; bu yüzden **yeniden denenmez**.

| Tür | Denenenler | Neden reddedildi | Ders |
|---|---|---|---|
| Teknik sinyal / puan | bot sinyali, bot sinyali + rejim, `/performans` görünümleri | Fazla getiri aralığı sıfırı içine alıyor (−1,5% [−28%, +23%]); "pozitif" görünümler 20 seansta XU100'ün altında (−0,2 puan), isabet %41–46 | Görünümler yalnız "negatif daha kötü" diyor; alım gerekçesi olamaz |
| Tek hissede trend takibi / kırılım | trend kuralı, weekly_trend, breakout, dryup_breakout, grouped_score | Nokta tahmini yüksek (+34,6%) ama aralık çok geniş; en kârlı 5 hisse çıkınca negatif (−5,2%); düşüş XU100'ün iki katı | Kazanç birkaç hisseye bağlı → "en kârlı 5 hariç" kapısı zorunlu |
| Kesitsel momentum | 6 ay en iyi 10, + rejim, walk-forward | Negatif ya da kararsız; 2025 +88%, 2026 −73% | Rejime aşırı bağlı; 12-1 gibi türevleri denenmez |
| Düşük oynaklık (H1) | 60 seans oynaklığı en düşük 10 | +0,9% [−16,5%, +18,6%]; düşüş XU100'den 11 puan derin | Literatürdeki dayanıklı anomali bu dönemde görünmedi |
| Endeks zamanlaması (H2 trend, H3 ay dönümü) | 200 günlük ortalama; ayın son/ilk 3 seansı | Aralıklar sıfırı içine alıyor; H3'ün kazancı neredeyse tamamen nakdin faizinden (%0 nakitle +1,4%) | Yüksek TL faizinde nakitte beklemek "zamanlama" gibi görünür; nakit getirisi ayrı ölçülmeli |
| Veriyi düzelterek sonucu iyileştirmek | yalnız kapanış düzeltmeleri | 635 düzeltmenin 448'i yapay mum üretiyor; sonuç farkı küçük | Kapanış düzeltmeleri kapalı; düzeltme yalnız onaylı ve kaynaklı (`price_fix_approvals.csv`) |

**Ortak sınır:** 3,2 yıllık veriyle güven aralıkları ±20–30 puan genişliğinde; yıllık 10 puanın altındaki gerçek bir üstünlük bu veriyle şanstan ayrılamaz. Daha uzun veri (2015'e uzatma) kaynak yokluğundan engelli (DECISIONS K-16). Bu yüzden yeni bir hipotez ancak yeni plan + kullanıcı onayı + holdout dönemiyle denenir ([RESEARCH_PROGRAM](RESEARCH_PROGRAM.md): bütçe, ileri holdout); asıl bağımsız kanıt canlı ölçümdür (ilk karar Kasım sonu).

---

## 2026-10-26 — Araştırma tablosu, geçmiş BIST 100 üyeliğiyle (v0.24.0)

- **Soru:** Bugünkü hisse listesiyle yapılan testler (survivorship bias) sonuçları ne kadar
  değiştiriyor? Hiçbir strateji XU100'ü istatistiksel olarak geçiyor mu?
- **Yöntem:** 2023-08-01 – 2026-10-23, komisyon %0,10 + kayma %0,05 her yön, nakit %0.
  Evren: 2022'den beri BIST 100'e girmiş 202 hisse, her gün yalnızca o günkü üyeler alınabilir;
  12'sinin verisi yok (çoğu spor kulübü). 6 strateji → %99,2 Bonferroni güven aralığı.
- **Kaynak:** GitHub Actions Research çalışması 40319864774.

| Strateji | Yıllık (geçmiş üyelik) | Yıllık (bugünkü liste) | XU100'e göre fazla getiri, %99,2 GA | Karar |
|---|---|---|---|---|
| Bot sinyali | +12,4% | +7,5% | −1,5% [−28,2%, +23,3%] | anlamlı değil |
| Bot sinyali + rejim | +10,8% | +3,4% | −3,6% [−35,2%, +26,2%] | anlamlı değil |
| Trend kuralı | +34,6% (MaxDD −48,5%) | +17,0% | +17,5% [−32,0%, +60,9%] | anlamlı değil |
| Momentum 6 ay, en iyi 10 | −16,6% | −9,5% | −28,9% [−132%, +39%] | anlamlı değil |
| Momentum + rejim | −12,6% | −2,5% | −24,0% [−142%, +51%] | anlamlı değil |
| Momentum walk-forward | +23,5% | +20,0% | +9,3% [−48,3%, +57,8%] | anlamlı değil |
| XU100 al-tut | +14,6% (MaxDD −26,5%) | | | |

- Walk-forward (geçmiş üyelik): XU100'ü geçen pencere 3/7, medyan test +%18,2,
  en iyi pencere hariç toplam +%12,9. Son pencere (2026-08 → 10) −%50,9 (XU100 −%17,1).
- Aday kurallar (190 hisse): weekly_trend ve dryup_breakout 1. ve 3. kapıyı geçti, ancak
  en kârlı 5 hisse çıkarılınca 2023 başlangıcında XU100'ün altına düştü (2. kapı ✗).
  Kazanç az sayıda hisseye bağlı. grouped_score ve breakout kapıları geçemedi.
- **Karar:** Hiçbir strateji XU100'ü istatistiksel olarak geçmedi. Hiçbiri sinyal olarak
  sunulmaz. Trend kuralının nokta tahmini yüksek ama aralık çok geniş ve düşüşü XU100'ün
  neredeyse iki katı; yalnızca izlenecek aday.

**Yöntem hatası, düzeltildi:** Bu çalışmadan önce GitHub iş akışı yalnızca bugünkü 117 hissenin
verisini indiriyordu; "geçmiş üyelik" testlerinde 202 eski üyenin 90'ı sessizce dışarıda
kalıyordu (`candidates --pit` dahil). Önceki `--pit` sonuçları bu yüzden geçersizdir.
İş akışı artık `--bist100-history` ile indiriyor ve eksik oran %10'u aşarsa rapor uyarıyor.

**Kalan sınırlar:** ~5 yıllık Yahoo verisi (yaklaşık 3 yıllık test dönemi), tek veri kaynağı,
2022 öncesi üyelik yaklaşık (değişiklik listesi 2022'de başlıyor), nakit getirisi %0.

---

## 2026-10-26 — İkinci kaynakla fiyat kontrolü (v0.31.0)

- **Soru:** Yahoo'dan gelen günlük kapanışlarda bağımsız bir kaynakla çelişen gün var mı?
- **Yöntem:** son 30 gün, 118 hisse; İş Yatırım fiyat geçmişi (HisseTekil, işlem fiyatı) ile
  günlük getiri karşılaştırması, eşik 1 puan. Seviye değil getiri karşılaştırılır, çünkü Yahoo
  fiyatları temettüye göre düzeltilmiştir.
- **Sonuç** (Research çalışması 40333047256): tutarlı 117, fark 0, kontrol edilemedi 1 (KPOWR:
  iki kaynakta da veri yok). "Tutarlı" sonucu, İş Yatırım'daki her günün Yahoo'da da bulunduğunu
  ve getirilerin 1 puan içinde olduğunu gösterir (ortak gün yoksa artık "kontrol edilemedi" sayılır).
- **Karar:** son 30 günde veri hatası bulunmadı. Kontrol her hafta tekrarlanır; daha uzun geçmiş
  (2022 sonrası) için ayrı bir tarama yapılabilir (hisse başına ~12 sn).

---

## 2026-10-26 — Uzun dönem fiyat kontrolü (2022 – bugün), ilk bulgular (v0.32.1)

- **Soru:** Backtestlerin kullandığı fiyatlarda (Yahoo, şirket işlemi düzeltmeli) araştırma
  sonuçlarını bozacak hata var mı?
- **Yöntem:** İş Yatırım fiyat geçmişiyle günlük getiri karşılaştırması; bağımsız üçüncü kaynak
  olarak haber ajansı kapanışları.
- **Bulgu 1 — XU100 doğru:** Yahoo'nun XU100'ü, İş Yatırım'ın BIST 100 değeriyle 1202 günün hepsinde
  tutarlı. AA'ya göre 06.01.2023'te BIST 100 +%4,41 (5.341,96); iki kaynak da bunu gösteriyor.
- **Bulgu 2 — Yahoo'da tek günlük yanlış kapanışlar:** bazı günlerde hisse kapanışı yanlış
  kaydedilmiş ve ertesi gün düzelmiş; iki günün toplam getirisi doğru. Örnek GARAN: 05.01.2023 Yahoo
  −%3,6 (gerçek −%10, taban), 06.01.2023 Yahoo −%2,4 (gerçek +%4,5). Aynı gün çok hissede:
  10.05.2022, 17.11.2022, 05.01.2023. 5 büyük hissede 2022'den beri 20 böyle gün.
  - Etki: uzun dönem getiriler bozulmaz (seviye kayması yok); o günün kapanışından üretilen sinyal
    ve göstergeler bozulabilir. Çoğu 2022 – Ocak 2023'te, yani araştırmanın test döneminden
    (2023-08 sonrası) önce, ama walk-forward eğitimi ve 2022/2023 başlangıçlı aday testlerini etkiler.
- **Bulgu 3 — düzeltilmemiş bölünme/bedelsizler:** ADEL, BJKAS, EUREN, CVKMD, TSPOR'da Yahoo'da
  gerçekte olmayan %28–%91 düşüşler. %20 sıçrama kuralı bu hisseleri zaten araştırma dışı bırakıyor;
  kural doğru çalışıyor. KCAER (28.11.2024, Yahoo −%13,7, gerçek −%0,2) eşiğin altında kalıp
  araştırmaya giriyor: düzeltme adayı.
- **Bulgu 4 — eksik günler:** 09.04.2024 (Ramazan arifesi, yarım gün) çoğu hissede Yahoo'da yok;
  bazı yeni halka arzların ilk 25–164 günü Yahoo'da yok.
- **Karar (şimdilik):** sinyal üretimi için yanlış kapanış günlerinin etkisi ölçülmeden veri
  değiştirilmeyecek. Tüm hisseler için tam tarama sonucu aşağıda.

---

## 2026-10-27 — Tam fiyat taraması sonucu (2022 – bugün, 202 hisse)

- **Kaynak:** Data check çalışması 40377105196; rapor ve düzeltme dosyası `research-results` dalında
  `datacheck/2026-10-27_00-08*`. 218.752 hisse-gün karşılaştırıldı.
- **XU100:** 1202 günün hepsinde tutarlı.
- **Tek gün yanlış kapanış (Yahoo, ertesi gün düzelen):** 635 hisse-gün. Çok hissede aynı gün:
  10.05.2022 (77), 27.06.2022 (61), 16.12.2022 (86), 05.01.2023 (158), 08.05.2025 (55).
  Düzeltme oranları `datacheck/latest_price_fixes.csv`'de (635 satır); etkileri araştırmada ayrıca ölçülür.
- **Hisseye özgü hatalar:** 33 gün. %20'yi aşanlar (ADEL, BJKAS, CVKMD, EUREN, FENER, GSRAY, TSPOR,
  TUKAS, ASUZU) zaten araştırma dışında; dışlama kuralı tam olarak bu hisseleri yakalıyor.
  Araştırmaya giren ve kalıcı seviye hatası yaratan iki hisse düzeltildi (`data/corporate_actions.csv`):
  - KCAER 28.11.2024: %191,22 bedelsiz; Yahoo −%13,7, İş Yatırım −%0,2 → oran 0,8650.
  - CANTE 26.01.2026: Yahoo −%15,9, İş Yatırım %0,0; bedelli (03.02.2026) Yahoo'da erken tarihe
    konmuş → oran 0,8408.
  Kalan farklar 1–4 puanlık tek günlük farklar (çoğu tavan/taban günlerinde yuvarlama); düzeltilmedi.
- **Yahoo'da eksik günler:** 09.04.2024 (yarım gün) çoğu hissede yok; ASGYO (164), BINHO (87), AVPGY (65)
  gün gibi yeni halka arzların ilk dönemleri yok.
- **Kontrol edilemedi:** CEMAS, GESAN, HEKTS (İş Yatırım geçersiz yanıt), KERVT (veri yok).

---

## 2026-10-27 — Fiyat düzeltmelerinin araştırma sonuçlarına etkisi

- **Soru:** 635 tek günlük yanlış kapanış ve KCAER/CANTE düzeltmeleri sonuçları değiştiriyor mu?
- **Yöntem:** aynı çalışmada araştırma tablosu düzeltmesiz (`research.txt`) ve 635 kapanış
  düzeltmesiyle (`research_fixed.txt`) hesaplandı (Research çalışması 40402066393,
  `runs/2026-10-27_00-10/`). KCAER/CANTE satırları her iki tabloda da uygulanmış durumda.
- **Sonuç:** kapanış düzeltmeleri bot sinyalini +%12,4'ten +%13,5'e çıkarıyor (XU100'e göre −1,5 → −0,6
  puan); diğer stratejiler ±0,1 puan. Hiçbir karar değişmiyor: hepsi "anlamlı değil". Aday kural
  kapıları da aynı (weekly_trend ve dryup_breakout 1. ve 3. kapıyı geçiyor, 2. kapıda kalıyor).
  KCAER/CANTE düzeltmesi tabloyu ölçülebilir biçimde değiştirmedi.
- **Karar:** tek günlük kapanış hataları araştırma sonuçlarını değiştirmiyor; varsayılan veriye
  uygulanmayacak (düzeltme katmanı kapalı kalır, haftalık çalışma etkiyi izlemeye devam eder).
  Eksiksiz bir backtest verisinin kanıtı bu tarama değil, iki kaynaktaki tutarlılıktır: XU100 ve
  hisse getirileri 2022'den beri, bilinen ve ölçülmüş istisnalar dışında, İş Yatırım ile örtüşüyor.
- **Gözlem:** 27.10.2026 00:10'daki çalışmada Yahoo 26.10 gününü döndürmedi (21:22'deki çalışma
  döndürmüştü); son 30 günlük ikinci kaynak kontrolü bunu "yalnız İş Yatırım'da: 26.10" olarak
  yakaladı. Gece yarısı civarı Yahoo verisi geçici olarak eksik olabilir; cumartesi 07:17 çalışması
  bundan etkilenmez.

---

## 2026-10-27 — Senaryolar A–D, yoğunlaşma ve mum tutarlılığı (v0.39.0)

- **Soru:** Veri düzeltmeleri sonuçları değiştiriyor mu? Sonuçlar az sayıda hisseye mi bağlı?
- **Yöntem:**
  - Senaryolar çalışması 40410635317, sonuçlar `research-results` dalında `scenarios/2026-10-27_01-15.txt`.
  - Dönem 2023-08-01 – 2026-10-23, geçmiş BIST 100 üyeliği, 10 pozisyon, komisyon + kayma %0,15 her yön.
  - Fiyat deposunun SHA-256 özeti çalışmadan önce ve sonra aynı (04d00b31294b): deney depoyu değiştirmedi.
- **Senaryolar:**
  - B, A ile aynı: KCAER/CANTE satırları bu stratejilerde hiçbir işlemi değiştirmiyor.
  - C/D'de bot sinyali yıllık +%12,4'ten +%13,5'e çıkıyor (+5 / −7 işlem). Trend kuralında 1 işlem değişiyor. Momentum aynı kalıyor.
- **Yoğunlaşma (A):** üç stratejide de en kârlı 5 hisse çıkarılınca sonuç negatife dönüyor.

  | Strateji | Yıllık | En kârlı 5 hisse olmadan |
  |---|---|---|
  | Bot sinyali | +%12,4 | −%2,9 |
  | Trend kuralı | +%34,6 | −%5,2 |
  | Momentum | −%16,6 | −%21,3 |

  En kârlı 5 hisse kârlı işlemlerden gelen kârın %57–71'ini oluşturuyor. MAGEN, KTLEV ve ASELS üç stratejinin listesinde de var.
- **Yıllar:**

  | Strateji | 2023 (Ağu–Ara) | 2024 | 2025 | 2026 |
  |---|---|---|---|---|
  | Bot sinyali | −%4,5 | +%34,6 | +%46,2 | −%22,4 |
  | Trend kuralı | +%2,0 | +%35,7 | +%62,4 | +%16,1 |
  | Momentum | −%2,8 | +%12,6 | +%88,1 | −%72,9 |
  | XU100 | +%4,2 | +%31,6 | +%14,6 | −%1,3 |

  Trend kuralı 2024–2026'da XU100'ün üstünde, 2023'te altında. Bu fark birkaç hissenin getirisinden geliyor.
- **Mum tutarlılığı:** düzeltmeler uygulanmış depoda (190 hisse, 217.560 gün):
  - 6 gün kapanış o günün aralığı dışında;
  - imkânsız mum (en yüksek < en düşük ya da açılış aralık dışında) yok;
  - 240 gün hacim 0.

  Yahoo mumları kendi içinde tutarlı. Yanlış kapanış günlerinde mumun tamamı yanlış. Bu yüzden yalnız kapanışı düzeltmek, 635 düzeltmenin 448'inde yapay mum üretir.
- **Karar:**
  - Kapanış düzeltmeleri kapalı kalır.
  - Hiçbir strateji sinyal olarak sunulmaz.
  - Sonuçlar bağımsız bir dönemde (canlı ölçüm) tekrar etmeden "çalışıyor" denmez.
  - Yeni kurallar en az "en kârlı 5 hisse hariç" kapısını geçmelidir. Aday kurallarda bu kapı zaten var; ana tablodaki stratejilerin hiçbiri bu kapıyı geçmiyor.

---

## 2026-10-27 — Teknik görünümlerin geçmiş sonucu (`/performans` referansı, v0.45.14)

- **Kaynak:** Research çalışması 40415685951 (v0.44.0), `runs/2026-10-27_01-52/`.
  - Geçmiş BIST 100 üyeliği, 190 hisse, 2023-08-01 – 2026-10-16.
  - Yöntem: ertesi seansın açılışında alıp 5/20/60 seans tutmak; sonuç XU100'e göre fark.
- **Sonuç (20 seans):**

  | Görünüm | XU100'e göre fark |
  |---|---|
  | Güçlü pozitif | −%0,28 |
  | Pozitif | −%0,17 |
  | Nötr | −%0,80 |
  | Negatif | −%0,87 |
  | Güçlü negatif | −%2,04 |

  İsabet oranı %41–46. Pozitif görünümler XU100'ü geçmiyor; yalnız negatif görünümler daha kötü sonuç veriyor. Bu, mevcut "tahmin gücü kanıtlanmadı" kararıyla tutarlı.
- **Karar:** dosya `data/view_expectations.csv` olarak eklendi (kullanıcı kararı, 27.10.2026). Bu değerler karşılaştırma için referanstır, kanıt değildir. Hiçbir kural bu sonuca göre ayarlanmadı.
- **Not:** dosya KCAER katsayısı 0,8650 iken üretildi (v0.45.13'te 0,8646 oldu). Fark tek bir hissenin 28.11.2024 öncesi fiyatlarında %0,05; sonuçlar ölçülebilir biçimde değişmez. Dosya bir sonraki elle yenilemede güncellenecek.

---

## Aşama 3 planı — ONAYLANDI (kullanıcı, 27.10.2026; değiştirilmez)

Bu bölüm, **hiçbir test çalıştırılmadan önce** yazıldı. Onaylandıktan sonra hipotezler, parametreler ve başarı ölçütleri değiştirilmez. Sonuçlar ne çıkarsa çıksın bu bölümün altına eklenir; olumsuz sonuçlar da silinmez.

### Şu ana kadar bilinenler (yeni hipotezler bunlara göre seçildi)

- Daha önce 6 kural test edildi: bot sinyali, bot sinyali + rejim, trend kuralı, 6 aylık momentum, momentum + rejim, momentum walk-forward. Hiçbiri XU100'ü istatistiksel olarak geçmedi.
- Hepsinin kârı en kârlı 5 hisseye bağlı (RESEARCH_LOG, 27.10).
- Bu kurallar ve onların türevleri (ör. 12-1 momentum) yeniden denenmeyecek; aynı veride tekrar tekrar test etmek veri gözetlemesi olur.

### Hipotezler (3 adet; parametreler sabit, ayar yapılmayacak)

| # | Hipotez | Kural | Neden aday |
|---|---|---|---|
| H1 | Düşük oynaklık | Her ayın ilk seansında, o gün BIST 100 üyesi olan hisselerden son 60 seans günlük getiri oynaklığı en düşük 10 hisse, eşit ağırlıkla alınır ve bir ay tutulur | Literatürde en dayanıklı anomalilerden biri; şimdiye kadar test edilen kuralların hiçbirine benzemiyor |
| H2 | Endeks trendi (zaman serisi) | Her ayın ilk seansında XU100 son 200 seans ortalamasının üstündeyse endeks (XU100) tutulur, altındaysa nakit | Kayıpları sınırlamaya yönelik basit ve yaygın bir kural; tek hisse seçimine dayanmıyor, bu yüzden 5 hisse yoğunlaşma sorunu yok |
| H3 | Ay dönümü | XU100 yalnız her ayın son 3 ve ilk 3 seansında tutulur; diğer günlerde nakit | Takvim etkisi; az işlem, tek parametre |

### Ön koşul

H2 ve H3 zamanın bir kısmında nakitte bekliyor. Nakit getirisi %0 alınırsa bu iki kural haksız yere kötü görünür, çünkü TL mevduat faizi yüksek. Bu yüzden testten önce:
- `data/cash/` klasörüne bir para piyasası fonunun TEFAS birim fiyatları kaynağıyla eklenir.
- Stopaj tablosu da eklenir.

Bu veri kamuya açık; hesap ya da ödeme gerekmiyor. Veri eklenemezse H2 ve H3 test edilmez ve bunun nedeni buraya yazılır.

### Ortak test kuralları

- **Dönem ve evren:** 2023-08-01 – son kapanış, geçmiş BIST 100 üyeliği, mevcut veri ve düzeltmeler (kapanış düzeltmeleri kapalı).
- **Maliyet:** her yönde komisyon %0,10 + kayma %0,05.
- **Başarı ölçütü (birincil):** XU100'e göre fazla getirinin blok bootstrap güven aralığı (21 seanslık bloklar) tamamen sıfırın üstünde olmalı. Bonferroni düzeltmesi 3 hipotez için yapılır (%98,3). Daha önceki 6 test ayrı bir aile olarak kayıtlı.
- **Sağlamlık kapıları:** üçü de geçilmeli.
  1. İki başlangıç tarihinde de (2023-08-01 ve 2024-01-02) XU100'ü geçmeli.
  2. H1 için: en kârlı 5 hisse çıkarılınca da XU100'ü geçmeli. H2 ve H3 endeks tuttuğu için bu kapı uygulanmaz; onun yerine dönemdeki 4 takvim yılının en az 3'ünde XU100'ü geçmeli.
  3. En büyük düşüş (MaxDD) XU100'ünkinden kötü olmamalı.
- **Kabul edilirse:** kural yalnız canlı ölçüme ve sanal hesaba alınır. Gerçek para ya da gerçek emir yok. Karar en erken 6 aylık canlı ölçümden sonra verilir.
- **Kabul edilmezse:** sonuç buraya yazılır. Kural ayarlanıp yeniden denenmez.

### Uygulama sırası (onaydan sonra)

1. Nakit verisi (TEFAS) ve stopaj tablosu eklenir; testli.
2. H1–H3 kuralları eklenir. Her kural için ileriye bakmama testi (`test_no_lookahead`) ve el hesabıyla küçük bir örnek testi yazılır.
3. Haftalık araştırma iş akışına ayrı bir tablo olarak eklenir. `history.csv`'ye ayrı bir aile adıyla yazılır.
4. İlk sonuç buraya, olduğu gibi yazılır.

### Nakit verisi: fon seçim kuralı ve stopaj (veri indirilmeden önce yazıldı, 27.10.2026)

- **Fon seçimi:** 31.07.2023 tarihinde TEFAS'ta unvanında "PARA PİYASASI" geçen yatırım fonları arasından portföy büyüklüğü en yüksek olan fon. Bu kural sonuca bakmadan sabitlendi; seçilen fonun getirisi seçimde rol oynamaz. Seçilen fonun 2023-08-01'den sonraki her işlem gününde fiyatı yoksa, kurala göre bir sonraki en büyük fon alınır ve bu durum buraya yazılır.
- **Fiyat:** TEFAS'ın günlük birim fiyatı. Fon yönetim ücreti fiyatın içindedir.
- **Stopaj (gerçek kişi, para piyasası fonu):** dönemler ve oranlar aşağıda.

  | Dönem | Oran |
  |---|---|
  | 23.12.2020 – 30.04.2024 | %0 |
  | 01.05.2024 – 31.10.2024 | %7,5 |
  | 01.11.2024 – 31.01.2025 | %10 |
  | 01.02.2025 – 08.07.2025 | %15 |
  | 09.07.2025 sonrası | %17,5 |

  Kaynaklar ikincil: Ziraat Bankası vergilendirme tablosu, İş Portföy ve Oyak Portföy duyuruları, KPMG ve Fintables yazıları. Resmî Gazete metniyle doğrudan doğrulanamadı; bu ortamdan erişilemedi.
- **Stopajın uygulanışı:** gerçekte oran, payın alındığı tarihe göre belirlenir. Backtest bunu, `core/backtest/cash.py`'nin yaklaşımıyla, o günkü oranın günlük kazanca uygulanması olarak hesaplar. Bu basitleştirme nakit getirisini biraz düşük gösterebilir; nakitte bekleyen kurallar için bu tutucu taraftadır.
- **Duyarlılık:** sonuçlar ayrıca stopajsız (brüt) nakit getirisiyle de raporlanır. Karar birincil hesaba (stopajlı) göre verilir.

### Nakit verisi alınamadı: H2 ve H3 test edilmiyor (27.10.2026)

- **Deneme:** Cash data çalışması 40463364732. TEFAS'ın eski veri adresi (`/api/DB/BindHistoryInfo`) 404 döndü.
- **Neden:** TEFAS Nisan 2026'da yeni bir altyapıya geçti. Yeni API (`/api/funds/...`) fon başına yalnız fiyat veriyor; **portföy büyüklüğünü artık yayımlamıyor**. Kaynaklar: tefas-crawler 0.6.0 kaynak kodu ve açıklaması, turkeyfundsdata, borsapy notları.
- **Sonuç:** önceden yazılan fon seçim kuralı ("31.07.2023'teki en büyük para piyasası fonu") uygulanamıyor. Fonu getirisine bakarak seçmek, bu planın önlemeye çalıştığı seçim yanlılığını doğurur.
- **Karar:** onaylanan plandaki hüküm gereği **H2 ve H3 test edilmiyor**. H1 her zaman hisselerde durduğu için nakit verisine ihtiyaç duymuyor; H1 planlandığı gibi test edilecek.
- **Açık seçenek:** H2 ve H3, başka bir nakit kaynağıyla test edilebilir; örneğin TCMB politika faizi kararları, her biri kaynağıyla. Bu, planda değişiklik demektir; ancak kullanıcı onayıyla yapılır. Değişiklik, H1 sonucu görülmeden önce önerildi.
- **Temizlik:** TEFAS indiricisi (`core/backtest/tefas.py`) ve `cashdata.yml` iş akışı kaldırıldı. Stopaj tablosu (`data/cash/withholding.csv`) kaynaklarıyla birlikte duruyor; başka bir nakit kaynağı onaylanırsa kullanılacak.

### Aşama 3 – H1 ilk sonuç: RED (27.10.2026)

Research çalışması 40464071625 (kod v0.47.0, `runs/2026-10-27_09-56/phase3.txt`; history.csv'de `a3` ailesi). Sonuç olduğu gibi:

| | 2023-08-01'den | 2024-01-02'den |
|---|---|---|
| Kural, yıllık | +15,9% | +12,0% |
| XU100, yıllık | +14,6% | +14,4% |
| Kural MaxDD | −37,7% | −37,7% |
| XU100 MaxDD | −26,5% | −26,5% |
| Sharpe / işlem | 0,73 / 161 | 0,61 / 140 |

- XU100'e göre fazla getiri (yıllık, %98,3 GA, Bonferroni 3 hipotez): **+0,9% [−16,5%, +18,6%] anlamlı değil**.
- En kârlı 5 hisse (BIMAS, CCOLA, REEDR, AEFES, SELEC) olmadan yıllık +6,1%.
- Birincil ölçüt ✗, kapı 1 ✗ (ikinci başlangıçta XU100'ün altında), kapı 2 ✗, kapı 3 ✗ (düşüş XU100'den 11 puan derin).

**Karar:** H1 reddedildi. Plan gereği kural ayarlanmaz (pencere, hisse sayısı, yeniden dengeleme sıklığı denenmez); canlı ölçüme alınmaz. Kod ve haftalık kayıt, yalnızca sonraki çalışmalarda sonucun değişip değişmediğini görmek için kalır.

**Aşama 3'ün durumu:** H1 red; H2 ve H3 nakit verisi olmadığı için test edilmedi. Önceden onaylanmış başka hipotez yok. H2/H3 için başka bir nakit kaynağı (örneğin TCMB politika faizi) ancak kullanıcı onayıyla, plan değişikliği olarak eklenebilir. Bu seçenek H1 sonucu görülmeden önce yazılmıştı; H1'in reddi onu güçlendirmez de zayıflatmaz da.

### Plan değişikliği 1 – H2 ve H3 için nakit: TCMB politika faizi (kullanıcı onayı 27.10.2026)

Bu bölüm, faiz verisi indirilmeden ve H2/H3'ün hiçbir sonucu görülmeden yazıldı. Hipotezler, dönem, maliyet, Bonferroni düzeyi (3 hipotez) ve kapılar değişmez. Değişen tek şey nakdin kaynağı; ek olarak kabulü **zorlaştıran** bir koşul eklenir.

- **Nakit getirisi:** TCMB politika faizi (bir hafta vadeli repo ihale faizi), `data/cash/policy_rate.csv`. Her satır bir PPK kararı ve kaynağı (TCMB basın duyurusu).
  - Yürürlük tarihi: kararın açıklandığı günden sonraki iş günü.
  - Yalnız açıklanan politika faizi kullanılır. Fonlamanın geçici olarak başka bir faizden yapıldığı dönemler (ör. Mart–Nisan 2025) ayrıca modellenmez; bu durum veri dosyasına not düşülür.
- **Net getiri:** brüt faiz × (1 − stopaj). Stopaj tablosu `data/cash/withholding.csv` (değişmedi). Faiz basit yıllık, takvim günü üzerinden işler (`core/backtest/cash.py`, RateSeries).
- **Neden üst sınır sayılır:** bireysel yatırımcı politika faizini birebir alamaz; bir para piyasası fonu bu faizin biraz altında, ücretler düşülmüş olarak kazanır. Bu yüzden nakit getirisi H2/H3 lehine fazla gösterilebilir.
- **Ek koşul (yalnız kabulü zorlaştırır):** H2 veya H3, birincil ölçüt ve üç kapıyı **politika faizi − 3 puan** ile de geçmelidir; ikisinden birinde kalırsa red.
- **Bilgi amaçlı (karara girmez):** %0 nakitle sonuç da yazılır.
- **Uygulama ayrıntıları (şimdiden sabit):**
  - Kurallar XU100 endeksini aynı maliyetle (her yönde %0,10 + %0,05) alıp satar. Gerçekte bu bir endeks fonu ya da vadeli işlemle yapılır; takip farkı yok sayılır.
  - Emirler, her kuralda olduğu gibi, sinyal gününün ertesi seansının açılışında gerçekleşir.
  - **H2:** ayın son seansının kapanışında XU100 > son 200 seans kapanış ortalaması ise endeks tutulur; ertesi ayın ilk seansının açılışında işlem yapılır.
  - **H3:** ayın sondan 4. seansının kapanışında giriş sinyali verilir (alım sondan 3. seansın açılışında). Ertesi ayın 3. seansının kapanışında çıkış sinyali verilir (satış 4. seansın açılışında). Seans günleri borsa tatil takviminden (`data/bist_holidays.csv`) alınır; bu takvim önceden yayımlanır, ileriye bakma sayılmaz.
  - **Kapı 2 (H2/H3):** takvim yılları 2023 (01.08'den), 2024, 2025, 2026 (son kapanışa kadar); en az 3'ünde XU100'ün üstünde.
- **Sonuç:** ne çıkarsa çıksın bu bölümün altına olduğu gibi yazılır. Kural ve faiz ayarı yapılmaz.
- **Uygulama notu (aynı gün, faiz verisi eklenmeden ve sonuç görülmeden önce):** `data/bist_holidays.csv` yalnız 2026'yı kapsıyor. H2 ve H3'ün ay sonu ve seans sırası için geçmiş aylarda **gerçekleşmiş seanslar** (XU100 mum tarihleri) kullanılır; son mumdan sonrası için tatil takvimi ve hafta içi günler kullanılır. 2023-08 sonrasında borsada önceden duyurulmamış bir kapanış bilinmiyor; bu yüzden gerçekleşmiş seanslar o dönem yayımlanmış takvimle aynıdır. Kurallar fiyatlara göre değil, yalnız tarihlere göre zamanlanır.

### Aşama 3 – H2 ve H3 ilk sonuç: RED (27.10.2026)

Research çalışması 40488966701 (kod v0.48.0, `runs/2026-10-27_13-30/phase3.txt`; history.csv'de `a3` ailesi). Dönem 2023-08-01 – 2026-10-26. Sonuç olduğu gibi:

| | H2 endeks trendi | H3 ay dönümü |
|---|---|---|
| Yıllık, 2023-08-01'den (XU100 +14,6%) | +21,2% | +27,1% |
| Yıllık, 2024-01-02'den (XU100 +14,5%) | +22,2% | +22,8% |
| MaxDD (XU100 −26,5%) | −22,5% | −11,3% |
| Fazla getiri, %98,3 GA | +4,9% [−9,1%, +20,2%] anlamlı değil | +8,1% [−17,1%, +35,3%] anlamlı değil |
| XU100'ün üstünde kalınan yıl | 2/4 | 3/4 |
| Piyasada kalma | %80 | %28 |
| Faiz − 3 puan ile fazla getiri | +4,4% [−9,6%, +19,5%] | +6,5% [−18,7%, +33,6%] |
| Bilgi: %0 nakitle yıllık | +12,3% | +1,4% |

- **H2:** birincil ölçüt ✗, kapı 1 ✓, kapı 2 ✗ (2/4 yıl), kapı 3 ✓. Faiz − 3 puanla da aynı sonuç. **Red.**
- **H3:** birincil ölçüt ✗, kapı 1 ✓, kapı 2 ✓, kapı 3 ✓. Faiz − 3 puanla da aynı sonuç. Birincil ölçüt tutmadığı için **red**.
- **Not (yorum, karara girmez):** H3'ün getirisinin neredeyse tamamı nakdin faizinden geliyor; %0 nakitle yıllık +1,4%. Yani bu dönemde XU100'ü geçmesi, ay dönümü etkisinden çok, yüksek TL faizinde zamanın %72'sini nakitte geçirmesinden kaynaklanıyor. Aralığın genişliği (yaklaşık ±26 puan) üç yıllık veriyle bu farkın şanstan ayrılamadığını gösteriyor.

**Karar:** H2 ve H3 reddedildi. Plan gereği kurallar ve faiz varsayımı ayarlanmaz, canlı ölçüme alınmaz. Haftalık araştırma bu üç hipotezi her hafta aynı biçimde yeniden hesaplar; sonuç değişirse yalnızca buraya not edilir, kendiliğinden kabul edilmez.

**Aşama 3 kapandı:** önceden kaydedilen üç hipotezin üçü de birincil ölçütü geçemedi. Bu veriyle (yaklaşık 3,2 yıl) XU100'den istatistiksel olarak ayrılan bir kural bulunamadı. Yeni hipotez, ancak yeni bir planla ve kullanıcı onayıyla denenir.

---

## a4 ön kaydı — ONAYLANDI (Claude, kullanıcının devriyle, 28.10.2026; değiştirilmez)

Bu bölüm, **iki kuralın hiçbiri hiçbir veride hesaplanmadan** yazıldı ve bu commit'le zaman damgalandı. Kullanıcı 28.10.2026'da hipotez onayını Claude'a bıraktı (DECISIONS K-28). Onaydan sonra hipotezler, parametreler, maliyet, ölçüt ve kapılar değiştirilmez; sonuç ne olursa olsun bu bölümün altına yazılır.

### Seçim gerekçesi

- "Reddedilen fikir türleri" tablosundaki türlerin (teknik sinyal, tek hissede trend/kırılım, geçmiş getiriye göre sıralama/momentum, düşük oynaklık, endeks ve takvim zamanlaması, veri düzeltmesi) hiçbir varyantı alınmadı. Geçmiş getiriye dayalı her sıralama (kısa vadeli dönüş, 52 hafta zirvesi, MAX etkisi gibi) bu ailenin türevi sayıldı ve dışarıda bırakıldı.
- Temel analiz verisi (F/K, PD/DD) ve temettü geçmişi sistemde yok. Bunlar veri olmadan ön kayda yazılmaz.
- **Bedelsiz sermaye artırımı etkisi** değerlendirildi ve alınmadı. `corporate_actions.csv`'de yalnız 16 satır var ve tarihler gerçek hak kullanım günü değil, Yahoo'daki sıçrama günü. Eksik ve kaydırılmış olay listesiyle olay çalışması yanıltıcı olurdu.
- Bütçe 3 hipotez; **2 hipotez** kullanılıyor. Az hipotez Bonferroni cezasını küçültür. Üçüncü hak bu döngüde kullanılmaz ve devredilmez.

### Hipotezler (parametreler sabit, ayar yapılmayacak)

| # | Hipotez | Kural | Neden aday |
|---|---|---|---|
| H4 | Eşit ağırlık | Her ayın ilk seansında, o gün BIST 100 üyesi olup fiyatı olan bütün hisseler eşit ağırlıkla alınır ve bir ay tutulur | XU100 piyasa değeri ağırlıklı; eşit ağırlık küçük üyelere daha çok pay verir. Sinyal ya da sıralama yok, parametre yok |
| H5 | Düşük işlem hacmi (likidite primi) | Her ayın ilk seansında, o gün BIST 100 üyesi olan hisselerden son 60 seansın günlük TL hacminin (kapanış × adet) medyanı en düşük 10 hisse eşit ağırlıkla alınır ve bir ay tutulur | Az işlem gören hissenin taşıma maliyetine prim ödendiği fikri (Amihud). Geçmiş getiriye ya da oynaklığa dayanmıyor |

### Test kuralları

- **Tarama dönemi ve evren:** 2023-08-01 – 30.10.2026 (`SCREEN_END`; holdout kodla kapalı), geçmiş BIST 100 üyeliği, Aşama 3 ile aynı fiyat temeli ve düzeltmeler (kapanış düzeltmeleri kapalı). İşlem ertesi seansın açılışında; Aşama 3 motoru (`core/backtest/phase3.py`) aynen.
- **Maliyet:** her yönde komisyon %0,10 + kayma %0,05.
- **Birincil ölçüt:** XU100'e göre günlük fazla getirinin blok bootstrap güven aralığı (21 seanslık bloklar) tamamen sıfırın üstünde. Bonferroni 2 hipotez için: **%97,5 GA**. a1–a3 ayrı aileler.
- **Sağlamlık kapıları:** hepsi geçilmeli.
  1. İki başlangıç tarihinde de (2023-08-01 ve 2024-01-02) XU100'ü geçmeli.
  2. Sonuç en kârlı 5 hisse çıkarılınca da XU100'ü geçmeli.
  3. MaxDD XU100'ünkinden kötü olmamalı.
  4. **Yalnız H5:** maliyet iki katına çıkınca (komisyon %0,20 + kayma %0,10 her yön) birincil ölçüt yine tutmalı. Az işlem gören hissede kayma büyüktür; bu kapı prim sanılanın aslında ödenemeyen maliyet olup olmadığını sınar.
- **Zaman:** Bütçe kuralı (6 ayda bir döngü, a3 27.10.2026) gereği tarama **27.04.2027'den önce çalıştırılmaz**. Kod bunu tarih kapısıyla zorlar; kapı açılmadan sonuç hesaplanmaz.
- **Holdout kararı:** Taramayı geçen kural, 02.11.2026'dan itibaren en az 250 seanslık ileri veriyle (en erken Kasım 2027) aynı kural, parametre ve ölçütle karara bağlanır. Tek yönlü test, Bonferroni holdout'a giren kural sayısına göre.
- **Kabul edilirse:** Kural yalnız canlı ölçüme ve sanal hesaba alınır. Gerçek para ya da emir yok, al/sat önerisi yok.
- **Kabul edilmezse:** Sonuç buraya yazılır, tür "Reddedilen fikir türleri" tablosuna eklenir, kural ayarlanıp yeniden denenmez.

### Uygulama sırası

1. ✅ (v0.67.0, 28.10.2026) H4 ve H5 kuralları ile tarih kapısı yazılır (`core/backtest/a4.py`, `core.strategy.rules.equal_weight_signals` / `low_turnover_signals`, `tests/test_a4.py`; haftalık araştırmada "a4" adımı, kapı açılana dek yalnız "çalıştırılmadı" yazar). Her kural için ileriye bakmama testi, el hesabıyla küçük bir örnek testi ve kapının testi eklenir. Bunlar yalnız yapay veriyle yapılır, gerçek veride sonuç hesaplanmaz.
2. 27.04.2027'den sonraki ilk haftalık araştırma çalışması taramayı yapar. `history.csv`'ye `a4` ailesi olarak yazılır.
3. İlk sonuç buraya olduğu gibi yazılır.

---

## Not — kullanıcı taramaları, keşif (28.10.2026; araştırma programı dışında)

Kullanıcının TradingView taramalarının teknik kısmı, PC'de keşif amaçlı denendi. Dönem 2023-08 – 30.10.2026, o günkü BIST 100 üyeleri, giriş ertesi açılış, XU100'e göre fazla getiri, **maliyet hariç**. 20 seans sonuçları:

| Tarama | Ortalama [aralık] | Olay |
|---|---|---|
| 06 Basit teknik | −%0,3 [−1,8; +1,7] | 516 |
| 08 Bebek (teknik) | −%0,0 [−1,4; +0,6] | — |
| 10 Düşeni kıran | −%0,9 [−3,0; +0,3] | 693 |
| Tek tuş trend (teknik) | +%0,5 [−0,8; +1,3] | 1249 |
| 05 (EMA kısmı) | +%0,3 [−0,7; +0,5] | — |
| Karşılaştırma: tüm hisseler | −%0,5 | — |

Hiçbiri XU100'den ayırt edilemedi. **Bu bir keşiftir, aday kural değildir; bütçeden harcanmaz.** Tür olarak "Reddedilen fikir türleri" tablosundaki teknik sinyal / tek hissede trend türüyle aynıdır. Aynı şablonların maliyet dahil karnesi haftalık araştırmada `templates.txt`'de yazılır (`/tara_sablonlar` aynısını gösterir). Sayılar farklı çıkarsa nedeni bu bölüme eklenir.

**Bizim sonuçlarımız ve farkın nedenleri (28.10.2026; araştırma çalışması 40668554066, açıklama çalışması `screens.yml` 40672060244).** Sütunlar: 20 seans, olay ortalaması maliyet hariç (kullanıcınınkiyle aynı tanım) · örnek sayısı · olay ortalaması 20 günlük hacim tanımıyla · bizim karar etiketimiz.

| Şablon | Kullanıcı (maliyet hariç) | Biz (maliyet hariç) | Örnek: kullanıcı / biz (bağımsız) | 20 günlük hacimle | Karne (maliyet dahil, gün ortalaması) |
|---|---|---|---|---|---|
| 06 `basit_teknik` | −%0,3 · 516 | −%1,3 | 516 / 663 (593) | −%1,5 · 638 | −%1,4 [−3,2; +0,5], ayırt edilemiyor |
| 08 `bebek_teknik` | −%0,0 | −%0,4 | — / 17788 | −%0,4 | −%1,1 [−2,0; −0,3], XU100'ün gerisinde |
| 10 `duseni_kiran` | −%0,9 · 693 | −%0,6 | 693 / 955 (581) | **+%0,3** · 936 | −%1,2 [−3,0; +0,6], ayırt edilemiyor |
| `tek_tus_trend` | +%0,5 · 1249 | +%0,7 | 1249 / 4009 (688) | — | +%0,3 [−0,9; +1,4], ayırt edilemiyor |
| 05 `teknik_temel_ema` | +%0,3 | +%0,5 | — / 31829 | — | −%0,1 [−0,7; +0,6], ayırt edilemiyor |
| tüm hisseler | −%0,5 | yaklaşık −%0,7 (maliyet dahil −%1,0) | | | |

Sonuç: **hükümler aynı.** Hiçbir şablon XU100'ü geçmiyor. Bizim aralıklarımız kullanıcınınkilerle örtüşüyor; yön aynı, büyüklük 0–1 puan farklı.

Farkın ölçülen ve olası nedenleri:
1. **Maliyet (ölçüldü).** Karne maliyet dahildir (gidiş-dönüş %0,3). Kullanıcının sayıları maliyet hariçtir. Yukarıdaki karşılaştırma maliyet hariç yapıldı.
2. **Ortalama türü (ölçüldü).** Karnedeki aralık, gün ortalamasının aralığıdır: her giriş günü bir kez sayılır. Olay ortalaması kalabalık günlere ağırlık verir. Fark çoğu şablonda 0,1–0,5 puan.
3. **Hacim tanımı (ölçüldü).** `goreli_hacim` TradingView'in varsayılanı gibi 10 günlüktür. 20 günlük oranla (`hacim_oran`) düşeni kıran −%0,6'dan +%0,3'e çıkıyor; diğerlerinde fark 0,1–0,4 puan. Yine de hiçbiri ayırt edilebilir hale gelmiyor.
4. **Likidite tabanı (ölçüldü): etkisi yok.** O günkü BIST 100 üyelerinin hepsi 10 mn TL'nin üstünde.
5. **Örnek sayıları (olası, doğrulanamadı).** Kullanıcının sayıları bizim toplam olay sayımız ile bağımsız olay sayımız arasında (516 – 593/663; 693 – 581/955; 1249 – 688/4009). Kullanıcı bir hissenin tutma süresi içindeki tekrar sinyallerini ayıklamış ya da farklı bir dönem veya evren kullanmış olabilir. Kullanıcının betiği görülmeden kesinleştirilemez; **açık**.
6. **Kesişim günü (tanım farkı).** `basit_teknik` kesişimi yalnız o günkü mumda arar; `basit_teknik_3g` son 3 seansta arar. Kullanıcının hangi tanımı kullandığı bilinmiyor. İki tanım da XU100'ün gerisinde.
7. **Eksik koşullar (aynı).** İki tarafta da temel veri koşulları (piyasa değeri, F/S, beta, gelir artışı vb.) uygulanmadı; bu fark yaratmaz.

**Bu açıklamalar şablon seçmek ya da şablon değiştirmek için kullanılmaz (K-38).**

**D1 düzeltmesinin etkisi (28.10.2026, öz-denetim 6, `screens.yml` 40677453651).** Karne artık araştırmanın dışarıda bıraktığı 12 hisseyi kullanmıyor: ADEL, ASUZU, BJKAS, CVKMD, EUREN, FENER, GOLTS, GSRAY, KERVT, PAHOL, TSPOR, TUKAS. 20 seans, olay ortalaması maliyet hariç:

| Şablon | Önce | Sonra |
|---|---|---|
| `basit_teknik` | −%1,3 | −%1,1 |
| `duseni_kiran` | −%0,6 | −%0,4 |
| `bebek_teknik` | −%0,4 | −%0,2 |

Diğerlerinde fark ±0,1 puan; tüm hisseler −%1,0'dan −%0,9'a. **Hiçbir hüküm değişmedi.**

## Not: profesyonel şablonlar ve eleme grupları, keşif (28.10.2026; araştırma programı dışında)

Açıklama çalışması `screens.yml` 40714343039, v0.89.1. Ayarlar: 20 seans, olay ortalaması, maliyet hariç, eleme yok (`ele=hayir`), o günkü BIST 100 üyeleri, giriş ertesi açılış. Kullanıcının PC keşfi de aynı tanımla (eleme öncesi, maliyet hariç) yapıldı.

| | Kullanıcı (PC) | Biz | Örnek | Varsayılan elemelerle (maliyet dahil, gün ortalaması) |
|---|---|---|---|---|
| `minervini` | +%1,07 [−1,04; +2,13] | +%1,4 | 12.940 | +%1,2 |
| `zirveye_yakin` | +%0,47 | +%0,6 | 8.339 | −%0,2 |
| `dusuk_oynaklik` | +%0,31 | +%0,4 | 14.977 | +%0,1 |
| `goreli_guc_ust` (6-1) | −%0,24 | +%0,1 | 15.626 | +%0,2 |
| 12-1 momentum | −%0,58 | hesaplanmadı (şablon değil) | | |
| Elenen grup (K-45) | −%3,07 [−5,53; −0,06] | −%4,1 | 5.068 | |
| Kalan grup | | −%0,3 | 71.084 | |
| Karşılaştırma: tüm hisseler | | | | −%0,6 |

Okuma:
- **Yön her satırda aynı**, büyüklük 0,1–0,4 puan farklı. Olası nedenler, önceki karşılaştırmadaki gibi:
  - 12 sıçramalı hisse dışarıda;
  - sıralar o günkü BIST 100 üyeleri arasında;
  - IBD RS'nin yaklaşık formülü;
  - örnek sayma yöntemi.
- **Elenen grup** iki hesapta da belirgin biçimde zayıf. Bu yalnız geçmişin özeti; canlı izleme (ileri hedef F1) asıl kanıt olacak.
- **Bu satırda aralık yok.** Karnenin aralıkları (20 seanslık blok bootstrap) haftalık araştırmadaki `templates.txt`'de ve `/tara_sablonlar`'da görünür.
- **Hiçbiri aday kural değildir. Eşikler bu sonuçlara göre değiştirilmez (K-47).** Minervini'nin olumlu görünmesi de çok sayıda şablon ve kriter denendiği için şans olabilir.

## Tanımlayıcı ölçüm: destek/direnç seviyeleri rastgele seviyelerden ayırt edilebiliyor mu? (28.10.2026; hipotez değil, bütçe dışı)

- **Yöntem (K-49, sonuçtan önce yazıldı):**
  - Tarama dönemi 2023-08-01 – 30.10.2026, holdout yok; o günkü BIST 100 üyeleri. Dışarıda yalnız PAHOL kaldı (kısa geçmiş).
  - Kapanış, o gün bilinen bir küme seviyesine 0,25 ATR'den yakın kapandığında bir "yaklaşma" sayıldı.
  - Sonraki 5 kapanışta: geldiği yöne 1 ATR uzaklaşma "dönüş", seviyenin öbür yanına 0,5 ATR geçme "kırılma", hiçbiri olmazsa "belirsiz".
  - Karşılaştırma: aynı gün ve aynı sayıda, 52 hafta [dip, zirve] aralığında düzgün rastgele seviyeler (sabit tohum).
- **Kaynak:** `screens.yml`, commit 2857f62, 28.10.2026.

| | Yaklaşma | Dönüş | Kırılma | Belirsiz |
|---|---|---|---|---|
| Gerçek küme seviyeleri | 23.965 | %31,3 | %51,0 | %17,7 |
| Rastgele seviyeler | 25.306 | %31,0 | %51,3 | %17,7 |

- **Dönüş farkı** (gerçek − rastgele): +0,3 puan, %95 [−0,5; +1,1]; 810 gün, 20 seanslık blok bootstrap.
- **Sonuç:** tarihsel olarak rastgele seviyeden **ayırt edilemedi**.
- **Gösterimdeki karşılığı (talimat §3.3):** seviyeler yine gösterilir. Her çıktıda (`/seviye`, `/analyze`, rapor satırı, web) "tarihsel olarak rastgele seviyeden ayırt edilemedi" notu durur.
- Bu bir hipotez testi değildir; seviyeler bir kurala dönüştürülmedi. Canlı kayıt (`logs/levels_log.csv`) sonuç bilinmeden yazılmaya devam eder; ileride aynı ölçüm ileri veride tekrarlanır.

