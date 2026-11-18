# Rejim tanımları: seçenekler (taslak, 18.11.2026; ARS-1 R-1)

**Karar sahibin, ön kayıt konusudur.** Bu taslak, hiçbir araştırma sonucuna ve hiçbir veriye bakılmadan yazıldı. Hiçbir tanım veriyle sınanmadı.

**Bütün seçenekler için ortak kurallar:**
- Rejim, o gün bilinebilen veriyle hesaplanır (D-1). Gelecekteki veri kullanılmaz; eşikler genişleyen pencereyle ya da önceden sabitlenmiş değerlerle belirlenir.
- Tanım, araştırmanın ön kaydında sabitlenir. Sonuç görüldükten sonra değiştirilmez.
- Endeks olarak XU100 (kapanış) kullanılır.

## 1. Yön: yükselen / düşen / yatay
| Seçenek | Tanım | Artı | Eksi |
|---|---|---|---|
| Y-A | XU100 kapanışı 200 seanslık ortalamanın %3 üstündeyse ve ortalamanın 20 seanslık eğimi pozitifse **yükselen**; %3 altındaysa ve eğim negatifse **düşen**; ikisi de değilse **yatay** | yaygın, anlaşılır; bant gürültülü geçişleri azaltır | 200 seans geç tepki verir; %3 bant ve 20 seans iki ayrı serbestlik derecesi |
| Y-B | Son 252 seanslık XU100 getirisi > +%10 ise **yükselen**, < −%10 ise **düşen**, arada **yatay** | tek parametre, basit | yüksek enflasyonda nominal getiri hep yukarı çeker. Türkiye'de reel getiri (TÜFE'yle düzeltilmiş) gerekir; o veri ayrıca kayıt ister |
| Y-C | Y-A'nın USD/TRY ile düzeltilmiş XU100'e (dolar bazlı) uygulanması | enflasyon ve kur etkisini ayırır | kur verisi ikinci bir kaynak ister; tanım karmaşıklaşır |

**Öneri: Y-A.** Nominal yükseliş yanılgısı için ek kural: araştırma kartında sonuç ayrıca reel getiriyle de raporlanır, ama bu yalnız ek bilgidir.

## 2. Oynaklık: yüksek / düşük
| Seçenek | Tanım | Artı | Eksi |
|---|---|---|---|
| O-A | XU100'ün 60 seanslık gerçekleşen oynaklığı, o güne kadarki bütün geçmişin (genişleyen pencere) medyanından büyükse **yüksek** | zamana sadık, eşik veriden öğrenilir ama geleceği kullanmaz | ilk yıllarda medyan kararsızdır; ilk 2 yıl "rejim yok" sayılmalı |
| O-B | 60 seanslık oynaklık yıllık %30'dan büyükse **yüksek** (sabit eşik) | tamamen önceden belirli, hesap basit | eşiği seçmek bir yargıdır; piyasa yapısı değişirse kayar |
| O-C | 60 seanslık oynaklığın son 3 yıldaki yüzdelik sırası ≥ 67 ise **yüksek**, ≤ 33 ise **düşük**, arada **orta** | üç düzey, uç dönemleri ayırır | gözlemler üçe bölünür; her rejimde örnek azalır |

**Öneri: O-A**, ilk 2 yıl hariç tutularak.

## 3. Enflasyon / faiz: yüksek / düşük
| Seçenek | Tanım | Artı | Eksi |
|---|---|---|---|
| F-A | TCMB politika faizi, son 36 ayın medyanından yüksekse **yüksek faiz** | veri projede zaten var (Aşama 3 nakit verisi, RESEARCH_LOG) | faiz ile enflasyon aynı şey değil; faiz kararları gecikmeli |
| F-B | Yıllık TÜFE %30'un üstündeyse **yüksek enflasyon** | doğrudan enflasyon | TÜFE aylık ve gecikmeli yayımlanır; zamana sadık kullanım için yayım tarihi kaydı gerekir (D-1) |
| F-C | Reel politika faizi (politika faizi − yıllık TÜFE) > 0 ise **sıkı**, ≤ 0 ise **gevşek** | para politikasının yönünü tek sayıda verir | iki veri kaynağı gerekir, ikisinin de yayım tarihi tutulmalı |

**Öneri: F-A.** Veri hazır ve zamana sadık kullanımı kolay. F-C, TÜFE yayım tarihleri kayda alınınca eklenebilir.

## Sahibe sorulanlar
- Her başlık için bir seçenek.
- Ön kayda ne zaman yazılacağı: Faz C (Şubat–Mart 2027) mı, yoksa a4'ün ek raporu için daha önce mi?
