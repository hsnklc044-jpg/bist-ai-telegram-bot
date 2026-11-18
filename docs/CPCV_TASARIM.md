# CPCV ve PBO tasarım notu (QB-ARS-1 S-3, S-4; Faz B, 18.11.2026)

**Durum (19.11.2026):** tasarım uygulandı: `core/research/cpcv.py` (358374b, kırmızı takım düzeltmeleri f2337e3). Kanıtlar aşağıda, "Uygulama ve kanıt" bölümünde. Hiçbir araç bunu henüz çağırmıyor. Hiçbir karar, eşik ya da canlı rapor değişmez. İlk satırdaki "yalnız tasarım" ifadesi 18.11 akşamına aitti; bu satır onun yerine geçer.

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

## Uygulama ve kanıt (19.11.2026)
**Üreteç.** `core/research/cpcv.py`:
- `splits(n, N, k, horizon, embargo)` → (eğitim, test) konumları;
- `paths()` → φ = k/N·C(N, k) yol;
- `leaks()` → sızıntı denetimi;
- `pbo()` → arındırılmış bölmelerde PBO.

Arındırma iki yönlüdür. Etiketi [t, t+h] olan bir eğitim gözlemi, aynı pencereye sahip bir test gözlemiyle kesişiyorsa (|t − s| ≤ h) eğitimden çıkar. Ambargo, her test grubunun ardından h + e gözlem bırakır.

**Testler** (`tests/test_research_cpcv.py`, `tests/test_research_redteam.py`):

| Ne kanıtlanıyor | Test | Bağımsız mı |
|---|---|---|
| Eğitim ile test hiç kesişmez, zaman sırası korunur | `test_train_and_test_never_overlap_and_stay_in_time_order` | evet (küme kesişimi) |
| **Kaba kuvvet boşluk testi, 72 ayarda:** her eğitim noktasıyla sonraki test noktaları arasında > h, önceki test noktaları arasında > h + e boşluk var | `test_brute_force_gap_for_many_settings` (19.11) | evet; `leaks()` ve üreteç kodu kullanılmaz, uzaklıklar doğrudan hesaplanır |
| Arındırma ve ambargo gereğinden geniş değil (tam olarak h öncesi, h + e sonrası) | `test_purge_is_not_wider_than_needed` (19.11) | evet (el hesabı: 195–199 ve 300–307) |
| El hesabıyla arındırma ve ambargo noktaları | `test_purge_drops_…`, `test_embargo_drops_…` | evet |
| Kanarya: sızıntılı bir bölme yakalanır | `test_the_leak_check_catches_a_leaky_split` | evet |
| Bölme ve yol sayıları: N=6, k=2 için 15 bölme ve 5 yol; her grup C(5,1) kez test ediliyor | `SplitCountTest` | evet (tanımdan gelen kombinatorik) |
| h = e = 0, N = 16, k = 8'de PBO, K-81 CSCV'ye eşit | `test_equals_the_existing_cscv_without_purge` | hayır (aynı yöntem; yalnız tutarlılık) |

**Bozma denemesi (19.11).** Üreteç iki kez kasıtlı bozuldu: ambargo kaldırıldı ve arındırma 1 gün kısaltıldı. Kaba kuvvet testi ikisinde de kırmızı oldu.

**Kalan:** kitaptaki yayımlanmış örnek sayılar kaynaktan okunamadı. Sayılar tanımdan türetildi. Bu iş Bekleyenler'de kalıyor.
