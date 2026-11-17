# S4 karar notu (18.11.2026)

S4 KANITLI ÖLÇÜM bugün %50 (2,5/5). Resmî seviye S1. Seviye atlanmadığı için S4 ancak S2 ve S3'ten sonra sayılır; ikisinin en erken tarihi 05–07.12.2026.

## 1. Satır satır durum ve tarihli adımlar
| Satır | Bugün | Ön kayıttaki ölçüt | Adımlar ve tarih |
|---|---|---|---|
| Canlı ilk karar | ⏳ | K-93 (1): `forward._verdict` değişmeden kullanılıyor. 5 seans ufku, 5 görünüm, ≥ 20 gün ve ≥ 10 bağımsız dönem, %95 aralık | Kod yazıldı (dal `claude/s4-s5-hazirlik`, sabah onayı bekliyor; canlıda değil; `s4_decision`, her akşam 21:00) → **en erken 06.01.2027** (46 kayıt günü + 5 seans). Kaçan her kayıt günü 1 seans erteler |
| Backtest–canlı sapması | kısmi | K-30 nedenleri; geçmiş değer canlı %95 aralığın dışındaysa sapma var | 06.01.2027: taslak kendiliğinden `logs/research_log_taslak/` altına yazılır → **07.01.2027**: robot taslağı RESEARCH_LOG'a dal üzerinden taşır → satır ✅ |
| Araştırma döngüsü (bütçe + holdout + ön kayıt) | kısmi | a4 ön kaydı (28.10, K-28): H4, H5; holdout 02.11.2026'dan | **27.04.2027** tarama (en erken) → **~30.04.2027** RESEARCH_LOG sonucu → satır ✅. Sonuç ne çıkarsa çıksın döngü tamamlanmış olur |
| Reddedilen fikir türleri | ✅ 27.10 | — | — |
| İki kaynak, fark SLO'su tutuyor | kısmi | K-93 (3): Borsa İstanbul resmî ikinci kaynaktır; art arda 4 cumartesi ✅ | 14.11 ✅ → 21.11 → 28.11 → **05.12.2026** (seri: `logs/haftalik_slo/seri.csv`). Bir hafta tutmazsa seri sıfırlanır, +4 hafta |

**S4 en erken kapanış: ~30.04.2027.** Belirleyen kalem araştırma döngüsü. Önce iki kaynak satırı (05.12), sonra canlı karar ve sapma satırları (06–07.01) kapanır.

## 2. Seçenekler
- **A. Ön kayda göre beklemek.** Kurallar bozulmaz ve S4 ~30.04.2027'de kapanır. Kayıp: zaman.
- **B. A'ya ek olarak bekleme süresini, holdout'a dokunmayan işlerle doldurmak** (§4). S4 tarihi değişmez, ama 27.04'te tarama ilk denemede doğru çalışır.
- **C. Taramayı öne çekmek** (örneğin 3 aylık holdout). Ön kaydı değiştirmek demektir ve kesinlikle yok kuralına girer. **Reddedildi.**
- **D. a3'ü (Aşama 3) "tam döngü" saymak.** a3, holdout kuralından önce ön kaydedildi; kanıt sayılmaz. **Reddedildi.**

## 3. Önerim
**B.** Eşik, pencere ve parametreler değişmez. Kod hazırlıkları yazıldı ve test edildi (dal `claude/s4-s5-hazirlik`, sabah onayı bekliyor; canlıda değil): karar hesabı, RESEARCH_LOG şablonu, iki kaynak tablosu, S5 bildirimi ve "emir yok" testi. Kalan bekleme süresi §4'teki gibi kullanılır. Bu karar kullanıcının onayını bekliyor.

## 4. Araştırma döngüsü: bekleme süresini verimli kullanmak (öneri, uygulanmadı)
Kural: holdout 02.11.2026'dan sonraki veridir. Bir döngüde en fazla 3 hipotez, 6 ayda bir. a4'te 2 hipotez var (H4, H5). a4 ön kaydı 3. hakkı açıkça kapatıyor: "Üçüncü hak bu döngüde kullanılmaz ve devredilmez" (RESEARCH_LOG "a4 ön kaydı"). Bu yüzden a4'e yeni hipotez **eklenemez**. Bunu önermek ön kaydı değiştirmek olurdu.
1. **Ön kaydı olduğu gibi bırakmak.** a4 2 hipotezle ve %97,5 GA ile kalır. 27.04.2027'den önce tarama yapılmaz.
2. **a5'i bir sonraki pencere için şimdiden ön kaydetmek.** Pencere 27.04.2027'den ileri; tarama en erken ~27.10.2027. *Gerekçe:* Aynı holdout iki döngüde kullanılmaz. Sonraki döngü bekleme olmadan başlar.
3. **Tarama kodunu şimdiden yazıp sınamak; sonuç üretmeden.** Sentetik veri ve holdout öncesi veriyle "kuru çalıştırma" yapılır; holdout maskeli kalır. *Gerekçe:* 27.04'te kod hatası yüzünden yeniden çalıştırma olursa bu bir "ikinci deneme" sayılırdı; önceden sınanmış kod bunu önler.
4. **Güç hesabı.** 6 aylık holdout (~120 seans) ile hangi etki büyüklüğünün ayırt edilebildiği hesaplanır. Bu hesap yalnız holdout öncesi oynaklıkla yapılır ve bir hipotez testi değildir. *Gerekçe:* Sonuç "anlamlı değil" çıkarsa bunun "etki yok" mu yoksa "veri yetmedi" mi olduğu önceden bilinir.
- **Yapılmayacaklar:** holdout'a ara bakış; 27.04'ten önce kısmi tarama; holdout öncesi veride bütçe dışı yeni hipotez denemek (3,2 yıllık veride 9 kural zaten reddedildi); başarısız hipotezi yeni ayarla yeniden denemek.
