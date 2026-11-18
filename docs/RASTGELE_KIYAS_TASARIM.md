# Rastgele seçim kıyası tasarımı (QB-ARS-1 R-4, 18.11.2026)

**Durum:** tasarım. Kod ancak sahip bu tasarımı onayladıktan sonra yazılır (gece talimatı madde 5).

## Soru
Kural, aynı sayıda ve aynı zamanlamayla yapılan rastgele hisse seçimlerinden anlamlı biçimde iyi mi?

## Yöntem (Monte Carlo)
1. **Aynı iskelet.** Kuralın gerçek işlem takvimi aynen kullanılır:
   - her giriş günü ve elde tutma süresi;
   - her gün tutulan hisse sayısı.

   Değişen tek şey, o gün o tarihte zamana sadık evrenden (D-1, D-2) seçilen hisselerdir. Seçim yerine koymasız ve eşit olasılıklıdır. Evren, kuralın kullandığı evrenle aynıdır (ör. o günün BIST 100 üyeleri).
2. **Aynı maliyet.** Komisyon, kayma, fiyat adımı ve tavan/taban kilidi kurala nasıl uygulanıyorsa rastgele seçimlere de aynen uygulanır (C-1, C-2). Kilitli günde rastgele seçim de işlem yapamaz.
3. **Tekrar sayısı.** R = 10.000. Bu sayıda, %1 düzeyindeki bir p değerinin standart hatası yaklaşık 0,001'dir.
4. **Tohum.**
   - Sabit bir ana tohum seçilir; önerilen değer çalışmanın ön kayıt tarihi (YYYYMMDD).
   - Her tekrarın tohumu `numpy.random.SeedSequence(ana).spawn(R)` ile türetilir.
   - Ana tohum ön kayda yazılır; sonuç aynı tohumla birebir yeniden üretilir (Md. 12, KT-06).
5. **Ölçü.** Kuralın ölçütüyle aynı istatistik kullanılır (ör. maliyet sonrası XU100'e göre fazla getiri).

   p değeri = (1 + rastgele sonuçların kuralınkine eşit ya da büyük olanlarının sayısı) / (R + 1).
6. **Karar.**
   - Eşik ön kayıttadır.
   - Birden çok kural varsa düzeltme S-2 ile yapılır (`core/research/multiple.py`).
   - Rastgeleyi geçemeyen kural, kural sayılmaz.
7. **Rapor.** Araştırma kartına şunlar yazılır:
   - kuralın değeri;
   - rastgele dağılımın %5, %50 ve %95 noktaları;
   - p değeri;
   - R ve tohum.

## Maliyet (hesap süresi)
- Bir tekrar, bir geriye dönük testin seçim adımıdır. Fiyat matrisleri önceden hazırlanıp vektörle hesaplanırsa 10.000 tekrar dakikalar sürer.
- Bu bir tahmindir ve ilk uygulamada ölçülür.
- Hesap gece penceresinde ve prizdeyken çalışır.

## Sahibin onayına sunulanlar
- R = 10.000;
- ana tohum = ön kayıt tarihi;
- yerine koymasız, eşit olasılıklı seçim;
- kuralla aynı işlem iskeleti ve aynı maliyet.

Bunlardan biri değişecekse ön kayıttan önce değişir.
