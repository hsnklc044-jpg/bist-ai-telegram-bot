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
