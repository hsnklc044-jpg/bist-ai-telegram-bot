<!-- 11.11.2026'da `C:\Projeler\QuantBIST-araclar\karne_kurali.md` dosyasından taşındı (L madde 1); tek kaynak artık bu dosya. -->
# Salı işi: /karne KOD ve /tablo TARAMA

Kaynak: Kullanıcının 06.11.2026'da verdiği TradingView Pine betiği ("Teknik Gösterge Değerlendirici"). Kullanıcı aynı puanlamanın birebir kurulmasını istiyor. K-64 koduna ve K-79 parçalarına dokunma. Kapanmış günlük mumlarla hesapla; TradingView son barı canlı olduğu için seans içinde fark olabilir.

## /karne KOD: İyi/Kötü, puan ve toplam (100 üzerinden)

| Gösterge | İyi koşulu | Puan |
|---|---|---|
| Supertrend | ATR 10, çarpan 3, kaynak hl2; yön yukarı | 5 |
| MACD | ema12-ema26 > 9 günlük sinyal | 10 |
| RSI | RSI(14) > 50 | 10 |
| SMA | kapanış > SMA(20) | 10 |
| ATR | ATR(14) > 1,1 x SMA(ATR(14), 14) | 5 |
| Bollinger | kapanış > orta bant (SMA 20) | 10 |
| ADX | ADX > 20 ve DI+ > DI-. DI: RMA(14). ADX: DX'in SMA(14)'ü, Wilder değil | 10 |
| PSAR | kapanış > SAR(0,02; 0,02; 0,2) | 10 |
| OBV | OBV > SMA(OBV, 20) | 10 |
| CCI | CCI(20, hlc3) > -100 | 5 |
| Göreli hacim | hacim / SMA(hacim, 20) > 1 | 10 |
| MFI | MFI(14, hlc3) > 50 | 5 |

Betikteki diğer sıralama seçenekleri (SMA/EMA sıralama) varsayılan değil; "Fiyat Karşılaştırma" esas.

Karnenin altına kısa grup özeti de ekle: Trend, Momentum, Hacim, Oynaklık. Toplamı değiştirmez; göstergeler birbiriyle ilişkili olduğu için yorumu kolaylaştırır.

## /tablo TARAMA

Sütunlar: Sembol, RSI, Fiyat/EMA (tümü üstünde, tümü altında, karışık), Hacim (5 gün, ortalamaya göre), Mum formasyonu (Yutan Boğa, Yükseliş Marubozu ve benzeri).
EMA seti ve formasyon kuralları kullanıcıdan gelmedi: Önce kullanıcıya sor.

## Genel görev

C:\Projeler\QuantBIST-araclar\otonom_gorev.md dosyasını da oku ve kullanıcıya öncelik listesinde sun.

## Sonraki büyük iş

/karne ve /tablodan sonra C:\Projeler\QuantBIST-araclar\model_6_12_ay.md dosyasını oku. Kullanıcı bu 6-12 aylık modeli istiyor; dosyadaki açık noktaları kullanıcıya sor.

## Doğrulama

GARAN'ı kullanıcının TradingView tablosuyla karşılaştır: 06.11.2026 10:22 ekranda toplam 90/100, yalnız göreli hacim Kötü (canlı bar).
Sabah listesinde `(-0,0%)` görünümünü de düzelt.
