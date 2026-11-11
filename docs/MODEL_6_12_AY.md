<!-- 11.11.2026'da `C:\Projeler\QuantBIST-araclar\model_6_12_ay.md` dosyasından taşındı (L madde 1); tek kaynak artık bu dosya. -->
# 6-12 aylık temel + teknik model (kullanıcı isteği, 06.11.2026)

Ayrı model olarak eklenir; mevcut modelle aynı veride karşılaştırılır. Önce mevcut veri kaynakları, tarama kuralları ve test akışı incelenir. K-64 kodu ve K-79 parçaları değişmez; holdout verisi okunmaz.
Ana ilke: Puan ile giriş kararı ayrıdır. Örneğin 82/100 puanlı hisse kırılım yapmadıysa veya fiyat alım tavanını aştıysa sonuç "İzle" olur ve eksik koşul yazılır.

## 1. Temel eleme
- Finans dışı BIST şirketleri; banka, sigorta, GYO ayrı sınıf.
- Likidite: önceki 60 tamamlanmış seansın medyan günlük TL işlem tutarı; asgari eşik ayarlanabilir.
- Son 12 ay faaliyet nakit akışı > 0.
- FAVÖK > 0 ise net borç/FAVÖK başlangıç eşiği 2,5. FAVÖK ≤ 0 ise oran gösterilmez, inceleme durumu yazılır.
- Değerleme sektör emsalleriyle karşılaştırılır. Hesaplanan veya kullanıcının girdiği üst alım fiyatı kullanılır; yoksa aday izleme listesine gider.
- Finansal veri yalnız KAP yayımından sonra kullanılabilir. Sonraki düzeltmeler geçmiş karar girdisine taşınmaz. "Eksik veri" ile "koşulu karşılamıyor" ayrı gösterilir.

## 2. Teknik puan (yalnız tamamlanmış günlük mum; geçmiş yetmezse "veri yetersiz"; koşul tam puan ya da sıfır)
Trend /40
- 15: Kapanış > SMA50 > SMA200 ve SMA50 bugün, 5 seans öncekinden yüksek.
- 8: Supertrend (ATR 10, çarpan 3) yukarı.
- 10: ADX/DMI (14, 14): ADX > 20 ve +DI > -DI.
- 4: PSAR kapanışın altında (0,02; 0,02; 0,20).
- 3: Kapanış Bollinger (20, 2) orta bandının üstünde.
Momentum /25
- 10: MACD (12, 26, 9) çizgisi sinyalin üstünde.
- 10: RSI(14) > 50.
- 5: CCI(20) > -100.
Hacim /35
- 10: OBV > kendi SMA20'si.
- 15: Bugünkü hacim / önceki 20 tamamlanmış seansın medyan hacmi ≥ 1,5 (bugün paydada yok).
- 10: MFI(14) > 50.
ATR(14) ve ATR% risk sütununda, puansız. Tavan 100. Eksik gösterge varsa kalanlar 100'e ölçeklenmez. Sektöre göre 63 seans getiri farkı aynı getiri tanımıyla hesaplanır; puana girmez, sıralamada kullanılır.

## 3. Giriş ve pozisyon riski
Temeli geçenler teknik puan ve sektör farkıyla sıralanır. İlk sürümde zorunlu puan eşiği yok. Giriş adayı koşulları:
- SMA trend koşulu sağlanıyor.
- Kapanış, sinyal günü hariç önceki 20 seansın en yükseğinin üstünde.
- Göreceli hacim ≥ 1,5.
- Sonraki seansta gerçekleşebilir giriş fiyatı üst alım fiyatını aşmıyor.
Giriş fiyatı, grafik yapısına göre teknik çıkış seviyesi ve mesafenin ATR karşılığı gösterilir. Çıkış ve risk bütçesi tanımlı, giriş > çıkış ise: lot = aşağı yuvarla(risk bütçesi / hisse başına planlanan kayıp). İşlem maliyeti, likidite ve portföy sınırları hesaba katılır. Araştırma ve karar desteği içindir.

## 4. Ekran
Her hisse için: fiyat tarihi ve son KAP tarihi; temel sonuç ve her eleme nedeni; her göstergenin değeri, koşulu, sonucu, puanı; Trend /40, Momentum /25, Hacim /35, toplam /100; sektör farkı, ATR%, kırılım seviyesi, üst alım fiyatı; durum (Elendi, İzle, Giriş adayı, Veri yetersiz); ölçülebilir koşullara dayanan kısa açıklama.
Puan ve durum kuralla hesaplanır. Yapay zekâ yalnız açıklar, eksik rakam tahmin etmez, sayılar ekranla eşleşir.

## 5. Geçmiş test
Aynı evren ve varsayımlarla: A temel filtre; B temel + SMA trendi + hacimli kırılım; C B + teknik puana göre sıralama.
Kapasite sınırlıysa sıralama kuralı açık yazılır. Hacim hem girişte hem puanda olduğu için hacim puanını çıkaran duyarlılık testi yapılır. Sinyal sonraki seansta işlenir; komisyon, alış-satış farkı, gerçekleşemeyen işlem hesaba katılır. Sonradan borsadan çıkan hisseler veri izin verdiği ölçüde evrende. Parametre dönemi ile değerlendirme dönemi ayrı. Rapor: net getiri, BIST getiri endeksine göre fark, en büyük düşüş, işlem sayısı, devir hızı; ölçülemeyen sonuçlar açıkça yazılır.
Bitince: model, varsayımlar, değişen dosyalar, doğrulama sonuçları, eksik girdiler ve engelledikleri kararlar gösterilir.

## Salıda çözülecek açık noktalar (Claude notu)
1. Geçmiş KAP finansalları sistemde yok (K-78). Bu veri gelmeden A, B ve C temel filtreyle dürüstçe geriye test edilemez.
2. Çıkış kuralı yok. 6-12 aylık ufuk için çıkış ve tutma süresi test öncesinde sabitlenmeli.
3. Gerekli girdiler: üst alım fiyatı, risk bütçesi, portföy sınırı, likidite eşiği, sektör sınıflaması. Bunlar kullanıcıdan istenir.
4. Getiri endeksi verisi var mı kontrol edilir; XU100 getiri endeksi değildir.
5. Holdout (02.11.2026 sonrası) okunmaz; K-78 gibi kurallar ölçümden önce yazılır. K-78 measure ve bu test için ayrı onay istenir.
6. /karne, kullanıcının TradingView betiğiyle birebir kalır (karne_kurali.md). Bu modelin puanı ayrı bir karnedir; iki puan karıştırılmaz.
7. Sıra: önce canlı karar ekranı (geçmiş finansal gerektirmez), sonra test; tek oturuma sığdırmaya çalışma.
