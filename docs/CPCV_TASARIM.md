# CPCV ve PBO tasarım notu (QB-ARS-1 S-3, S-4; Faz B, 18.11.2026)

**Durum:** yalnız tasarım; kod sonraki gecelerde ve önce testle yazılacak. Hiçbir karar, eşik ya da canlı rapor değişmez.

## Bugün ne var
`core/backtest/overfit.py` (K-81) zaten iki ölçü hesaplıyor:
- **PBO:** kombinatoryal simetrik çapraz doğrulama (CSCV), 16 blok ve C(16, 8) bölme;
- **Deflated Sharpe.**

İkisi de araştırma raporunda yalnız bilgi olarak duruyor. Özellik testleri var: saf gürültü yaklaşık yazı-tura çıkıyor, baskın strateji nadiren aşırı uydurulmuş çıkıyor. Eksik olanlar şunlar:
- yayımlanmış bir sayıyla doğrulama;
- zaman serisi için arındırma (purge) ve ambargo;
- CPCV'nin yol (path) üretimi.

## Tasarım
1. **Bölme.** Seans takvimi N eşit gruba bölünür. Önerilen N = 10. Her bölmede k grup test, kalanlar eğitim olur. Önerilen k = 2, böylece C(10, 2) = 45 bölme çıkar. Her test grubu (N−1)!/((k−1)!(N−k)!) = 9 kez test edilir ve 9 tam geriye-dönük-test yolu oluşur.
2. **Arındırma.** Eğitimdeki bir gözlemin etiket penceresi bir test grubuyla kesişiyorsa o gözlem eğitimden çıkarılır. Örneğin etiket "ertesi açılıştan h seans sonrasına kadar getiri" ise penceresi [t+1, t+h] olur.
3. **Ambargo.** Her test grubunun hemen ardından gelen eğitim gözlemleri de çıkarılır. Önerilen pay: toplam seansların %1'i ya da etiket süresi h, hangisi büyükse.
4. **Rastgele karıştırma yasak.** Bölmeler zamana göre sıralı kalır. Testler bunu ayrıca denetler (ARS-1 S-4).
5. **PBO.** Her bölmede, eğitimde en iyi olan varyantın testteki göreli sırasının logiti hesaplanır. PBO, bu logitin ≤ 0 olduğu bölmelerin oranıdır. Mevcut CSCV hesabı korunur; arındırma ve ambargo eklenmiş sürümü yanına konur, eskisi silinmez.

## Doğrulama planı (kod yazılmadan önce)
- **Yapısal testler:**
  - bölme sayısı C(N, k) olmalı;
  - her grubun test edilme sayısı formülle aynı olmalı;
  - eğitim ile test kesişmemeli;
  - arındırılan ve ambargolanan gözlemler el hesabıyla bulunanla aynı olmalı.
- **Geleceğe bakma testi:** etiket penceresi test grubuna giren bir gözlem eğitimde kalırsa test kırmızı olmalı (kanarya).
- **Yayımlanmış sayı:**
  - Kaynak: López de Prado (2018), *Advances in Financial Machine Learning*, bölüm 7 ve 12. Bu kitaptaki örnek bölme sayıları ve yol sayıları (örneğin N = 6, k = 2 için 15 bölme ve 5 yol) testte aynen üretilmeli.
  - Kaynak bu gece okunamadı (ağdan erişilemedi). Testteki sayı kaynaktan okunmadan yazılmayacak; "Bekleyenler"de.

## Açık kararlar
- N, k ve ambargo payı her araştırmanın ön kaydında sabitlenir. Bu belge yalnız varsayılanları önerir.
